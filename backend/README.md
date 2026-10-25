# VibeGuide Backend

Taste-intelligent travel concierge API. Resolves cultural anchors through Qloo, recommends places per day-phase with explainability, and writes “Why It Fits Your Vibe” narratives (Gemini when configured, otherwise templates).

## Setup

```bash
# from repo root
python -m venv venv
# Windows
.\venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r backend/requirements.txt
cp backend/.env.example backend/.env
# edit backend/.env and set QLOO_API_KEY (hackathon key)
```

Hackathon keys only work against `https://hackathon.api.qloo.com`.

## Run

```bash
cd backend
uvicorn main:app --reload --port 8000
```

- Health: `GET http://localhost:8000/api/health`
- Cities: `GET http://localhost:8000/api/cities`
- Generate: `POST http://localhost:8000/api/generate-itinerary`
- Alias: `POST http://localhost:8000/api/itinerary`
- Refine (requires `GEMINI_API_KEY`): `POST http://localhost:8000/api/refine`

### Adding a city

Edit [`data/cities.json`](data/cities.json). Each entry needs `id`, `label`, `location_query` (Qloo geo string), `region` (`us` | `europe` | `asia` | `india` | `oceania`), `country`, `lat`, `lng`, and optional `aliases`. Restart uvicorn; the frontend map picker picks cities up from `/api/cities`.

Probe a new city before demoing it:

```bash
python scripts/qloo_probe.py --cities Paris Chicago Mumbai Sydney
```

Curated fallback itineraries exist only for Tokyo and New York. Other cities degrade honestly when Qloo is unavailable.

Example:

```bash
curl -s http://localhost:8000/api/generate-itinerary ^
  -H "Content-Type: application/json" ^
  -d "{\"city\":\"Tokyo\",\"music\":\"Nujabes\",\"film\":\"Studio Ghibli\"}"
```

## Pipeline

1. Resolve anchors: music → artist search, film → movie/person/brand search, vibe → `/v2/tags`
2. For each phase (MORNING → NIGHT), call `/v2/insights` with `filter.type=urn:entity:place`, `filter.location.query`, category `filter.tags`, taste signals, and `feature.explainability=true`
3. Dedupe venues across phases; retry with broader tags, then signals-only, if a phase is empty
4. Narratives via Gemini structured JSON (validated against venue names) or template text grounded in explainability
5. If Qloo is down or unconfigured, return curated fallback with `is_fallback=true` and `source=fallback` on every stop

## Live probe

```bash
python backend/scripts/qloo_probe.py
```

Writes a redacted summary and a category-tag override under `backend/scripts/captures/` (gitignored).

## Tests

```bash
cd backend
pytest -q
```

## Env vars

See [`.env.example`](.env.example). Important:

| Variable | Purpose |
|----------|---------|
| `QLOO_API_KEY` | Required for live taste data |
| `GEMINI_API_KEY` | Optional; enables Gemini narratives + `/api/refine` |
| `ALLOWED_ORIGINS` | CORS allow-list (comma-separated) |
