"""Tests for AnchorResolver and PlaceFinder."""

from __future__ import annotations

import httpx
import pytest
import respx

from config import Settings
from qloo.categories import CategoryResolver
from qloo.client import QlooClient
from qloo.places import PlaceFinder
from qloo.resolver import AnchorResolver
from tests.fixtures.synthetic import (
    PHASE_TAG_RESPONSES,
    insights_places,
    place_entity,
    search_artist,
    search_film,
    tags_vibe,
)

BASE = "https://hackathon.api.qloo.com"


def _mock_tag_discovery(respx_mock):
    def tag_handler(request: httpx.Request) -> httpx.Response:
        q = request.url.params.get("filter.query", "")
        body = PHASE_TAG_RESPONSES.get(q) or tags_vibe(q)
        return httpx.Response(200, json=body)

    respx_mock.get(f"{BASE}/v2/tags").mock(side_effect=tag_handler)


@pytest.mark.asyncio
@respx.mock
async def test_resolve_music_and_film(settings: Settings):
    # Film resolver searches brand, then movie, then person.
    respx.get(f"{BASE}/search").mock(
        side_effect=[
            httpx.Response(200, json=search_artist()),
            httpx.Response(200, json=search_film()),
            httpx.Response(200, json={"results": []}),
            httpx.Response(200, json={"results": []}),
        ]
    )
    async with QlooClient(settings=settings) as client:
        resolver = AnchorResolver(client)
        results = await resolver.resolve_all(music="Nujabes", film="Studio Ghibli")
    assert len(results) == 2
    assert results[0].resolved and results[0].entity_id == "ent-artist-1"
    assert results[1].resolved and results[1].kind == "film"
    assert results[1].matched_name == "Studio Ghibli"
    assert AnchorResolver.signal_entity_ids(results) == ["ent-artist-1", "ent-brand-1"]


@pytest.mark.asyncio
@respx.mock
async def test_resolve_vibe_to_tag(settings: Settings):
    respx.get(f"{BASE}/v2/tags").mock(return_value=httpx.Response(200, json=tags_vibe("cozy lo-fi")))
    async with QlooClient(settings=settings) as client:
        resolver = AnchorResolver(client)
        result = await resolver.resolve_vibe("cozy lo-fi")
    assert result.resolved
    assert result.tag_id
    assert result.kind == "vibe"


@pytest.mark.asyncio
@respx.mock
async def test_unresolved_anchor(settings: Settings):
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(404, json={"error": "No results"}))
    async with QlooClient(settings=settings) as client:
        resolver = AnchorResolver(client)
        result = await resolver.resolve_music("zzzxxyyqq-not-a-real-artist")
    assert not result.resolved
    assert result.entity_id is None


@pytest.mark.asyncio
@respx.mock
async def test_place_finder_parses_explainability(settings: Settings):
    _mock_tag_discovery(respx)
    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json=search_artist())
    )
    respx.get(f"{BASE}/v2/insights").mock(
        return_value=httpx.Response(
            200,
            json=insights_places(
                [
                    place_entity(
                        entity_id="place-1",
                        name="Lion Kissaten",
                        tag="Cafe",
                        influence_id="ent-artist-1",
                        influence_score=0.72,
                    )
                ]
            ),
        )
    )
    async with QlooClient(settings=settings) as client:
        resolver = AnchorResolver(client)
        resolutions = await resolver.resolve_all(music="Nujabes")
        finder = PlaceFinder(client, CategoryResolver(client))
        places = await finder.find_for_phase(
            city="Tokyo",
            phase="MORNING",
            resolutions=resolutions,
        )
    assert len(places) == 1
    assert places[0].name == "Lion Kissaten"
    assert places[0].affinity == 0.8
    assert places[0].influenced_by
    assert places[0].influenced_by[0].anchor == "Nujabes"
    assert places[0].influenced_by[0].score == 0.72
    assert places[0].image_url


@pytest.mark.asyncio
@respx.mock
async def test_place_finder_sends_location_and_tags(settings: Settings):
    _mock_tag_discovery(respx)
    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json=search_artist())
    )
    insights_route = respx.get(f"{BASE}/v2/insights").mock(
        return_value=httpx.Response(200, json=insights_places([]))
    )
    async with QlooClient(settings=settings) as client:
        resolutions = await AnchorResolver(client).resolve_all(music="Nujabes")
        await PlaceFinder(client).find_for_phase(
            city="New York",
            phase="EVENING",
            resolutions=resolutions,
            exclude_ids=["place-x"],
        )
    url = str(insights_route.calls.last.request.url)
    assert "filter.type=urn%3Aentity%3Aplace" in url or "filter.type=urn:entity:place" in url
    assert "New+York+City" in url or "New%20York%20City" in url
    assert "feature.explainability=true" in url
    assert "filter.exclude.entities" in url
