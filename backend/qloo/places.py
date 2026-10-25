"""Per-phase place recommendations via /v2/insights."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from config import CITY_REGISTRY
from models import AnchorResolution, Influence
from qloo.categories import CategoryResolver
from qloo.client import QlooClient, QlooError
from qloo.resolver import AnchorResolver

logger = logging.getLogger("vibe.qloo.places")

# Junk patterns found in live Qloo responses (age ranges, payments, amenities,
# and occasion labels that are not what a place is).
_TAG_JUNK = re.compile(
    r"^\d[\d\s\-]+$"  # pure numbers / age ranges: "25 29", "30 34"
    r"|nfc|mobile payment|credit card"  # payment methods
    r"|mastercard|visa|amex"
    r"|restroom|wheelchair|accessible"
    r"|air condition|flat screen|towel"
    r"|front desk|check.?in|check.?out"
    r"|parking\b|wifi\b|wi-fi"
    r"|delivery\b|drive.?thru"  # purely operational
    r"|^place$"  # too generic to be useful
    r"|\bbirthday\b|\banniversary\b|\bwedding\b|\bbachelorette\b"
    r"|\bdate night\b|\bkid friendly\b|\bfamily friendly\b|\bgood for groups\b"
    r"|\btourists?\b",
    re.IGNORECASE,
)

# Amenity and audience labels that contain a venue word but are not the place type.
# "Bar service", "Solo diners", and "Gift shop" were showing up as the description.
_SKIP_AS_VENUE = re.compile(
    r"\bservice\b|\bonsite\b|\bsolo diners?\b|\bgift shops?\b|\bgood for\b|\btakeout\b|\btakeaway\b",
    re.IGNORECASE,
)

_NAME_KIND = re.compile(
    r"\b(museums?|galleries|restaurants?|caf[eé]s?|coffees?|izakayas?|ramens?|"
    r"baker(?:y|ies)|nightclubs?|pubs?|lounges?|bars?|parks?|temples?|shrines?)\b",
    re.IGNORECASE,
)

_VENUE_TIERS: tuple[tuple[int, re.Pattern[str]], ...] = (
    (
        40,
        re.compile(
            r"\b(cocktail bars?|jazz clubs?|music venues?|record stores?|"
            r"coffee shops?|art galleries|bookstores?|book shops?)\b",
            re.IGNORECASE,
        ),
    ),
    (
        30,
        re.compile(
            r"\b(museums?|galleries|restaurants?|caf[eé]s?|izakaya|ramen|"
            r"baker(?:y|ies)|nightclubs?|pubs?|lounges?|kissaten|tea houses?|"
            r"diners?|bistros?)\b",
            re.IGNORECASE,
        ),
    ),
    (25, re.compile(r"\bbars?\b", re.IGNORECASE)),
    (
        15,
        re.compile(
            r"\b(parks?|temples?|shrines?|cinemas?|theat(?:er|re)s?|markets?|"
            r"brewer(?:y|ies)|winer(?:y|ies)|karaoke)\b",
            re.IGNORECASE,
        ),
    ),
)


def _is_useful_tag(name: str) -> bool:
    return bool(name) and len(name) >= 3 and not _TAG_JUNK.search(name)


def venue_rank(name: str) -> int:
    """Higher means the label is a real kind of place. 0 means don't use it."""
    if not name or not _is_useful_tag(name) or _SKIP_AS_VENUE.search(name):
        return 0
    best = 0
    for score, pattern in _VENUE_TIERS:
        if pattern.search(name):
            best = max(best, score)
    return best


def best_venue_label(labels: list[str]) -> str:
    best_name = ""
    best_score = 0
    for label in labels:
        score = venue_rank(label)
        if score > best_score:
            best_score = score
            best_name = label.strip()
    return best_name


def _canonical_kind(word: str) -> str:
    w = word.casefold().replace("é", "e")
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
        return w[:-1]
    return w


def kind_from_name(name: str) -> str:
    """When tags are amenities, the venue name is often the only real type."""
    if not name:
        return ""
    match = _NAME_KIND.search(name)
    if match:
        return _canonical_kind(match.group(1))
    compact = re.sub(r"[^a-z]", "", name.casefold())
    for suffix in ("museum", "cafe", "bar", "ramen", "izakaya"):
        if compact.endswith(suffix) and len(compact) > len(suffix):
            return suffix
    return ""


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


