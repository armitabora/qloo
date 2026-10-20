"""Per-phase place recommendations via /v2/insights."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Optional

from config import CITY_REGISTRY
from models import AnchorResolution, Influence
from qloo.categories import CategoryResolver
from qloo.client import QlooClient, QlooError
from qloo.resolver import AnchorResolver

logger = logging.getLogger("vibe.qloo.places")


@dataclass
class PlaceCandidate:
    entity_id: str
    name: str
    category: str = ""
    address: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    affinity: Optional[float] = None
    influenced_by: list[Influence] = field(default_factory=list)
    image_url: Optional[str] = None
    raw_properties: dict[str, Any] = field(default_factory=dict)


def _extract_entities(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results") or {}
    if isinstance(results, dict):
        entities = results.get("entities") or []
    elif isinstance(results, list):
        entities = results
    else:
        entities = payload.get("entities") or []
    return [e for e in entities if isinstance(e, dict)]


def _entity_id(entity: dict[str, Any]) -> Optional[str]:
    eid = entity.get("entity_id") or entity.get("id") or entity.get("qloo_id")
    return str(eid) if eid else None


def _affinity(entity: dict[str, Any]) -> Optional[float]:
    query = entity.get("query")
    if isinstance(query, dict) and query.get("affinity") is not None:
        try:
            return float(query["affinity"])
        except (TypeError, ValueError):
            pass
    if entity.get("affinity") is not None:
        try:
            return float(entity["affinity"])
        except (TypeError, ValueError):
            pass
    return None


def _address(entity: dict[str, Any]) -> Optional[str]:
    props = entity.get("properties") or {}
    if not isinstance(props, dict):
        return None
    for key in ("address", "formatted_address", "location"):
        val = props.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
        if isinstance(val, dict):
            for sub in ("formatted", "name", "address"):
                if isinstance(val.get(sub), str) and val[sub].strip():
                    return val[sub].strip()
    geocode = props.get("geocode")
    if isinstance(geocode, dict):
        parts = [
            geocode.get("name"),
            geocode.get("admin1_region"),
            geocode.get("country_code"),
        ]
        joined = ", ".join(str(p) for p in parts if p)
        return joined or None
    return None


def _image_url(entity: dict[str, Any]) -> Optional[str]:
    props = entity.get("properties") or {}
    if not isinstance(props, dict):
        return None
    image = props.get("image")
    if isinstance(image, dict):
        url = image.get("url") or image.get("src")
        return str(url) if url else None
    if isinstance(image, str):
        return image
    return None


def _tag_names(entity: dict[str, Any], limit: int = 4) -> list[str]:
    tags = entity.get("tags") or []
    names: list[str] = []
    for t in tags:
        if isinstance(t, dict):
            name = t.get("name") or t.get("id")
        else:
            name = str(t)
        if name:
            names.append(str(name))
        if len(names) >= limit:
            break
    return names


def _category_label(entity: dict[str, Any], fallback: str = "Place") -> str:
    tags = _tag_names(entity, limit=1)
    if tags:
        return tags[0]
    props = entity.get("properties") or {}
    if isinstance(props, dict) and props.get("business_type"):
        return str(props["business_type"])
    return fallback


def _parse_explainability(
    entity: dict[str, Any],
    resolutions: list[AnchorResolution],
) -> list[Influence]:
    """Map query.explainability back onto user anchors."""
    query = entity.get("query") or {}
    if not isinstance(query, dict):
        return []
    explain = query.get("explainability") or entity.get("explainability") or {}
    if not isinstance(explain, dict):
        return []

    # Typical shape: {"signal.interests.entities": {entity_id: score, ...}}
    # or {"entities": [{"id": ..., "score": ...}]}
    id_to_score: dict[str, float] = {}

    for key, val in explain.items():
        if key in ("warning", "aggregate", "average"):
            continue
        if isinstance(val, dict):
            for eid, score in val.items():
                try:
                    id_to_score[str(eid)] = float(score)
                except (TypeError, ValueError):
                    continue
        elif isinstance(val, list):
            for item in val:
                if not isinstance(item, dict):
                    continue
                eid = item.get("id") or item.get("entity_id")
                score = item.get("score") or item.get("affinity") or 0
                if eid:
                    try:
                        id_to_score[str(eid)] = float(score)
                    except (TypeError, ValueError):
                        id_to_score[str(eid)] = 0.0

    influences: list[Influence] = []
    for res in resolutions:
        if not res.resolved:
            continue
        score = None
        if res.entity_id and res.entity_id in id_to_score:
            score = id_to_score[res.entity_id]
        # Tag influence keys are less common; still surface resolved anchors with score 0
        # only when we have at least one scored match overall.
        if score is None:
            continue
        influences.append(
            Influence(
                anchor=res.input,
                matched_name=res.matched_name or res.input,
                score=score,
            )
        )

    influences.sort(key=lambda i: i.score, reverse=True)
    # If explainability missing but we have anchors, soft-fill from resolved entities
    # so the UI still shows cultural grounding (score 0 marks "unscored").
    if not influences and resolutions:
        for res in resolutions:
            if res.resolved and res.entity_id:
                influences.append(
                    Influence(
                        anchor=res.input,
                        matched_name=res.matched_name or res.input,
                        score=0.0,
                    )
                )
                break
    return influences[:5]


def parse_place(
    entity: dict[str, Any],
    resolutions: list[AnchorResolution],
) -> Optional[PlaceCandidate]:
    eid = _entity_id(entity)
    name = str(entity.get("name") or entity.get("title") or "").strip()
    if not eid or not name:
        return None
    return PlaceCandidate(
        entity_id=eid,
        name=name,
        category=_category_label(entity),
        address=_address(entity),
        tags=_tag_names(entity),
        affinity=_affinity(entity),
        influenced_by=_parse_explainability(entity, resolutions),
        image_url=_image_url(entity),
        raw_properties=entity.get("properties") if isinstance(entity.get("properties"), dict) else {},
    )


class PlaceFinder:
    """Find places for a city phase using taste signals + category tags."""

    def __init__(self, client: QlooClient, categories: Optional[CategoryResolver] = None):
        self.client = client
        self.categories = categories or CategoryResolver(client)

    async def find_for_phase(
        self,
        *,
        city: str,
        phase: str,
        resolutions: list[AnchorResolution],
        exclude_ids: Optional[list[str]] = None,
        take: int = 10,
        use_broad_tags: bool = False,
        skip_tags: bool = False,
    ) -> list[PlaceCandidate]:
        city_cfg = CITY_REGISTRY[city]
        entity_ids = AnchorResolver.signal_entity_ids(resolutions)
        tag_ids = AnchorResolver.signal_tag_ids(resolutions)

        params: dict[str, Any] = {
            "filter.type": "urn:entity:place",
            "filter.location.query": city_cfg.location_query,
            "feature.explainability": True,
            "take": take,
        }
        if entity_ids:
            params["signal.interests.entities"] = entity_ids
        if tag_ids:
            params["signal.interests.tags"] = tag_ids
        if exclude_ids:
            params["filter.exclude.entities"] = exclude_ids

        if not skip_tags:
            cat_tags = await self.categories.tags_for_phase(phase, broad=use_broad_tags)
            if cat_tags:
                params["filter.tags"] = cat_tags
                params["operator.filter.tags"] = "union"

        # Need at least one primary signal (entities, interest tags, or we fail closed).
        if not entity_ids and not tag_ids:
            logger.warning("No taste signals for %s/%s — skipping insights call", city, phase)
            return []

        try:
            payload = await self.client.insights(params)
        except QlooError as exc:
            logger.warning("insights failed for %s/%s: %s", city, phase, exc)
            raise

        candidates: list[PlaceCandidate] = []
        for entity in _extract_entities(payload):
            place = parse_place(entity, resolutions)
            if place:
                candidates.append(place)

        candidates.sort(key=lambda p: (p.affinity is not None, p.affinity or 0.0), reverse=True)
        return candidates
