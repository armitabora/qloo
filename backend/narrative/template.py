"""Template narratives grounded in Qloo explainability and tags (no LLM)."""

from __future__ import annotations

import re
from typing import Optional

from models import AnchorResolution, ItineraryRequest
from qloo.places import PlaceCandidate, _is_useful_tag, best_venue_label, kind_from_name, venue_rank

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
            "cocktail",
            "wine",
            "coffee",
            "ramen",
            "beer",
        )
    ):
        score += 4.0
    return score


_PLURALS = {
    "cocktails": "cocktail",
    "bars": "bar",
    "cafes": "cafe",
    "museums": "museum",
    "galleries": "gallery",
    "restaurants": "restaurant",
    "clubs": "club",
    "pubs": "pub",
    "lounges": "lounge",
}


def _plain(tag: str) -> str:
    word = tag.strip().lower()
    return _PLURALS.get(word, word)


def _with_article(phrase: str) -> str:
    phrase = phrase.strip()
    if not phrase:
        return ""
    article = "an" if phrase[0].lower() in "aeiou" else "a"
    return f"{article} {phrase}"


def _candidate_labels(place: PlaceCandidate) -> list[str]:
    labels: list[str] = []
    if place.category:
        labels.append(place.category)
    labels.extend(place.tags)
    seen: set[str] = set()
    out: list[str] = []
    for label in labels:
        key = label.strip().lower()
        if not key or key in seen or not _is_useful_tag(label):
            continue
        seen.add(key)
        out.append(label.strip())
    return out


def _venue_kind(place: PlaceCandidate) -> str:
    label = best_venue_label(_candidate_labels(place))
    if label:
        return _plain(label)
    return kind_from_name(place.name)


def _quality_word(place: PlaceCandidate, kind: str) -> str:
    labels = [t for t in place.tags if _is_useful_tag(t) and _descriptor_tag_score(t) > 2]
    labels.sort(key=_descriptor_tag_score, reverse=True)
    kind_l = kind.lower()
    for label in labels:
        if venue_rank(label):
            continue
        word = _plain(label)
        if not word or word in kind_l:
            continue
        return word
    return ""


def _descriptor(place: PlaceCandidate) -> str:
    """A grammatical kind of place, or "" when the only tags are junk."""
    kind = _venue_kind(place)
    quality = _quality_word(place, kind)
    if kind and quality:
        return _with_article(f"{quality} {kind}")
    if kind:
        return _with_article(kind)
    if quality:
        return _with_article(f"{quality} spot")
    return ""


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
            "People who like {anchor} often start the day in a place like this.",
            "A taste for {anchor} is what pulled it into the afternoon.",
            "Fans of {anchor} tend to spend the evening somewhere with this feel.",
            "People drawn to {anchor} tend to end the night in a room like this.",
        ]
        return templates[idx % len(templates)].format(anchor=anchor)

    if score is not None or place.influenced_by:
        templates = [
            "It fits the morning because it lines up with {anchor}.",
            "It fits the afternoon because it lines up with {anchor}.",
            "It fits the evening because it lines up with {anchor}.",
            "It fits the night because it lines up with {anchor}.",
        ]
        return templates[idx % len(templates)].format(anchor=anchor)

    templates = [
        f"The morning stop follows what you said you like: {anchors}.",
        f"The afternoon stop follows what you said you like: {anchors}.",
        f"The evening stop follows what you said you like: {anchors}.",
        f"The night stop follows what you said you like: {anchors}.",
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
    phrase = _descriptor(place)
    lead = f"{opener}, {phrase}." if phrase else f"{opener}."
    why = _influence_sentence(
        phase, place, resolutions, _anchor_phrase(resolutions)
    )
    return f"{lead} {why}"


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
