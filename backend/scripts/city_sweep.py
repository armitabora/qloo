"""Sweep generate-itinerary across all cities with fixed taste inputs."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CITIES = json.loads((ROOT / "data" / "cities.json").read_text(encoding="utf-8"))
OUT_DIR = Path(__file__).resolve().parent / "captures"
API = "http://localhost:8000/api/generate-itinerary"

PAYLOAD_BASE = {
    "music": "Tame Impala",
    "film": "Christopher Nolan",
    "vibe": "Brutalist",
}


def generate(city: str) -> dict:
    body = json.dumps({**PAYLOAD_BASE, "city": city}).encode()
    req = urllib.request.Request(
        API,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read().decode())


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    results: list[dict] = []
    errors: list[dict] = []

    for i, city_row in enumerate(CITIES, 1):
        city = city_row["id"]
        t0 = time.time()
        try:
            data = generate(city)
            elapsed = int((time.time() - t0) * 1000)
            stops = data.get("stops") or []
            qloo_n = sum(1 for s in stops if s.get("source") == "qloo")
            fb_n = sum(1 for s in stops if s.get("source") == "fallback")
            addr_n = sum(1 for s in stops if (s.get("address") or "").strip())
            summary = {
                "city": city,
                "ok": True,
                "elapsed_ms": elapsed,
                "is_fallback": data.get("is_fallback"),
                "meta": data.get("meta"),
                "anchors_resolved": data.get("anchors_resolved"),
                "stop_count": len(stops),
                "qloo_stops": qloo_n,
                "fallback_stops": fb_n,
                "stops_with_address": addr_n,
                "stops": [
                    {
                        "phase": s.get("phase"),
                        "venue": s.get("venue"),
                        "address": s.get("address"),
                        "category": s.get("category"),
                        "source": s.get("source"),
                        "affinity": s.get("affinity"),
                        "entity_id": s.get("entity_id"),
                        "has_address": bool((s.get("address") or "").strip()),
                        "influenced_by": s.get("influenced_by"),
                    }
                    for s in stops
                ],
            }
            print(
                f"[{i:02d}/{len(CITIES)}] {city}: stops={len(stops)} "
                f"qloo={qloo_n} fallback={fb_n} addr={addr_n} "
                f"fallback_flag={data.get('is_fallback')} {elapsed}ms",
                flush=True,
            )
            results.append(summary)
        except Exception as exc:  # noqa: BLE001
            elapsed = int((time.time() - t0) * 1000)
            msg = str(exc)
            if isinstance(exc, urllib.error.HTTPError):
                try:
                    msg = exc.read().decode()[:800]
                except Exception:  # noqa: BLE001
                    pass
            print(f"[{i:02d}/{len(CITIES)}] {city}: FAIL {elapsed}ms {msg}", flush=True)
            err = {"city": city, "error": msg, "elapsed_ms": elapsed}
            errors.append(err)
            results.append({"city": city, "ok": False, **err})

    report = {"inputs": PAYLOAD_BASE, "results": results, "errors": errors}
    out_path = OUT_DIR / "city_sweep_tame_nolan_brutalist.json"
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    ok = sum(1 for r in results if r.get("ok"))
    print(f"\nDONE ok={ok}/{len(CITIES)} errors={len(errors)} -> {out_path}", flush=True)


if __name__ == "__main__":
    main()
