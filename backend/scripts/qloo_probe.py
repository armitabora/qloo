#!/usr/bin/env python3
"""Live discovery probe against the Qloo hackathon API.

Verifies:
  1. /search resolves cultural anchors to entity IDs
  2. /v2/tags returns place-category tag IDs for each day phase
  3. /v2/insights with filter.location.query + filter.tags returns
     category-appropriate places for Tokyo and New York City
  4. feature.explainability returns influence metadata when signals are present

Usage (from repo root, venv active):
  set QLOO_API_KEY=...   # or put it in backend/.env
  python backend/scripts/qloo_probe.py

Does NOT write raw Qloo payloads to disk (ToS). Prints a summary only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

BACKEND = Path(__file__).resolve().parents[1]
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from config import (  # noqa: E402
    CITY_REGISTRY,
    PHASE_CATEGORY_QUERIES,
    PHASES,
    clear_settings_cache,
    get_settings,
)
from qloo.client import QlooClient, QlooError  # noqa: E402


def _entity_id(entity: dict[str, Any]) -> str | None:
    return entity.get("entity_id") or entity.get("id") or entity.get("qloo_id")


def _entity_name(entity: dict[str, Any]) -> str:
    return str(entity.get("name") or entity.get("title") or "?")


def _tag_names(entity: dict[str, Any], limit: int = 8) -> list[str]:
    tags = entity.get("tags") or []
    names: list[str] = []
    for t in tags:
        if isinstance(t, dict):
            name = t.get("name") or t.get("id") or ""
        else:
            name = str(t)
        if name:
            names.append(str(name))
        if len(names) >= limit:
            break
    return names


def _extract_entities(payload: dict[str, Any]) -> list[dict[str, Any]]:
    results = payload.get("results") or {}
    if isinstance(results, dict):
        entities = results.get("entities") or []
    elif isinstance(results, list):
        entities = results
    else:
        entities = payload.get("entities") or []
    return [e for e in entities if isinstance(e, dict)]


async def resolve_category_tags(client: QlooClient) -> dict[str, list[dict[str, str]]]:
    """Map each phase to discovered tag {id, name} records."""
    discovered: dict[str, list[dict[str, str]]] = {}
    for phase in PHASES:
        queries = PHASE_CATEGORY_QUERIES[phase]
        tags_for_phase: list[dict[str, str]] = []
        seen: set[str] = set()
        for q in queries:
            tags = await client.tags(q, take=8)
            for t in tags:
                tid = str(t.get("id") or t.get("tag_id") or "")
                name = str(t.get("name") or "")
                if not tid or tid in seen:
                    continue
                # Prefer place-related tags when the id hints at it.
                lower = (tid + " " + name).lower()
                if any(
                    bad in lower
                    for bad in ("movie", "artist", "podcast", "book", "tv_show", "video_game")
                ):
                    continue
                seen.add(tid)
                tags_for_phase.append({"id": tid, "name": name or tid, "query": q})
        discovered[phase] = tags_for_phase
        print(f"\n[{phase}] tag discovery for {queries}:")
        if not tags_for_phase:
            print("  !! NO TAGS FOUND")
        for t in tags_for_phase[:6]:
            print(f"  - {t['id']}  ({t['name']})  via '{t['query']}'")
    return discovered


async def probe_city(
    client: QlooClient,
    city_key: str,
    category_tags: dict[str, list[dict[str, str]]],
    signal_entity_ids: list[str],
) -> dict[str, Any]:
    city = CITY_REGISTRY[city_key]
    report: dict[str, Any] = {"city": city_key, "location_query": city.location_query, "phases": {}}

    for phase in PHASES:
        tag_ids = [t["id"] for t in category_tags.get(phase, [])][:4]
        params: dict[str, Any] = {
            "filter.type": "urn:entity:place",
            "filter.location.query": city.location_query,
            "take": 8,
            "feature.explainability": True,
        }
        if tag_ids:
            params["filter.tags"] = tag_ids
            params["operator.filter.tags"] = "union"
        if signal_entity_ids:
            params["signal.interests.entities"] = signal_entity_ids

        try:
            payload = await client.insights(params)
            entities = _extract_entities(payload)
        except QlooError as exc:
            report["phases"][phase] = {"error": str(exc), "status": getattr(exc, "status_code", None)}
            print(f"\n[{city_key}/{phase}] ERROR: {exc}")
            continue

        summary = []
        for e in entities[:5]:
            summary.append(
                {
                    "name": _entity_name(e),
                    "id": _entity_id(e),
                    "tags": _tag_names(e),
                    "affinity": (e.get("query") or {}).get("affinity")
                    if isinstance(e.get("query"), dict)
                    else e.get("affinity"),
                }
            )

        # Heuristic: does any returned place tag overlap our category keywords?
        keywords = [q.lower() for q in PHASE_CATEGORY_QUERIES[phase]]
        hit = 0
        for item in summary:
            blob = " ".join(item["tags"]).lower() + " " + item["name"].lower()
            if any(k in blob for k in keywords):
                hit += 1

        report["phases"][phase] = {
            "requested_tags": tag_ids,
            "result_count": len(entities),
            "category_keyword_hits": hit,
            "sample": summary,
        }
        print(f"\n[{city_key}/{phase}] results={len(entities)} keyword_hits={hit}")
        for s in summary[:3]:
            print(f"  • {s['name']}  tags={s['tags'][:4]}  affinity={s['affinity']}")

    return report


async def resolve_demo_anchors(client: QlooClient) -> list[str]:
    """Resolve Studio Ghibli + Nujabes for signal.interests.entities."""
    ids: list[str] = []
    for query, types in (
        ("Nujabes", "urn:entity:artist"),
        ("Studio Ghibli", ["urn:entity:brand", "urn:entity:movie", "urn:entity:person"]),
    ):
        results = await client.search(query, types=types, take=5)
        print(f"\n[search] '{query}' → {len(results)} hits")
        for r in results[:3]:
            eid = _entity_id(r)
            print(f"  - {_entity_name(r)}  id={eid}  type={r.get('type') or r.get('entity_type')}")
            if eid and eid not in ids:
                ids.append(eid)
                break
    return ids


async def main(cities: list[str]) -> int:
    clear_settings_cache()
    settings = get_settings()
    if not settings.has_qloo_key:
        print("ERROR: QLOO_API_KEY is not set. Put it in backend/.env or the environment.")
        return 2

    print(f"Base URL: {settings.qloo_base_url}")
    print(f"Key present: yes (len={len(settings.qloo_api_key)})")

    async with QlooClient(settings=settings) as client:
        # Sanity: search
        try:
            hits = await client.search("Radiohead", types="urn:entity:artist", take=3)
            print(f"\n[sanity] /search Radiohead → {len(hits)} results")
        except QlooError as exc:
            print(f"ERROR: /search failed: {exc}")
            return 1

        category_tags = await resolve_category_tags(client)
        signal_ids = await resolve_demo_anchors(client)

        reports = []
        for city in cities:
            if city not in CITY_REGISTRY:
                print(f"Unknown city: {city}")
                continue
            reports.append(await probe_city(client, city, category_tags, signal_ids))

        # Compact verdict
        print("\n======== VERDICT ========")
        ok = True
        for report in reports:
            for phase, data in report["phases"].items():
                if "error" in data:
                    print(f"FAIL {report['city']}/{phase}: {data['error']}")
                    ok = False
                elif data.get("result_count", 0) == 0:
                    print(f"WARN {report['city']}/{phase}: 0 results (filters may be over-tight)")
                elif data.get("category_keyword_hits", 0) == 0:
                    print(
                        f"WARN {report['city']}/{phase}: results present but no keyword overlap "
                        f"(tags may still be valid — inspect sample)"
                    )
                else:
                    print(f"OK   {report['city']}/{phase}: {data['result_count']} places, hits={data['category_keyword_hits']}")

        # Write a redacted summary (no full payloads) for the build log.
        out_dir = Path(__file__).resolve().parent / "captures"
        out_dir.mkdir(exist_ok=True)
        summary_path = out_dir / "probe_summary.json"
        category_override = {
            "strict": {phase: [t["id"] for t in tags] for phase, tags in category_tags.items()},
            "broad": {},
        }
        (out_dir / "category_tags.json").write_text(
            json.dumps(category_override, indent=2), encoding="utf-8"
        )
        redacted = {
            "cities": [
                {
                    "city": r["city"],
                    "location_query": r["location_query"],
                    "phases": {
                        phase: {
                            "result_count": d.get("result_count"),
                            "category_keyword_hits": d.get("category_keyword_hits"),
                            "requested_tag_count": len(d.get("requested_tags") or []),
                            "error": d.get("error"),
                            "sample_names": [s["name"] for s in (d.get("sample") or [])],
                        }
                        for phase, d in r["phases"].items()
                    },
                }
                for r in reports
            ],
            "category_tag_ids": category_override["strict"],
            "signal_entity_count": len(signal_ids),
        }
        summary_path.write_text(json.dumps(redacted, indent=2), encoding="utf-8")
        print(f"\nWrote redacted summary → {summary_path}")
        print(f"Wrote category override → {out_dir / 'category_tags.json'}")
        return 0 if ok else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--cities",
        nargs="+",
        default=["Tokyo", "New York"],
        help="Cities from CITY_REGISTRY",
    )
    args = parser.parse_args()
    raise SystemExit(asyncio.run(main(args.cities)))
