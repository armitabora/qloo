"""Analyze city sweep report: anchors, locality, suspect venues."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
report = json.loads(
    (Path(__file__).resolve().parent / "captures" / "city_sweep_tame_nolan_brutalist.json").read_text(
        encoding="utf-8"
    )
)
cities_meta = {
    c["id"]: c for c in json.loads((ROOT / "data" / "cities.json").read_text(encoding="utf-8"))
}

results = report["results"]
ok = [r for r in results if r.get("ok")]
fail = [r for r in results if not r.get("ok")]
print(f"OK {len(ok)} FAIL {len(fail)}")
for f in fail:
    print(" FAIL", f["city"], (f.get("error") or "")[:200])

print("\n=== ANCHOR RESOLUTION ===")
for kind in ("music", "film", "vibe"):
    resolutions: list[tuple] = []
    for r in ok:
        for a in r.get("anchors_resolved") or []:
            if a.get("kind") == kind:
                resolutions.append(
                    (a.get("resolved"), a.get("matched_name"), a.get("entity_id") or a.get("tag_id"))
                )
    uniq = Counter(resolutions)
    print(f"{kind}: {len(uniq)} unique resolution(s)")
    for (resolved, name, eid), n in uniq.most_common(8):
        print(f"  n={n} resolved={resolved} matched={name!r} id={eid}")

fallback_cities = [r["city"] for r in ok if r.get("is_fallback")]
partial_fb = [r["city"] for r in ok if r.get("fallback_stops", 0) > 0]
no_addr = [
    (r["city"], [s["venue"] for s in r.get("stops", []) if not s.get("has_address")])
    for r in ok
]
no_addr = [(c, v) for c, v in no_addr if v]
no_entity = []
for r in ok:
    missing = [
        s["venue"]
        for s in r.get("stops", [])
        if not s.get("entity_id") and s.get("source") == "qloo"
    ]
    if missing:
        no_entity.append((r["city"], missing))

print("\n=== QUALITY ===")
print("is_fallback cities:", fallback_cities or "none")
print("any fallback stops:", partial_fb or "none")
print("cities with missing addresses:", no_addr or "none")
print("qloo stops missing entity_id:", no_entity or "none")
print("stop_count dist:", dict(Counter(r.get("stop_count") for r in ok)))
print("qloo_stops dist:", dict(Counter(r.get("qloo_stops") for r in ok)))
engines = Counter((r.get("meta") or {}).get("narrative_engine") for r in ok)
print("narrative engines:", dict(engines))

print("\n=== ADDRESS LOCALITY HEURISTIC ===")
suspect: list[tuple] = []
for r in ok:
    meta = cities_meta[r["city"]]
    tokens = {meta["label"].lower(), meta["country"].lower()}
    for a in meta.get("aliases") or []:
        tokens.add(a.lower())
    for part in meta.get("location_query", "").replace(",", " ").split():
        if len(part) > 2:
            tokens.add(part.lower())
    # common country abbreviations / alt names
    extras = {
        "United States": {"usa", "us", "united states"},
        "United Kingdom": {"uk", "england", "britain", "great britain"},
        "Netherlands": {"nederland", "holland"},
        "South Korea": {"korea", "republic of korea"},
        "Hong Kong": {"hk", "hong kong sar"},
        "Singapore": {"sg"},
        "New Zealand": {"nz", "aotearoa"},
        "India": {"india", "bharat"},
        "Japan": {"japan", "nihon"},
        "Thailand": {"thailand"},
        "Taiwan": {"taiwan", "roc"},
        "Spain": {"spain", "españa", "espana"},
        "Portugal": {"portugal"},
        "Ireland": {"ireland", "eire"},
        "Italy": {"italy", "italia"},
        "Germany": {"germany", "deutschland"},
        "France": {"france"},
        "Australia": {"australia", "au"},
    }
    tokens |= extras.get(meta["country"], set())
    for s in r.get("stops", []):
        addr = (s.get("address") or "").lower()
        venue = s.get("venue") or ""
        if not addr:
            suspect.append((r["city"], venue, "(no address)", "missing"))
            continue
        if not any(t in addr for t in tokens):
            suspect.append((r["city"], venue, s.get("address"), "token_miss"))

print(f"suspect stops: {len(suspect)} / {sum(len(r.get('stops', [])) for r in ok)}")
for city, venue, addr, reason in suspect:
    print(f"  [{reason}] {city} | {venue} | {addr}")

print("\n=== ALL VENUES BY CITY ===")
for r in ok:
    print(f"\n{r['city']} ({r['elapsed_ms']}ms, engine={(r.get('meta') or {}).get('narrative_engine')})")
    for s in r.get("stops", []):
        print(f"  {s['phase']}: {s['venue']} — {s.get('address')} [src={s.get('source')}]")
