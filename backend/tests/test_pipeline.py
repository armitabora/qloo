"""Pipeline degradation ladder tests."""

from __future__ import annotations

import httpx
import pytest
import respx

from config import Settings
from models import ItineraryRequest
from pipeline import NoAnchorsResolvedError, generate_itinerary
from qloo.client import QlooClient
from tests.fixtures.synthetic import (
    PHASE_TAG_RESPONSES,
    insights_places,
    place_entity,
    search_artist,
    search_film,
    tags_vibe,
)

BASE = "https://hackathon.api.qloo.com"


def _mock_tags(respx_mock):
    def handler(request: httpx.Request) -> httpx.Response:
        q = request.url.params.get("filter.query", "")
        body = PHASE_TAG_RESPONSES.get(q) or tags_vibe(q)
        return httpx.Response(200, json=body)

    respx_mock.get(f"{BASE}/v2/tags").mock(side_effect=handler)


def _phase_places():
    return {
        "MORNING": place_entity(entity_id="p-m", name="Morning Cafe", tag="Cafe"),
        "AFTERNOON": place_entity(
            entity_id="p-a", name="Afternoon Gallery", tag="Museum", affinity=0.7
        ),
        "EVENING": place_entity(
            entity_id="p-e", name="Evening Ramen", tag="Restaurant", affinity=0.75
        ),
        "NIGHT": place_entity(
            entity_id="p-n", name="Night Bar", tag="Bar", affinity=0.66
        ),
    }


@pytest.mark.asyncio
@respx.mock
async def test_full_pipeline_template_narratives(settings: Settings):
    _mock_tags(respx)
    respx.get(f"{BASE}/search").mock(
        side_effect=[
            httpx.Response(200, json=search_artist()),
            httpx.Response(200, json=search_film()),
        ]
    )

    places = _phase_places()

    def insights_handler(request: httpx.Request) -> httpx.Response:
        # Route by category tag so parallel phases get distinct venues.
        tags_param = request.url.params.get("filter.tags", "")
        if "cafe" in tags_param or "coffee" in tags_param or "bakery" in tags_param:
            entity = places["MORNING"]
        elif "museum" in tags_param or "gallery" in tags_param or "bookstore" in tags_param or "record" in tags_param:
            entity = places["AFTERNOON"]
        elif "restaurant" in tags_param:
            entity = places["EVENING"]
        elif "bar" in tags_param or "jazz" in tags_param or "venue" in tags_param:
            entity = places["NIGHT"]
        else:
            entity = places["MORNING"]
        return httpx.Response(200, json=insights_places([entity]))

    respx.get(f"{BASE}/v2/insights").mock(side_effect=insights_handler)

    settings_no_gemini = Settings(
        qloo_api_key="test-qloo-key",
        qloo_base_url=BASE,
        gemini_api_key="",
        qloo_cache_ttl_seconds=0,
        qloo_max_retries=0,
    )
    async with QlooClient(settings=settings_no_gemini) as client:
        resp = await generate_itinerary(
            ItineraryRequest(city="Tokyo", music="Nujabes", film="Studio Ghibli"),
            client=client,
        )

    assert resp.city == "Tokyo"
    assert len(resp.stops) == 4
    assert resp.meta.narrative_engine == "template"
    assert not resp.is_fallback
    assert all(s.source == "qloo" for s in resp.stops)
    venues = {s.venue for s in resp.stops}
    assert len(venues) == 4
    assert any(a.resolved for a in resp.anchors_resolved)
    assert "Nujabes" in resp.stops[0].vibe_narrative or "Studio Ghibli" in resp.stops[0].vibe_narrative


@pytest.mark.asyncio
@respx.mock
async def test_all_anchors_unresolved_raises(settings: Settings):
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(404, json={"error": "No results"}))
    respx.get(f"{BASE}/v2/tags").mock(return_value=httpx.Response(404, json={"error": "No results"}))
    settings_local = Settings(
        qloo_api_key="test-qloo-key",
        qloo_base_url=BASE,
        qloo_cache_ttl_seconds=0,
        qloo_max_retries=0,
    )
    async with QlooClient(settings=settings_local) as client:
        with pytest.raises(NoAnchorsResolvedError):
            await generate_itinerary(
                ItineraryRequest(city="Tokyo", music="zzznobody"),
                client=client,
            )


@pytest.mark.asyncio
@respx.mock
async def test_qloo_down_uses_fallback(settings: Settings):
    _mock_tags(respx)
    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json=search_artist())
    )
    respx.get(f"{BASE}/v2/insights").mock(
        return_value=httpx.Response(500, json={"error": "down"})
    )
    settings_local = Settings(
        qloo_api_key="test-qloo-key",
        qloo_base_url=BASE,
        qloo_cache_ttl_seconds=0,
        qloo_max_retries=0,
    )
    async with QlooClient(settings=settings_local) as client:
        resp = await generate_itinerary(
            ItineraryRequest(city="Tokyo", music="Nujabes"),
            client=client,
        )
    # Either full fallback or mixed — at least honest source labels
    assert len(resp.stops) == 4
    assert resp.is_fallback or any(s.source == "fallback" for s in resp.stops)


@pytest.mark.asyncio
async def test_missing_qloo_key_serves_fallback():
    settings_local = Settings(qloo_api_key="", gemini_api_key="")
    from narrative.engine import NarrativeEngine

    client = QlooClient(settings=settings_local)
    resp = await generate_itinerary(
        ItineraryRequest(city="New York", vibe="lo-fi"),
        client=client,
        narrative=NarrativeEngine(settings=settings_local),
        settings=settings_local,
    )
    assert resp.is_fallback
    assert all(s.source == "fallback" for s in resp.stops)
    assert resp.city == "New York"
