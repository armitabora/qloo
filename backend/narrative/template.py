"""Template narratives grounded in Qloo explainability and tags (no LLM)."""

from __future__ import annotations

from typing import Optional

from models import AnchorResolution, ItineraryRequest
from qloo.places import PlaceCandidate


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


def _influence_phrase(place: PlaceCandidate) -> str:
    if not place.influenced_by:
        return ""
    top = place.influenced_by[0]
    if top.score and top.score > 0:
        return f" strongly pulled by your affinity for {top.matched_name}"
    return f" echoing {top.matched_name}"


def _tag_phrase(place: PlaceCandidate) -> str:
    if not place.tags:
        return place.category or "this spot"
    if len(place.tags) == 1:
        return place.tags[0]
    return f"{place.tags[0]} with {place.tags[1]} energy"


def narrative_for_place(
    *,
    phase: str,
    place: PlaceCandidate,
    resolutions: list[AnchorResolution],
    request: ItineraryRequest,
) -> str:
    anchors = _anchor_phrase(resolutions)
    influence = _influence_phrase(place)
    tags = _tag_phrase(place)
    city = request.city
    phase_l = phase.title()

    return (
        f"{phase_l} at {place.name} — a {tags} stop in {city}"
        f"{influence}. Because you love {anchors}, this place fits the same "
        f"cultural frequency rather than a generic top-10 list."
    )


def narrative_for_fallback(
    *,
    phase: str,
    venue: str,
    category: str,
    resolutions: list[AnchorResolution],
    existing: Optional[str] = None,
) -> str:
    if existing:
        # Keep curated fallback copy when present — still honest via source=fallback.
        return existing
    anchors = _anchor_phrase(resolutions)
    return (
        f"{phase.title()} at {venue} ({category or 'local favorite'}) "
        f"selected as a safety-net stand-in while live taste data was unavailable — "
        f"still tuned toward {anchors}."
    )


def build_narratives(
    *,
    request: ItineraryRequest,
    resolutions: list[AnchorResolution],
    places: list[Optional[PlaceCandidate]],
    fallback_slots: list[Optional[dict]],
    phases: tuple[str, ...] = ("MORNING", "AFTERNOON", "EVENING", "NIGHT"),
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
            out.append(f"{phase.title()} stop unavailable for this vibe — try different anchors.")
    return out
