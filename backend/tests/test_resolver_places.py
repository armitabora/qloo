"""Tests for AnchorResolver and PlaceFinder."""

from __future__ import annotations

import httpx
import pytest
import respx

from config import Settings
from qloo.categories import CategoryResolver
from qloo.client import QlooClient
from qloo.places import PlaceFinder, parse_place
from qloo.resolver import AnchorResolver, looks_like_gibberish, match_score
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


def test_match_score_rejects_nonsense_and_loose_names():
    assert looks_like_gibberish("asdasd")
    assert looks_like_gibberish("asdf")
    assert looks_like_gibberish("hahaha")
    assert looks_like_gibberish("sdasd")
    assert looks_like_gibberish("sada")
    assert looks_like_gibberish("asda")
    assert looks_like_gibberish("sda")
    assert not looks_like_gibberish("Nujabes")
    assert not looks_like_gibberish("Coco")
    assert not looks_like_gibberish("BTS")
    assert not looks_like_gibberish("lo-fi")
    assert not looks_like_gibberish("Sade")
    assert not looks_like_gibberish("Daft Punk")
    assert not looks_like_gibberish("jazz")
    assert not looks_like_gibberish("pop")
    assert not looks_like_gibberish("sad")
    assert match_score("sada", "Sada") == 0
    assert match_score("asda", "ASDA") == 0
    assert match_score("sda", "S. Dali Museum") == 0
    assert match_score("sda", "S. Dali Museum", partial=True) == 0
    assert match_score("asdasd", "Asdasd") == 0
    assert match_score("Studio Ghibli", "Picsart Photo Studio") == 0
    assert match_score("Studio Ghibli", "Ghibli") >= 60
    assert match_score("Studio Ghibli", "Studio Ghibli") == 100
    assert match_score("ghibli", "Studio Ghibli") >= 60
    assert match_score("Bay", "Michael Bay") >= 60
    assert match_score("radio", "Radiohead") >= 60
    assert match_score("cozy lo-fi", "Lo-Fi", partial=True) >= 60
    assert match_score("jazz", "Jazz") >= 60


@pytest.mark.asyncio
@respx.mock
async def test_gibberish_anchor_does_not_search(settings: Settings):
    route = respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json=search_film("Sada", "ent-sada"))
    )
    async with QlooClient(settings=settings) as client:
        resolver = AnchorResolver(client)
        music = await resolver.resolve_music("sdasd")
        film = await resolver.resolve_film("sada")
        vibe = await resolver.resolve_vibe("asda")
    assert not music.resolved
    assert not film.resolved
    assert not vibe.resolved
    assert route.call_count == 0


@pytest.mark.asyncio
@respx.mock
async def test_short_nonsense_does_not_fuzzy_match(settings: Settings):
    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json=search_artist("S. Dali Museum", "ent-dali"))
    )
    respx.get(f"{BASE}/v2/tags").mock(
        return_value=httpx.Response(
            200,
            json={"results": {"tags": [{"id": "urn:tag:place:dali", "name": "S. Dali Museum"}]}},
        )
    )
    async with QlooClient(settings=settings) as client:
        resolver = AnchorResolver(client)
        music = await resolver.resolve_music("sda")
        vibe = await resolver.resolve_vibe("sda")
    assert not music.resolved
    assert music.entity_id is None
    assert not vibe.resolved
    assert vibe.tag_id is None


@pytest.mark.asyncio
@respx.mock
async def test_short_real_name_still_resolves(settings: Settings):
    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json=search_artist("BTS", "ent-bts"))
    )
    async with QlooClient(settings=settings) as client:
        result = await AnchorResolver(client).resolve_music("BTS")
    assert result.resolved
    assert result.matched_name == "BTS"
    assert result.entity_id == "ent-bts"


def test_category_prefers_venue_over_occasion():
    entity = place_entity(entity_id="place-1", name="BAR Zolddich", tag="Birthday")
    entity["tags"] = [
        {"name": "Birthday", "id": "urn:tag:good_for:birthday"},
        {"name": "Bar", "id": "urn:tag:genre:place:bar"},
        {"name": "Cocktails", "id": "urn:tag:offering:cocktails"},
    ]
    place = parse_place(entity, [])
    assert place is not None
    assert place.category == "Bar"
    assert "Birthday" not in place.tags


def test_parse_place_upgrades_thumbnail_image_url():
    entity = place_entity(entity_id="place-1", name="Lion Kissaten")
    entity["properties"]["image"]["url"] = (
        "https://lh3.googleusercontent.com/p/AF1QipThumb=s200-c"
    )
    place = parse_place(entity, [])
    assert place is not None
    assert place.image_url.endswith("=s1600")

    entity["properties"]["image"]["url"] = (
        "https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference=abc"
    )
    place = parse_place(entity, [])
    assert place is not None
    assert "maxwidth=1600" in place.image_url
