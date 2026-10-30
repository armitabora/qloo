# VibeGuide

**Taste-intelligent travel concierge powered by Qloo's cultural AI.**

Generic travel guides give everyone the same "Top 10" list. VibeGuide uses Qloo to understand your cultural taste: what you listen to, where you eat, what you watch, and builds city itineraries that actually feel like *you*.

> Built for the [Qloo Agentic Hackathon](https://devpost.com/) · Deadline Oct 30, 2026

**Live demo:** [qloo-alpha.vercel.app](https://qloo-alpha.vercel.app/)

---

## What It Does

1. **Pick a city**: choose from ~30 destinations on an illustrated map picker (or the logo grid).
2. **Taste onboarding**: name a few artists, films, or vibes you love.
3. **Itinerary generation**: VibeGuide calls Qloo across restaurants, music venues, bars, and attractions and assembles a morning-to-night day plan.
4. **"Why it fits your vibe"**: every stop gets a short narrative from Gemini (with a template fallback), then the form dissolves into the itinerary still-life.
5. **Real-time refine**: thumbs-up / thumbs-down a suggestion; the Gemini agent re-ranks remaining stops against your feedback.

Footer pages cover **About**, **Terms**, and **Privacy**.

---

## Try the live site (free-tier note)

The frontend is on Vercel; the FastAPI backend is on Render's free tier.

- **Backend boot**: after idle time the Render service sleeps. The first request (or a cold `/api/health` hit) can take about a minute while the instance wakes up.
- **First search**: the first itinerary generation after wake-up is also slower. Free-tier CPU, cold caches, and live Qloo/Gemini calls all stack on that first run. Later searches in the same session are usually faster thanks to the in-process Qloo cache.

If a generate call hangs or fails right after opening the demo, wait for the backend to wake, then try again.

---

## Tech Stack

| Layer      | Technology                          |
|------------|-------------------------------------|
| Backend    | Python 3.13 + FastAPI               |
| Frontend   | React + Vite + Tailwind CSS         |
| Hosting    | Vercel (frontend) + Render (API)    |
| Taste API  | **Qloo** `/v2/insights`, `/v2/search` |
| Narratives | Google Gemini (`gemini-3.8-flash`) + template fallback |

---

## Qloo API Integration

VibeGuide uses Qloo at three points in the pipeline:

1. **Category resolution**: maps user seed preferences to Qloo entity types and fetches matching taste tags (parallel searches + process cache).
2. **Cross-category insights**: `/v2/insights` with `filter.type` + `signal.interests.entities` translates music/film taste into dining/nightlife recommendations.
3. **Location-scoped search**: `/v2/search` with geo filter ensures every recommendation is a real, visitable place in the destination city.

Each itinerary stop exposes `influenced_by`, `affinity`, and `source` so the taste connection is always explainable.

---

## Running Locally

### Prerequisites

- Python 3.13+
- Node 18+
- A [Qloo API key](https://www.qloo.com/)
- A [Google Gemini API key](https://aistudio.google.com/) *(optional; template fallback works without it)*

### Backend

```bash
cd backend
cp .env.example .env        # fill in QLOO_API_KEY (and optionally GEMINI_API_KEY)
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev                  # proxies /api/* to localhost:8000
```

Open [http://localhost:5173](http://localhost:5173).

### Smoke-test the pipeline

```bash
cd backend
python scripts/qloo_probe.py --cities Tokyo Paris Chicago Mumbai Sydney
```

---

## Destinations

About 30 cities across the United States, Europe, Asia, India, and Oceania. The map picker loads them from `GET /api/cities`.

To add a city, append a row to [`backend/data/cities.json`](backend/data/cities.json) (`id`, `label`, `location_query`, `region`, `country`, `lat`, `lng`, `aliases`) and restart the backend. No frontend deploy needed.

Curated offline fallbacks exist only for **Tokyo** and **New York**. Other cities need a live Qloo key; without it they return an honest degraded response instead of wrong-city venues.

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/cities` | Destination registry (regions + lat/lng for the map picker) |
| `POST` | `/api/generate-itinerary` | Generate a new itinerary |
| `POST` | `/api/itinerary` | Alias for generate |
| `POST` | `/api/refine` | Refine with thumbs-up/down feedback (Gemini agent) |
| `GET`  | `/api/health` | Health check |

See [`backend/README.md`](backend/README.md) for full request/response schemas.

---

## Deploy

| Service  | Host   | Notes |
|----------|--------|-------|
| Frontend | Vercel | Root directory `frontend`; SPA rewrites in `frontend/vercel.json` so `/about`, `/terms`, and `/privacy` load |
| Backend  | Render | Root directory `backend`; start with `uvicorn main:app --host 0.0.0.0 --port $PORT` |

Set `VITE_API_BASE_URL` to the Render URL at Vercel build time, `ALLOWED_ORIGINS` to the Vercel origin on Render, plus `QLOO_API_KEY` and optional `GEMINI_API_KEY` on the backend.

---

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings + city registry loader
│   ├── data/cities.json     # ~30 destinations (single source of truth)
│   ├── qloo/                # Qloo client, resolver, pipeline (cache + parallel search)
│   ├── narrative/           # Gemini + template narrative engine
│   ├── agent/               # Gemini refine agent
│   ├── scripts/             # qloo_probe.py smoke-test
│   └── tests/               # pytest suite
├── frontend/
│   ├── vercel.json          # SPA rewrites for footer routes
│   └── src/
│       ├── App.jsx
│       └── components/      # map picker, dissolve, itinerary, About/Terms/Privacy
└── LICENSE
```

---

## Team

- **Armita Bora**: frontend & product
- **Chinmoy Jyoti Bora**: backend & Qloo pipeline

---

## License

MIT, see [LICENSE](LICENSE).
