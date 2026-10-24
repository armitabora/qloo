# VibeGuide

**Taste-intelligent travel concierge powered by Qloo's cultural AI.**

Generic travel guides give everyone the same "Top 10" list. VibeGuide uses Qloo to understand your cultural taste: what you listen to, where you eat, what you watch, and builds city itineraries that actually feel like *you*.

> Built for the [Qloo Agentic Hackathon](https://devpost.com/) · Deadline Oct 30, 2026

---

## What It Does

1. **Taste Onboarding**: pick a handful of artists, cuisines, or vibes you love.
2. **Itinerary Generation**: VibeGuide calls Qloo's Taste API across multiple entity types (restaurants, music venues, bars, attractions) and assembles a day-by-day plan for any city.
3. **"Why It Fits Your Vibe"**: every stop gets a short narrative explaining the taste connection, written by Gemini (with a template fallback).
4. **Real-Time Refine**: thumbs-up / thumbs-down a suggestion; the Gemini agent re-ranks remaining stops against your feedback.

---

## Tech Stack

| Layer     | Technology                  |
|-----------|-----------------------------|
| Backend   | Python 3.13 + FastAPI       |
| Frontend  | React + Vite + Tailwind CSS |
| Taste API | **Qloo** `/v2/insights`, `/v2/search` |
| Narratives | Google Gemini (`gemini-3.8-flash`) + template fallback |

---

## Qloo API Integration

VibeGuide uses Qloo at three points in the pipeline:

1. **Category resolution**: maps user seed preferences to Qloo entity types and fetches matching taste tags.
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
python scripts/qloo_probe.py --city Tokyo
```

---

## API Reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/generate-itinerary` | Generate a new itinerary |
| `GET`  | `/api/itinerary` | Retrieve the last generated itinerary |
| `POST` | `/api/refine` | Refine with thumbs-up/down feedback (Gemini agent) |
| `GET`  | `/api/health` | Health check |

See [`backend/README.md`](backend/README.md) for full request/response schemas.

---

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app
│   ├── config.py            # Settings (env vars)
│   ├── qloo/                # Qloo client, resolver, pipeline
│   ├── narrative/           # Gemini + template narrative engine
│   ├── agent/               # Gemini refine agent
│   ├── scripts/             # qloo_probe.py smoke-test
│   └── tests/               # pytest suite (30+ tests)
├── frontend/
│   └── src/App.jsx          # React UI
└── scope.md                 # Hackathon scope document
```

---

## Team

- **Armita Bora**: frontend & product
- **Chinmoy Jyoti Bora**: backend & Qloo pipeline

---

## License

MIT, see [LICENSE](LICENSE).
