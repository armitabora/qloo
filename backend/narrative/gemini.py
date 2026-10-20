"""Gemini structured narratives with venue-name validation."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

from config import Settings, get_settings
from models import AnchorResolution, ItineraryRequest
from qloo.places import PlaceCandidate

logger = logging.getLogger("vibe.narrative.gemini")


class GeminiNarrativeError(Exception):
    pass


def _lazy_client(api_key: str):
    from google import genai

    return genai.Client(api_key=api_key)


def _venue_names(places: list[Optional[PlaceCandidate]], fallback_slots: list[Optional[dict]]) -> list[str]:
    names: list[str] = []
    for i in range(4):
        place = places[i] if i < len(places) else None
        fb = fallback_slots[i] if i < len(fallback_slots) else None
        if place is not None:
            names.append(place.name)
        elif fb is not None:
            names.append(str(fb.get("venue") or f"Stop {i+1}"))
        else:
            names.append(f"Stop {i+1}")
    return names


def _build_prompt(
    request: ItineraryRequest,
    resolutions: list[AnchorResolution],
    places: list[Optional[PlaceCandidate]],
    fallback_slots: list[Optional[dict]],
) -> str:
    venues = _venue_names(places, fallback_slots)
    anchors = [
        {
            "input": r.input,
            "kind": r.kind,
            "matched": r.matched_name,
            "resolved": r.resolved,
        }
        for r in resolutions
    ]
    stops_payload = []
    phases = ("MORNING", "AFTERNOON", "EVENING", "NIGHT")
    for i, phase in enumerate(phases):
        place = places[i] if i < len(places) else None
        entry: dict[str, Any] = {"phase": phase, "venue": venues[i]}
        if place is not None:
            entry["tags"] = place.tags
            entry["category"] = place.category
            entry["influenced_by"] = [
                {"anchor": inf.anchor, "matched_name": inf.matched_name, "score": inf.score}
                for inf in place.influenced_by
            ]
        stops_payload.append(entry)

    return (
        "You are an editorial cultural travel concierge.\n"
        f"City: {request.city}\n"
        f"User anchors (JSON): {json.dumps(anchors)}\n"
        f"Stops (JSON): {json.dumps(stops_payload)}\n\n"
        "Write exactly 4 short vibe narratives (1–2 sentences each, under 40 words).\n"
        "Each narrative MUST mention the exact venue name for that stop.\n"
        "Ground the reason in the user's anchors and any influenced_by / tags provided.\n"
        "Do not invent extra venues. Do not number the lines with 1. 2. 3. 4.\n"
        'Return ONLY valid JSON: {"narratives": ["...", "...", "...", "..."]}'
    )


def validate_narratives(narratives: list[str], venue_names: list[str]) -> bool:
    if len(narratives) != 4:
        return False
    for text, venue in zip(narratives, venue_names):
        if not text or not text.strip():
            return False
        # Require venue name (case-insensitive) somewhere in the narrative.
        if venue.lower() not in text.lower():
            # Allow partial match on first meaningful token (e.g. "Lion" from "Lion Kissaten")
            tokens = [t for t in re.split(r"\W+", venue) if len(t) > 3]
            if not tokens or not any(t.lower() in text.lower() for t in tokens[:2]):
                return False
    return True


async def generate_with_gemini(
    *,
    request: ItineraryRequest,
    resolutions: list[AnchorResolution],
    places: list[Optional[PlaceCandidate]],
    fallback_slots: list[Optional[dict]],
    settings: Optional[Settings] = None,
    client: Any = None,
) -> list[str]:
    settings = settings or get_settings()
    if not settings.has_gemini_key and client is None:
        raise GeminiNarrativeError("GEMINI_API_KEY not configured")

    prompt = _build_prompt(request, resolutions, places, fallback_slots)
    venues = _venue_names(places, fallback_slots)

    try:
        genai_client = client or _lazy_client(settings.gemini_api_key)
        # google-genai is sync; run as-is for hackathon simplicity.
        response = genai_client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
        )
        text = (getattr(response, "text", None) or "").strip()
        if not text:
            raise GeminiNarrativeError("Empty Gemini response")

        # Extract JSON object even if wrapped in fences.
        match = re.search(r"\{[\s\S]*\}", text)
        if not match:
            raise GeminiNarrativeError("Gemini response was not JSON")
        data = json.loads(match.group(0))
        narratives = data.get("narratives")
        if not isinstance(narratives, list):
            raise GeminiNarrativeError("Missing narratives array")
        narratives = [str(x).strip() for x in narratives]
        if not validate_narratives(narratives, venues):
            raise GeminiNarrativeError("Narrative failed venue-name validation")
        return narratives[:4]
    except GeminiNarrativeError:
        raise
    except Exception as exc:
        raise GeminiNarrativeError(str(exc)) from exc
