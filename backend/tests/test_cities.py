"""City registry and /api/cities endpoint tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from config import CITY_REGISTRY, REGION_LABELS, city_ids, load_city_registry
from main import app


def test_registry_has_thirty_cities():
    assert len(CITY_REGISTRY) == 30
    assert "Tokyo" in CITY_REGISTRY
    assert "New York" in CITY_REGISTRY
    assert "Paris" in CITY_REGISTRY
    assert "Mumbai" in CITY_REGISTRY
    assert "Sydney" in CITY_REGISTRY


def test_registry_regions_cover_all_buckets():
    regions = {cfg.region for cfg in CITY_REGISTRY.values()}
    assert regions == set(REGION_LABELS.keys())


def test_city_ids_sorted():
    ids = city_ids()
    assert ids == sorted(ids)
    assert len(ids) == 30


def test_load_city_registry_roundtrip():
    from config import _CITIES_PATH

    reloaded = load_city_registry(_CITIES_PATH)
    assert set(reloaded.keys()) == set(CITY_REGISTRY.keys())
    assert reloaded["New York"].location_query == "New York City"


def test_api_cities_shape():
    client = TestClient(app)
    res = client.get("/api/cities")
    assert res.status_code == 200
    body = res.json()
    assert len(body["cities"]) == 30
    assert {r["id"] for r in body["regions"]} == set(REGION_LABELS.keys())
    sample = next(c for c in body["cities"] if c["id"] == "New York")
    assert sample["region"] == "us"
    assert sample["lat"] == pytest.approx(40.71)
    assert "NYC" in sample["aliases"]
