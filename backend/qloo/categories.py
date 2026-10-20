"""Phase → place-category tag ID resolution (discovered via /v2/tags)."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Optional

from config import PHASE_BROAD_CATEGORY_QUERIES, PHASE_CATEGORY_QUERIES, PHASES
from qloo.client import QlooClient, QlooError

logger = logging.getLogger("vibe.qloo.categories")

# Optional override written by qloo_probe.py (gitignored captures/).
_OVERRIDE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "captures" / "category_tags.json"

# Soft preference: tag IDs that look place-related score higher.
_PLACE_HINTS = ("place", "restaurant", "cafe", "coffee", "bar", "museum", "gallery", "hotel", "venue", "nightlife", "shop", "store", "bakery")
_EXCLUDE_HINTS = ("movie", "artist", "podcast", "book", "tv_show", "video_game", "brand:media")


def _score_tag(tag: dict[str, Any], query: str) -> float:
    tid = str(tag.get("id") or tag.get("tag_id") or "").lower()
    name = str(tag.get("name") or "").lower()
    blob = f"{tid} {name}"
    if any(bad in blob for bad in _EXCLUDE_HINTS):
        return -100.0
    score = 0.0
    q = query.lower()
    if q and q in name:
        score += 5.0
    if q and q.replace(" ", "_") in tid:
        score += 4.0
    if any(h in blob for h in _PLACE_HINTS):
        score += 3.0
    if "urn:tag:" in tid:
        score += 1.0
    return score


def _tag_id(tag: dict[str, Any]) -> Optional[str]:
    tid = tag.get("id") or tag.get("tag_id")
    return str(tid) if tid else None


class CategoryResolver:
    """Resolve and cache phase category tag IDs."""

    def __init__(self, client: QlooClient):
        self.client = client
        self._cache: dict[str, list[str]] = {}
        self._broad_cache: dict[str, list[str]] = {}
        self._loaded_override = False

    def _load_override(self) -> None:
        if self._loaded_override:
            return
        self._loaded_override = True
        if not _OVERRIDE_PATH.exists():
            return
        try:
            data = json.loads(_OVERRIDE_PATH.read_text(encoding="utf-8"))
            for phase, ids in (data.get("strict") or {}).items():
                if phase in PHASES and isinstance(ids, list):
                    self._cache[phase] = [str(x) for x in ids if x]
            for phase, ids in (data.get("broad") or {}).items():
                if phase in PHASES and isinstance(ids, list):
                    self._broad_cache[phase] = [str(x) for x in ids if x]
            logger.info("Loaded category tag override from %s", _OVERRIDE_PATH)
        except Exception as exc:
            logger.warning("Failed to load category override: %s", exc)

    async def _discover(self, queries: tuple[str, ...], take_per: int = 8) -> list[str]:
        ranked: list[tuple[float, str]] = []
        seen: set[str] = set()
        for q in queries:
            try:
                tags = await self.client.tags(q, take=take_per)
            except QlooError as exc:
                logger.warning("tag discovery failed for %r: %s", q, exc)
                continue
            for tag in tags:
                tid = _tag_id(tag)
                if not tid or tid in seen:
                    continue
                score = _score_tag(tag, q)
                if score < 0:
                    continue
                seen.add(tid)
                ranked.append((score, tid))
        ranked.sort(key=lambda x: x[0], reverse=True)
        return [tid for _, tid in ranked[:6]]

    async def tags_for_phase(self, phase: str, *, broad: bool = False) -> list[str]:
        phase = phase.upper()
        self._load_override()
        cache = self._broad_cache if broad else self._cache
        if phase in cache and cache[phase]:
            return list(cache[phase])
        queries = (
            PHASE_BROAD_CATEGORY_QUERIES.get(phase)
            if broad
            else PHASE_CATEGORY_QUERIES.get(phase)
        ) or ()
        ids = await self._discover(queries)
        cache[phase] = ids
        return list(ids)

    async def warm_all(self) -> dict[str, list[str]]:
        """Preload strict tags for every phase. Returns the cache map."""
        out: dict[str, list[str]] = {}
        for phase in PHASES:
            out[phase] = await self.tags_for_phase(phase, broad=False)
        return out

    def export_override(self) -> dict[str, Any]:
        return {"strict": dict(self._cache), "broad": dict(self._broad_cache)}
