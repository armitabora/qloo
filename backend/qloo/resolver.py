"""Resolve free-text cultural anchors into Qloo entity / tag IDs."""

from __future__ import annotations

import logging
from typing import Any, Optional

from models import AnchorResolution
from qloo.client import QlooClient, QlooError

logger = logging.getLogger("vibe.qloo.resolver")


def _entity_id(entity: dict[str, Any]) -> Optional[str]:
    eid = entity.get("entity_id") or entity.get("id") or entity.get("qloo_id")
    return str(eid) if eid else None


def _entity_name(entity: dict[str, Any]) -> str:
    return str(entity.get("name") or entity.get("title") or "")


def _entity_type(entity: dict[str, Any]) -> Optional[str]:
    t = entity.get("type") or entity.get("entity_type")
    return str(t) if t else None


class AnchorResolver:
    """Map music / film / vibe inputs to Qloo signals."""

    MUSIC_TYPES = "urn:entity:artist"
    FILM_TYPES = ["urn:entity:movie", "urn:entity:person", "urn:entity:brand"]

    def __init__(self, client: QlooClient):
        self.client = client

    async def resolve_all(
        self,
        *,
        music: Optional[str] = None,
        film: Optional[str] = None,
        vibe: Optional[str] = None,
    ) -> list[AnchorResolution]:
        results: list[AnchorResolution] = []
        if music and music.strip():
            results.append(await self.resolve_music(music.strip()))
        if film and film.strip():
            results.append(await self.resolve_film(film.strip()))
        if vibe and vibe.strip():
            results.append(await self.resolve_vibe(vibe.strip()))
        return results

    async def resolve_music(self, text: str) -> AnchorResolution:
        return await self._resolve_entity(text, kind="music", types=self.MUSIC_TYPES)

    async def resolve_film(self, text: str) -> AnchorResolution:
        # Try movie → person → brand in one multi-type search first.
        try:
            hits = await self.client.search(text, types=self.FILM_TYPES, take=6)
        except QlooError as exc:
            logger.warning("film search failed for %r: %s", text, exc)
            hits = []
        best = self._pick_best(hits, preferred_types=self.FILM_TYPES)
        if best:
            return AnchorResolution(
                input=text,
                kind="film",
                resolved=True,
                matched_name=_entity_name(best) or text,
                entity_id=_entity_id(best),
                entity_type=_entity_type(best),
            )
        return AnchorResolution(input=text, kind="film", resolved=False)

    async def resolve_vibe(self, text: str) -> AnchorResolution:
        try:
            tags = await self.client.tags(text, take=8)
        except QlooError as exc:
            logger.warning("vibe tag search failed for %r: %s", text, exc)
            tags = []
        best = None
        best_score = -1.0
        needle = text.lower()
        for tag in tags:
            tid = tag.get("id") or tag.get("tag_id")
            name = str(tag.get("name") or "")
            if not tid:
                continue
            score = 0.0
            if needle and needle in name.lower():
                score += 5
            if needle.replace(" ", "_") in str(tid).lower():
                score += 3
            # Prefer non-media tags for vibe aesthetics.
            blob = f"{tid} {name}".lower()
            if any(x in blob for x in ("genre:media", "urn:tag:genre:movie", "artist")):
                score -= 2
            if score > best_score:
                best_score = score
                best = tag
        if best:
            return AnchorResolution(
                input=text,
                kind="vibe",
                resolved=True,
                matched_name=str(best.get("name") or text),
                tag_id=str(best.get("id") or best.get("tag_id")),
            )
        return AnchorResolution(input=text, kind="vibe", resolved=False)

    async def _resolve_entity(
        self, text: str, *, kind: str, types: str | list[str]
    ) -> AnchorResolution:
        try:
            hits = await self.client.search(text, types=types, take=5)
        except QlooError as exc:
            logger.warning("%s search failed for %r: %s", kind, text, exc)
            hits = []
        preferred = types if isinstance(types, list) else [types]
        best = self._pick_best(hits, preferred_types=preferred)
        if best:
            return AnchorResolution(
                input=text,
                kind=kind,  # type: ignore[arg-type]
                resolved=True,
                matched_name=_entity_name(best) or text,
                entity_id=_entity_id(best),
                entity_type=_entity_type(best),
            )
        return AnchorResolution(input=text, kind=kind, resolved=False)  # type: ignore[arg-type]

    @staticmethod
    def _pick_best(
        hits: list[dict[str, Any]], preferred_types: list[str]
    ) -> Optional[dict[str, Any]]:
        if not hits:
            return None
        # Prefer exact-ish name + preferred type order.
        def rank(entity: dict[str, Any]) -> tuple:
            et = _entity_type(entity) or ""
            try:
                type_rank = preferred_types.index(et)
            except ValueError:
                type_rank = 99
            return (type_rank, 0 if _entity_id(entity) else 1)

        return sorted(hits, key=rank)[0]

    @staticmethod
    def signal_entity_ids(resolutions: list[AnchorResolution]) -> list[str]:
        return [r.entity_id for r in resolutions if r.resolved and r.entity_id]

    @staticmethod
    def signal_tag_ids(resolutions: list[AnchorResolution]) -> list[str]:
        return [r.tag_id for r in resolutions if r.resolved and r.tag_id]

    @staticmethod
    def any_resolved(resolutions: list[AnchorResolution]) -> bool:
        return any(r.resolved for r in resolutions)
