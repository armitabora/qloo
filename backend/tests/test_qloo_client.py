"""Unit tests for QlooClient: retries, errors, cache."""

from __future__ import annotations

import httpx
import pytest
import respx

from config import Settings
from qloo.client import (
    QlooAuthError,
    QlooClient,
    QlooForbiddenError,
    QlooNotFoundError,
    QlooRateLimitError,
)


BASE = "https://hackathon.api.qloo.com"


@pytest.mark.asyncio
@respx.mock
async def test_search_success(settings: Settings):
    route = respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(
            200,
            json={
                "results": [
                    {"entity_id": "abc", "name": "Radiohead", "type": "urn:entity:artist"}
                ]
            },
        )
    )
    async with QlooClient(settings=settings) as client:
        results = await client.search("Radiohead", types="urn:entity:artist", take=3)
    assert route.called
    assert results[0]["name"] == "Radiohead"
    assert client.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_search_404_returns_empty(settings: Settings):
    respx.get(f"{BASE}/search").mock(return_value=httpx.Response(404, json={"error": "No results"}))
    async with QlooClient(settings=settings) as client:
        results = await client.search("zzzz-unknown")
    assert results == []


@pytest.mark.asyncio
@respx.mock
async def test_auth_error_401(settings: Settings):
    respx.get(f"{BASE}/v2/insights").mock(
        return_value=httpx.Response(401, json={"error": "No API key found in request"})
    )
    async with QlooClient(settings=settings) as client:
        with pytest.raises(QlooAuthError):
            await client.insights({"filter.type": "urn:entity:place"})


@pytest.mark.asyncio
@respx.mock
async def test_forbidden_403(settings: Settings):
    respx.get(f"{BASE}/v2/insights").mock(
        return_value=httpx.Response(403, json={"error": "You do not have permission"})
    )
    async with QlooClient(settings=settings) as client:
        with pytest.raises(QlooForbiddenError):
            await client.insights({"filter.type": "urn:entity:music"})


@pytest.mark.asyncio
@respx.mock
async def test_retry_on_429_then_success(settings: Settings):
    route = respx.get(f"{BASE}/search").mock(
        side_effect=[
            httpx.Response(429, json={"error": "rate limited"}, headers={"Retry-After": "0"}),
            httpx.Response(200, json={"results": [{"entity_id": "1", "name": "Ok"}]}),
        ]
    )
    async with QlooClient(settings=settings) as client:
        results = await client.search("Ok")
    assert results[0]["name"] == "Ok"
    assert route.call_count == 2
    assert client.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_retry_exhausted_raises_rate_limit(settings: Settings):
    settings_no_cache = Settings(
        qloo_api_key="test-qloo-key",
        qloo_base_url=BASE,
        qloo_timeout_seconds=2.0,
        qloo_max_retries=1,
        qloo_cache_ttl_seconds=0,
    )
    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(429, json={"error": "rate limited"}, headers={"Retry-After": "0"})
    )
    async with QlooClient(settings=settings_no_cache) as client:
        with pytest.raises(QlooRateLimitError):
            await client.search("x")


@pytest.mark.asyncio
@respx.mock
async def test_retry_on_500(settings: Settings):
    route = respx.get(f"{BASE}/v2/tags").mock(
        side_effect=[
            httpx.Response(500, json={"error": "boom"}),
            httpx.Response(200, json={"results": {"tags": [{"id": "urn:tag:x", "name": "cafe"}]}}),
        ]
    )
    async with QlooClient(settings=settings) as client:
        tags = await client.tags("cafe")
    assert tags[0]["name"] == "cafe"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_cache_hits_skip_http(settings: Settings):
    route = respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(
            200, json={"results": [{"entity_id": "1", "name": "Cached"}]}
        )
    )
    async with QlooClient(settings=settings) as client:
        a = await client.search("Cached", types="urn:entity:artist")
        b = await client.search("Cached", types="urn:entity:artist")
    assert a == b
    assert route.call_count == 1
    assert client.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_timeout_retries_then_raises(settings: Settings):
    def _timeout(_request: httpx.Request):
        raise httpx.ReadTimeout("slow")

    route = respx.get(f"{BASE}/search").mock(side_effect=_timeout)
    settings_fast = Settings(
        qloo_api_key="test-qloo-key",
        qloo_base_url=BASE,
        qloo_timeout_seconds=0.1,
        qloo_max_retries=1,
        qloo_cache_ttl_seconds=0,
    )
    async with QlooClient(settings=settings_fast) as client:
        with pytest.raises(Exception) as exc:
            await client.search("slow")
    assert "timeout" in str(exc.value).lower() or "slow" in str(exc.value).lower()
    assert route.call_count == 2


@pytest.mark.asyncio
async def test_missing_api_key_raises_auth():
    bare = Settings(qloo_api_key="", qloo_base_url=BASE, qloo_max_retries=0)
    async with QlooClient(settings=bare) as client:
        with pytest.raises(QlooAuthError):
            await client.search("x")


@pytest.mark.asyncio
@respx.mock
async def test_insights_flattens_list_params(settings: Settings):
    route = respx.get(f"{BASE}/v2/insights").mock(
        return_value=httpx.Response(200, json={"results": {"entities": []}})
    )
    async with QlooClient(settings=settings) as client:
        await client.insights(
            {
                "filter.type": "urn:entity:place",
                "signal.interests.entities": ["id1", "id2"],
                "filter.tags": ["urn:tag:a", "urn:tag:b"],
                "feature.explainability": True,
                "take": 5,
            }
        )
    request = route.calls.last.request
    assert "id1%2Cid2" in str(request.url) or "id1,id2" in str(request.url)
    assert "feature.explainability=true" in str(request.url)


@pytest.mark.asyncio
@respx.mock
async def test_tags_parse_nested_results(settings: Settings):
    respx.get(f"{BASE}/v2/tags").mock(
        return_value=httpx.Response(
            200,
            json={"results": {"tags": [{"id": "urn:tag:genre:place:cafe", "name": "Cafe"}]}},
        )
    )
    async with QlooClient(settings=settings) as client:
        tags = await client.tags("cafe")
    assert tags[0]["id"].endswith("cafe")
