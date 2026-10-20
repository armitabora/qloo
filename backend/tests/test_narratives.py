"""Narrative template + Gemini validation tests."""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from config import Settings
from models import AnchorResolution, Influence, ItineraryRequest
from narrative.engine import NarrativeEngine
from narrative.gemini import GeminiNarrativeError, generate_with_gemini, validate_narratives
from narrative.template import build_narratives
from qloo.places import PlaceCandidate


def _place(name: str = "Lion Kissaten") -> PlaceCandidate:
    return PlaceCandidate(
        entity_id="p1",
        name=name,
        category="Cafe",
        tags=["Cafe", "Vinyl"],
        affinity=0.8,
        influenced_by=[Influence(anchor="Nujabes", matched_name="Nujabes", score=0.7)],
    )


def _resolutions() -> list[AnchorResolution]:
    return [
        AnchorResolution(
            input="Nujabes",
            kind="music",
            resolved=True,
            matched_name="Nujabes",
            entity_id="ent-artist-1",
        )
    ]


def test_template_cites_anchors_and_venue():
    request = ItineraryRequest(city="Tokyo", music="Nujabes")
    places = [_place(), None, _place("Afuri"), _place("Bar Martha")]
    fallback = [None, {"venue": "Flash Disc Ranch", "category": "Record Shop", "vibe_narrative": "Curated fallback copy."}, None, None]
    texts = build_narratives(
        request=request,
        resolutions=_resolutions(),
        places=places,
        fallback_slots=fallback,
    )
    assert len(texts) == 4
    assert "Lion Kissaten" in texts[0]
    assert "Nujabes" in texts[0]
    assert "Curated fallback copy." in texts[1]


def test_validate_narratives_requires_venue():
    venues = ["Lion Kissaten", "Flash Disc Ranch", "Afuri", "Bar Martha"]
    good = [
        "Lion Kissaten feels like Nujabes.",
        "Flash Disc Ranch crates match your taste.",
        "Afuri is clean and intentional.",
        "Bar Martha closes the night.",
    ]
    assert validate_narratives(good, venues)
    bad = list(good)
    bad[0] = "Some other cafe feels right."
    assert not validate_narratives(bad, venues)


@pytest.mark.asyncio
async def test_gemini_wrong_venue_raises_and_engine_falls_back():
    class FakeModels:
        def generate_content(self, **kwargs):
            payload = {
                "narratives": [
                    "Totally Wrong Cafe is perfect.",
                    "Flash Disc Ranch crates match your taste.",
                    "Afuri is clean and intentional.",
                    "Bar Martha closes the night.",
                ]
            }
            return SimpleNamespace(text=json.dumps(payload))

    class FakeClient:
        models = FakeModels()

    request = ItineraryRequest(city="Tokyo", music="Nujabes")
    places = [_place(), _place("Flash Disc Ranch"), _place("Afuri"), _place("Bar Martha")]
    settings = Settings(gemini_api_key="fake", gemini_model="gemini-2.0-flash")

    with pytest.raises(GeminiNarrativeError):
        await generate_with_gemini(
            request=request,
            resolutions=_resolutions(),
            places=places,
            fallback_slots=[None, None, None, None],
            settings=settings,
            client=FakeClient(),
        )

    engine = NarrativeEngine(settings=settings, gemini_client=FakeClient())
    texts, name = await engine.write(
        request=request,
        resolutions=_resolutions(),
        places=places,
        fallback_slots=[None, None, None, None],
    )
    assert name == "template"
    assert "Lion Kissaten" in texts[0]


@pytest.mark.asyncio
async def test_engine_uses_gemini_when_valid():
    class FakeModels:
        def generate_content(self, **kwargs):
            payload = {
                "narratives": [
                    "Lion Kissaten channels Nujabes.",
                    "Flash Disc Ranch crates match your taste.",
                    "Afuri is clean and intentional.",
                    "Bar Martha closes the night.",
                ]
            }
            return SimpleNamespace(text=json.dumps(payload))

    class FakeClient:
        models = FakeModels()

    request = ItineraryRequest(city="Tokyo", music="Nujabes")
    places = [_place(), _place("Flash Disc Ranch"), _place("Afuri"), _place("Bar Martha")]
    settings = Settings(gemini_api_key="fake")
    engine = NarrativeEngine(settings=settings, gemini_client=FakeClient())
    texts, name = await engine.write(
        request=request,
        resolutions=_resolutions(),
        places=places,
        fallback_slots=[None, None, None, None],
    )
    assert name == "gemini"
    assert texts[0].startswith("Lion Kissaten")
