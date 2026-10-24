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

# Hard exclude: these pollute filter.tags and pull hotels / amenities.
_EXCLUDE_SUBSTRINGS = (
    ":hotel:",
    "hotel:",
    "amenity:",
    "nearby_attraction:",
    "setting:qloo:",
    "decor:qloo:",
    "ambience:qloo:",
    "keyword:qloo:",
    "neighborhood_characteristics:",
    "service_options:",
    "offerings:place:",
    "specialty_dish:",
    "genre:media:",
    "wikidata:",
    "movie",
    "artist",
    "podcast",
    "book",
    "tv_show",
    "video_game",
)


def _score_tag(tag: dict[str, Any], query: str) -> float:
    tid = str(tag.get("id") or tag.get("tag_id") or "").lower()
    name = str(tag.get("name") or "").lower()
    blob = f"{tid} {name}"
    if any(bad in blob for bad in _EXCLUDE_SUBSTRINGS):
        return -100.0

    score = 0.0
    q = query.lower().strip()
    q_us = q.replace(" ", "_")

    # Strongly prefer canonical place category / genre tags discovered live.
    if tid.startswith("urn:tag:category:place:"):
        score += 20.0
    elif tid.startswith("urn:tag:genre:place:restaurant:") and q_us in tid:
        # e.g. genre:place:restaurant:cafe / bar / cocktail_bar
        score += 16.0
    elif tid.startswith("urn:tag:genre:place:") and ":hotel:" not in tid:
        # e.g. genre:place:museum, genre:place:restaurant
        score += 14.0
    elif tid.startswith("urn:tag:dining_option:qloo:"):
        score += 4.0
    elif tid.startswith("urn:tag:cuisine:qloo:"):
        score += 2.0
    else:
        score -= 5.0  # unknown shapes are last resort

    if q and name == q:
        score += 8.0
    elif q and q in name:
        score += 4.0
    if q_us and tid.endswith(":" + q_us):
        score += 6.0
    elif q_us and q_us in tid:
        score += 3.0

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
                    # Re-filter override through scoring so stale hotel tags drop out.
                    cleaned = [str(x) for x in ids if x and _score_tag({"id": x, "name": ""}, "") > 0]
                    if cleaned:
                        self._cache[phase] = cleaned[:4]
            for phase, ids in (data.get("broad") or {}).items():
                if phase in PHASES and isinstance(ids, list):
                    cleaned = [str(x) for x in ids if x and _score_tag({"id": x, "name": ""}, "") > 0]
                    if cleaned:
                        self._broad_cache[phase] = cleaned[:6]
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
        # Keep the top few high-signal tags only — too many tags softens the filter.
        return [tid for _, tid in ranked[:4]]

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
