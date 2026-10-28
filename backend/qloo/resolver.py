"""Resolve free-text cultural anchors into Qloo entity / tag IDs."""

from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from typing import Any, Optional

from models import AnchorResolution
from qloo.client import QlooClient, QlooError

logger = logging.getLogger("vibe.qloo.resolver")

# Below this, a Qloo hit is a different name that merely came back from search.
_MIN_MATCH = 60.0
_KEYBOARD_ROWS = ("qwertyuiop", "asdfghjkl", "zxcvbnm")
# Words that show up in many titles and must not carry a match on their own.
_GENERIC_TOKENS = frozenset(
    {
        "studio",
        "studios",
        "music",
        "film",
        "films",
        "movie",
        "movies",
        "night",
        "house",
        "band",
        "group",
        "records",
        "sound",
        "pictures",
        "photo",
        "entertainment",
        "productions",
        "production",
        "official",
    }
)


def _entity_id(entity: dict[str, Any]) -> Optional[str]:
    eid = entity.get("entity_id") or entity.get("id") or entity.get("qloo_id")
    return str(eid) if eid else None


def _entity_name(entity: dict[str, Any]) -> str:
    return str(entity.get("name") or entity.get("title") or "")


def _entity_type(entity: dict[str, Any]) -> Optional[str]:
    t = entity.get("type") or entity.get("entity_type")
    return str(t) if t else None


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    return "".join(c for c in text if not unicodedata.combining(c))


def _compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", _fold(text))


def _tokens(text: str) -> list[str]:
    folded = _fold(text).replace("&", " and ")
    return re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", folded)


# Real 3-letter anchors that sit on one keyboard row. Everything else that
# tight ("sda", "qwe") is mash, even if Qloo has a record with that name.
_SHORT_ROW_WORDS = frozenset({"sad", "dad", "pop"})


def _same_row_cluster(compact: str) -> bool:
    """True when every letter is huddled on one keyboard row.

    "sada", "asda", and "sdasd" are home-row mashes. They must not match a
    film or brand that happens to share the spelling. "Sade" uses two rows,
    so a real name still gets through.
    """
    if len(compact) < 3 or not compact.isalpha():
        return False
    if compact in _SHORT_ROW_WORDS:
        return False
    # "dada" / "coco" — a doubled pair, not a scramble.
    if len(compact) == 4 and compact[:2] == compact[2:]:
        return False
    cols: list[int] = []
    row: Optional[int] = None
    for ch in compact:
        found: Optional[tuple[int, int]] = None
        for row_i, keys in enumerate(_KEYBOARD_ROWS):
            col = keys.find(ch)
            if col >= 0:
                found = (col, row_i)
                break
        if found is None:
            return False
        col, row_i = found
        if row is None:
            row = row_i
        elif row_i != row:
            return False
        cols.append(col)
    return max(cols) - min(cols) <= 2


