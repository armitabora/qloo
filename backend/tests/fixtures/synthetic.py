"""Synthetic Qloo-shaped payloads for unit tests (not real API data)."""

from __future__ import annotations

from typing import Any


def search_artist(name: str = "Nujabes", entity_id: str = "ent-artist-1") -> dict[str, Any]:
    return {
        "results": [
            {
                "entity_id": entity_id,
                "name": name,
                "type": "urn:entity:artist",
            }
        ]
    }


def search_film(name: str = "Studio Ghibli", entity_id: str = "ent-brand-1") -> dict[str, Any]:
    return {
        "results": [
            {
                "entity_id": entity_id,
                "name": name,
                "type": "urn:entity:brand",
            }
        ]
    }


def tags_cafe() -> dict[str, Any]:
    return {
        "results": {
            "tags": [
                {"id": "urn:tag:genre:place:cafe", "name": "Cafe"},
                {"id": "urn:tag:genre:place:coffee_shop", "name": "Coffee Shop"},
            ]
        }
    }


def tags_vibe(query: str = "lo-fi") -> dict[str, Any]:
    return {
        "results": {
            "tags": [
                {"id": "urn:tag:genre:music:lo_fi", "name": "Lo-Fi"},
                {"id": f"urn:tag:keyword:{query.replace(' ', '_')}", "name": query},
            ]
        }
    }


def place_entity(
    *,
    entity_id: str,
    name: str,
    tag: str = "Cafe",
    affinity: float = 0.8,
    influence_id: str = "ent-artist-1",
    influence_score: float = 0.6,
) -> dict[str, Any]:
    return {
        "entity_id": entity_id,
        "name": name,
        "type": "urn:entity:place",
        "tags": [{"name": tag, "id": f"urn:tag:genre:place:{tag.lower().replace(' ', '_')}"}],
        "properties": {
            "address": f"123 Example St, near {name}",
            "image": {"url": f"https://example.com/{entity_id}.jpg"},
            "geocode": {"name": "Shibuya", "admin1_region": "Tokyo", "country_code": "JP"},
        },
        "query": {
            "affinity": affinity,
            "explainability": {
                "signal.interests.entities": {influence_id: influence_score},
            },
        },
    }


def insights_places(entities: list[dict[str, Any]]) -> dict[str, Any]:
    return {"results": {"entities": entities}}


PHASE_TAG_RESPONSES = {
    "cafe": tags_cafe(),
    "coffee shop": {
        "results": {"tags": [{"id": "urn:tag:genre:place:coffee_shop", "name": "Coffee Shop"}]}
    },
    "bakery": {
        "results": {"tags": [{"id": "urn:tag:genre:place:bakery", "name": "Bakery"}]}
    },
    "museum": {
        "results": {"tags": [{"id": "urn:tag:genre:place:museum", "name": "Museum"}]}
    },
    "art gallery": {
        "results": {"tags": [{"id": "urn:tag:genre:place:art_gallery", "name": "Art Gallery"}]}
    },
    "bookstore": {
        "results": {"tags": [{"id": "urn:tag:genre:place:bookstore", "name": "Bookstore"}]}
    },
    "record store": {
        "results": {"tags": [{"id": "urn:tag:genre:place:record_store", "name": "Record Store"}]}
    },
    "restaurant": {
        "results": {"tags": [{"id": "urn:tag:genre:place:restaurant", "name": "Restaurant"}]}
    },
    "bar": {"results": {"tags": [{"id": "urn:tag:genre:place:bar", "name": "Bar"}]}},
    "cocktail bar": {
        "results": {"tags": [{"id": "urn:tag:genre:place:cocktail_bar", "name": "Cocktail Bar"}]}
    },
    "jazz club": {
        "results": {"tags": [{"id": "urn:tag:genre:place:jazz_club", "name": "Jazz Club"}]}
    },
    "music venue": {
        "results": {"tags": [{"id": "urn:tag:genre:place:music_venue", "name": "Music Venue"}]}
    },
}
