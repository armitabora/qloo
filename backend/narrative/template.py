"""Template narratives grounded in Qloo explainability and tags (no LLM)."""

from __future__ import annotations

import re
from typing import Optional

from models import AnchorResolution, ItineraryRequest
from qloo.places import PlaceCandidate, _is_useful_tag

_OPENERS = {
    "MORNING": "Start your morning at {name}",
    "AFTERNOON": "Spend your afternoon at {name}",
    "EVENING": "For dinner, head to {name}",
    "NIGHT": "Close the night at {name}",
}

_PHASE_ORDER = ("MORNING", "AFTERNOON", "EVENING", "NIGHT")

# Dish / menu tags make awkward paired descriptors ("stylish and chocolate cookies").
_DESCRIPTOR_WEAK = re.compile(
    r"assorted|sashimi|cookie|ramen|burger|pizza|sandwich|menu|dish|"
    r"delivery|takeout|nfc|payment",
    re.IGNORECASE,
)


def _anchor_phrase(resolutions: list[AnchorResolution]) -> str:
    names = [r.matched_name or r.input for r in resolutions if r.resolved]
    if not names:
        names = [r.input for r in resolutions]
    if not names:
        return "your taste"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{', '.join(names[:-1])}, and {names[-1]}"


def _phase_index(phase: str) -> int:
    phase = phase.upper()
    try:
        return _PHASE_ORDER.index(phase)
    except ValueError:
        return 0


def _anchor_for_phase(
    phase: str,
    resolutions: list[AnchorResolution],
    place: PlaceCandidate,
) -> tuple[str, Optional[float]]:
    """Pick which anchor to cite and its explainability score (if any)."""
    idx = _phase_index(phase)

    if place.influenced_by:
        if len(place.influenced_by) > 1:
            inf = place.influenced_by[idx % len(place.influenced_by)]
        else:
            inf = place.influenced_by[0]
        return inf.matched_name, inf.score

    # No per-place explainability: rotate user anchors by phase / kind.
    kind_priority = {
        "MORNING": ("music", "vibe", "film"),
        "AFTERNOON": ("film", "vibe", "music"),
        "EVENING": ("film", "music", "vibe"),
        "NIGHT": ("music", "film", "vibe"),
    }.get(phase.upper(), ("music", "film", "vibe"))

    resolved = [r for r in resolutions if r.resolved]
    by_kind = {r.kind: r for r in resolved}
    for kind in kind_priority:
        if kind in by_kind:
            r = by_kind[kind]
            return r.matched_name or r.input, None

    resolved_all = [r for r in resolutions if r.input]
    if resolved_all:
        r = resolved_all[idx % len(resolved_all)]
        return r.matched_name or r.input, None
    return _anchor_phrase(resolutions), None


def _descriptor_tag_score(tag: str) -> float:
    t = tag.lower()
    score = 0.0
    if _DESCRIPTOR_WEAK.search(t):
        score -= 10.0
    if len(t.split()) > 3:
        score -= 3.0
    if t in ("place", "restaurant", "bar", "cafe"):
        score += 1.0
    if any(
        x in t
        for x in (
            "museum",
            "gallery",
            "stylish",
            "themed",
            "gaming",
            "jazz",
            "historic",
            "intimate",
            "lively",
            "cultural",
            "vinyl",
            "indie",
        )
    ):
        score += 4.0
    return score


def _descriptor(place: PlaceCandidate) -> str:
    clean = [t for t in place.tags if _is_useful_tag(t)]
    clean.sort(key=_descriptor_tag_score, reverse=True)
    clean = [t for t in clean if _descriptor_tag_score(t) > -5]

    if place.category and _is_useful_tag(place.category):
        cat = place.category.lower()
        if clean and _descriptor_tag_score(clean[0]) > 2:
            return f"a {cat} with a {clean[0].lower()} feel"
        return f"a {cat}"

    if not clean:
        return "a local spot"
    if len(clean) == 1:
        return f"a {clean[0].lower()} spot"
    if _descriptor_tag_score(clean[1]) > 0:
        return f"a {clean[0].lower()} spot with a {clean[1].lower()} feel"
    return f"a {clean[0].lower()} spot"