def looks_like_gibberish(text: str) -> bool:
    """Keyboard mash and repeated syllables, not short real names like BTS or Coco."""
    compact = _compact(text)
    if len(compact) < 2:
        return True
    if len(compact) >= 4 and len(set(compact)) == 1:
        return True
    n = len(compact)
    for size in range(1, n // 2 + 1):
        if n % size:
            continue
        reps = n // size
        if compact[:size] * reps != compact:
            continue
        if (size >= 3 and reps >= 2) or reps >= 3:
            return True
    for row in _KEYBOARD_ROWS:
        if len(compact) >= 4 and (compact in row or compact in row[::-1]):
            return True
    if _same_row_cluster(compact):
        return True
    return False


def match_score(query: str, name: str, *, partial: bool = False) -> float:
    """How confidently `name` is the thing the user typed.

    Short queries must be a whole token. "sda" is not "S. Dali Museum",
    and "Studio Ghibli" is not "Picsart Photo Studio".
    """
    if looks_like_gibberish(query):
        return 0.0
    q_compact = _compact(query)
    n_compact = _compact(name)
    if len(q_compact) < 2 or not n_compact:
        return 0.0
    if q_compact == n_compact:
        return 100.0

    q_compacts = [c for c in (_compact(t) for t in _tokens(query)) if c]
    n_compacts = [c for c in (_compact(t) for t in _tokens(name)) if c]
    if not q_compacts or not n_compacts:
        return 0.0

    if all(c in n_compacts for c in q_compacts):
        return 85.0

    # "radio" → "Radiohead". Never "sda" → "S. Dali Museum" via a 3-letter prefix.
    if len(q_compact) >= 4 and n_compact.startswith(q_compact):
        return 75.0

    longest = max(len(c) for c in q_compacts)
    if longest >= 4:
        long_tokens = [c for c in q_compacts if len(c) == longest]
        if all(c in n_compacts for c in long_tokens):
            return 70.0

    # "Studio Ghibli" → "Ghibli", but not "Studio Ghibli" → "Picsart Photo Studio".
    distinctive = [c for c in q_compacts if len(c) >= 5 and c not in _GENERIC_TOKENS]
    if distinctive:
        longest_distinctive = max(distinctive, key=len)
        if longest_distinctive in n_compacts:
            return 72.0

    # Vibes: "cozy lo-fi" may come back as the tag "Lo-Fi".
    if partial and any(len(c) >= 4 and c in n_compacts for c in q_compacts):
        return 65.0
    return 0.0


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
        tasks: list[Any] = []
        if music and music.strip():
            tasks.append(self.resolve_music(music.strip()))
        if film and film.strip():
            tasks.append(self.resolve_film(film.strip()))
        if vibe and vibe.strip():
            tasks.append(self.resolve_vibe(vibe.strip()))
        if not tasks:
            return []
        return list(await asyncio.gather(*tasks))

    async def resolve_music(self, text: str) -> AnchorResolution:
        if looks_like_gibberish(text):
            return AnchorResolution(input=text, kind="music", resolved=False)
        return await self._resolve_entity(text, kind="music", types=self.MUSIC_TYPES)

    async def resolve_film(self, text: str) -> AnchorResolution:
        if looks_like_gibberish(text):
            return AnchorResolution(input=text, kind="film", resolved=False)
        # Prefer brand for studio names, then movie / person. Search types in parallel.
        ordered_types = ["urn:entity:brand", "urn:entity:movie", "urn:entity:person"]

        async def _search_type(t: str) -> list[dict[str, Any]]:
            try:
                return await self.client.search(text, types=t, take=5)
            except QlooError as exc:
                logger.warning("film search failed for %r type=%s: %s", text, t, exc)
                return []

        batches = await asyncio.gather(*[_search_type(t) for t in ordered_types])
        hits: list[dict[str, Any]] = [hit for batch in batches for hit in batch]
        best = self._pick_best(hits, preferred_types=ordered_types, query=text)
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
        if looks_like_gibberish(text):
            return AnchorResolution(input=text, kind="vibe", resolved=False)
        try:
            tags = await self.client.tags(text, take=8)
        except QlooError as exc:
            logger.warning("vibe tag search failed for %r: %s", text, exc)
            tags = []
        best = None
        best_key: Optional[tuple[float, float]] = None
        for tag in tags:
            tid = tag.get("id") or tag.get("tag_id")
            name = str(tag.get("name") or "")
            if not tid:
                continue
            score = match_score(text, name, partial=True)
            if score < _MIN_MATCH:
                continue
            # Prefer non-media tags for vibe aesthetics when the name match ties.
            blob = f"{tid} {name}".lower()
            media_penalty = 2.0 if any(x in blob for x in ("genre:media", "urn:tag:genre:movie", "artist")) else 0.0
            key = (score - media_penalty, score)
            if best_key is None or key > best_key:
                best_key = key
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
        best = self._pick_best(hits, preferred_types=preferred, query=text)
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
    def _name_score(query: str, name: str) -> float:
        return match_score(query, name)

    @classmethod
    def _pick_best(
        cls,
        hits: list[dict[str, Any]],
        preferred_types: list[str],
        query: str = "",
    ) -> Optional[dict[str, Any]]:
        if not hits:
            return None

        def rank(entity: dict[str, Any]) -> tuple:
            et = _entity_type(entity) or ""
            try:
                type_rank = preferred_types.index(et)
            except ValueError:
                type_rank = 99
            name_score = cls._name_score(query, _entity_name(entity))
            return (-name_score, type_rank, 0 if _entity_id(entity) else 1)

        best = sorted(hits, key=rank)[0]
        if query and cls._name_score(query, _entity_name(best)) < _MIN_MATCH:
            return None
        return best

    @staticmethod
    def signal_entity_ids(resolutions: list[AnchorResolution]) -> list[str]:
        return [r.entity_id for r in resolutions if r.resolved and r.entity_id]

    @staticmethod
    def signal_tag_ids(resolutions: list[AnchorResolution]) -> list[str]:
        return [r.tag_id for r in resolutions if r.resolved and r.tag_id]

    @staticmethod
    def any_resolved(resolutions: list[AnchorResolution]) -> bool:
        return any(r.resolved for r in resolutions)