_SIZE_QUERY_KEYS = ("maxwidth", "maxheight", "w", "h", "width", "height")
_GOOGLE_SIZE_SUFFIX = re.compile(r"=[swh]\d+[a-z0-9=-]*$", re.IGNORECASE)
_PATH_DIMS = re.compile(r"/(\d{2,4})x(\d{2,4})/")


def _upgrade_image_url(url: str) -> str:
    """Prefer a larger raster when the source URL encodes a thumbnail size."""
    if not url:
        return url
    upgraded = url
    host = ""
    try:
        from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

        parts = urlsplit(url)
        host = (parts.hostname or "").lower()
        query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)]
        changed = False
        new_query = []
        for key, val in query:
            if key.lower() in _SIZE_QUERY_KEYS:
                try:
                    if int(val) < 1200:
                        new_query.append((key, "1600"))
                        changed = True
                        continue
                except ValueError:
                    pass
            new_query.append((key, val))
        path = parts.path
        if "googleusercontent.com" in host or "ggpht.com" in host:
            stripped, n = _GOOGLE_SIZE_SUFFIX.subn("=s1600", path)
            if n:
                path = stripped
                changed = True
        dim_match = _PATH_DIMS.search(path)
        if dim_match:
            try:
                if int(dim_match.group(1)) < 800 or int(dim_match.group(2)) < 800:
                    path = _PATH_DIMS.sub("/1600x1600/", path, count=1)
                    changed = True
            except ValueError:
                pass
        if changed:
            upgraded = urlunsplit(
                (parts.scheme, parts.netloc, path, urlencode(new_query), parts.fragment)
            )
    except Exception:
        upgraded = url

    if ("googleusercontent.com" in host or "ggpht.com" in host) and _GOOGLE_SIZE_SUFFIX.search(
        upgraded
    ):
        upgraded = _GOOGLE_SIZE_SUFFIX.sub("=s1600", upgraded)
    return upgraded


def _collect_image_urls(value: Any, depth: int = 0) -> list[str]:
    if depth > 4 or value is None:
        return []
    if isinstance(value, str) and value.startswith(("http://", "https://")):
        return [value]
    urls: list[str] = []
    if isinstance(value, dict):
        for key in ("original", "large", "full", "hires", "high_resolution", "url", "src", "href"):
            nested = value.get(key)
            if isinstance(nested, str) and nested.startswith(("http://", "https://")):
                urls.append(nested)
        for nested in value.values():
            if isinstance(nested, (dict, list)):
                urls.extend(_collect_image_urls(nested, depth + 1))
    elif isinstance(value, list):
        for item in value:
            urls.extend(_collect_image_urls(item, depth + 1))
    return urls


def _image_url(entity: dict[str, Any]) -> Optional[str]:
    props = entity.get("properties") or {}
    if not isinstance(props, dict):
        return None
    candidates: list[str] = []
    for key in ("image", "images", "photo", "photos"):
        candidates.extend(_collect_image_urls(props.get(key)))
    if not candidates:
        return None
    return _upgrade_image_url(candidates[0])


def _tag_names(entity: dict[str, Any], limit: int = 4) -> list[str]:
    tags = entity.get("tags") or []
    names: list[str] = []
    for t in tags:
        if isinstance(t, dict):
            name = t.get("name") or t.get("id")
        else:
            name = str(t)
        if name and _is_useful_tag(str(name)):
            names.append(str(name))
        if len(names) >= limit:
            break
    return names


def _tag_label(tag: Any) -> str:
    if isinstance(tag, dict):
        name = tag.get("name") or tag.get("id")
    else:
        name = str(tag)
    return str(name).strip() if name else ""


def _category_label(entity: dict[str, Any], fallback: str = "") -> str:
    """Venue type for the UI. Occasion tags like Birthday are not a type of place."""
    names = [
        label
        for t in (entity.get("tags") or [])
        if (label := _tag_label(t)) and _is_useful_tag(label)
    ]
    picked = best_venue_label(names)
    if not picked:
        inferred = kind_from_name(str(entity.get("name") or ""))
        picked = inferred[:1].upper() + inferred[1:] if inferred else ""
    if picked:
        return picked
    props = entity.get("properties") or {}
    if isinstance(props, dict) and props.get("business_type"):
        business = str(props["business_type"])
        if venue_rank(business):
            return business
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