def _influence_sentence(
    phase: str,
    place: PlaceCandidate,
    resolutions: list[AnchorResolution],
    anchors: str,
) -> str:
    anchor, score = _anchor_for_phase(phase, resolutions, place)
    idx = _phase_index(phase)
    strong = score is not None and score > 0.3

    if strong:
        templates = [
            (
                "Qloo's taste graph ranked it highly for fans of {anchor}: "
                "a cross-domain match, not a generic list."
            ),
            (
                "Your taste signal for {anchor} is what pushed this venue up "
                "in Qloo's insights for this part of the day."
            ),
            (
                "Qloo connected {anchor} to places with this character; "
                "this one landed near the top of that cluster."
            ),
            (
                "Fans of {anchor} tend to overlap with spots like this in "
                "Qloo's cultural graph. That's why it's here."
            ),
        ]
        return templates[idx % len(templates)].format(anchor=anchor)

    if score is not None or place.influenced_by:
        templates = [
            (
                "It surfaced because Qloo mapped your interest in {anchor} "
                "onto real venues in the city."
            ),
            (
                "{anchor} was one of the taste inputs Qloo used when "
                "filtering recommendations for this stop."
            ),
            (
                "Qloo's entity signals included {anchor}; this place fit "
                "that slice of your profile."
            ),
            (
                "This pick reflects how {anchor} reads in Qloo's graph: "
                "similar audiences, similar spaces."
            ),
        ]
        return templates[idx % len(templates)].format(anchor=anchor)

    templates = [
        f"Matched to {anchors} via Qloo's cross-domain taste data.",
        f"Qloo used your anchors ({anchors}) to shape this leg of the day.",
        f"Chosen from taste signals around {anchors}, not a static travel list.",
        f"Grounded in Qloo insights tied to {anchors}.",
    ]
    return templates[idx % len(templates)]


def narrative_for_place(
    *,
    phase: str,
    place: PlaceCandidate,
    resolutions: list[AnchorResolution],
    request: ItineraryRequest,
) -> str:
    opener_tmpl = _OPENERS.get(phase.upper(), f"{phase.title()} at {{name}}")
    opener = opener_tmpl.format(name=place.name)
    descriptor = _descriptor(place)
    influence = _influence_sentence(
        phase, place, resolutions, _anchor_phrase(resolutions)
    )
    desc = descriptor[0].upper() + descriptor[1:] if descriptor else descriptor
    return f"{opener}. {desc}. {influence}"


def narrative_for_fallback(
    *,
    phase: str,
    venue: str,
    category: str,
    resolutions: list[AnchorResolution],
    existing: Optional[str] = None,
) -> str:
    if existing:
        return existing
    anchors = _anchor_phrase(resolutions)
    return (
        f"{phase.title()} at {venue} ({category or 'local favorite'}) "
        f"selected as a safety-net stand-in while live taste data was unavailable, "
        f"still tuned toward {anchors}."
    )


def build_narratives(
    *,
    request: ItineraryRequest,
    resolutions: list[AnchorResolution],
    places: list[Optional[PlaceCandidate]],
    fallback_slots: list[Optional[dict]],
    phases: tuple[str, ...] = _PHASE_ORDER,
) -> list[str]:
    out: list[str] = []
    for i, phase in enumerate(phases):
        place = places[i] if i < len(places) else None
        fb = fallback_slots[i] if i < len(fallback_slots) else None
        if place is not None:
            out.append(
                narrative_for_place(
                    phase=phase,
                    place=place,
                    resolutions=resolutions,
                    request=request,
                )
            )
        elif fb is not None:
            out.append(
                narrative_for_fallback(
                    phase=phase,
                    venue=fb.get("venue", "a local spot"),
                    category=fb.get("category", ""),
                    resolutions=resolutions,
                    existing=fb.get("vibe_narrative"),
                )
            )
        else:
            out.append(
                f"{phase.title()} stop unavailable for this vibe. Try different anchors."
            )
    return out
