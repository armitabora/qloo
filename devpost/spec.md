---
doc: spec
status: approved
---

# VibeGuide — Technical Specification

A technical blueprint for VibeGuide: a decoupled full-stack architecture pairing a Python (FastAPI) orchestration backend with a React (Vite) + Tailwind CSS single-page frontend.

---

## How This Works, In Plain Language

VibeGuide runs as two coordinated local services on your Mac:
1. **The Frontend (React + Vite)**: Displays the sleek, dark-mode editorial user interface in your web browser at `http://localhost:5173`. It collects your city and cultural anchors, validates that you provided at least one anchor, triggers the cycling loading animation, and renders the 4-stop vertical timeline.
2. **The Backend (FastAPI)**: Runs at `http://localhost:8000`. When the frontend makes an HTTP `POST` request, FastAPI receives the inputs, queries the **Qloo API** to fetch culturally aligned physical places in Tokyo or New York, constructs a tailored prompt for **Google Gemini**, prompts the LLM to write the "Why It Fits Your Vibe" narratives, and returns structured JSON back to the browser.
3. **The Demo Safety Net**: If either the Qloo API or the Gemini LLM is slow, down, or rate-limited during a live hackathon demo recording, FastAPI automatically switches to a high-quality pre-computed fallback dataset for Tokyo and New York, ensuring the demo video never stalls.

Why this shape? It cleanly isolates the frontend presentation from backend API secrets and orchestration, allows rapid visual iteration with React + Tailwind, and keeps all taste intelligence and prompt logic in Python where data manipulation is cleanest.

---

## The Core Journey Through the System

*Reference: `prd.md > The Core Journey`*

1. **User loads UI**: Browser navigates to `http://localhost:5173`. React renders `AnchorForm` inside a centered column against an editorial dark background (`#121214`).
2. **User submits inputs**: The user chooses a city (default Tokyo) and enters at least one anchor (e.g. Music: "Radiohead", Film: "Studio Ghibli").
3. **Frontend checks inputs**: `AnchorForm` verifies that `city` is present and at least one cultural anchor has text. If empty, it applies a subtle shake animation and halts.
4. **Request dispatch**: The frontend calls `POST http://localhost:8000/api/itinerary` via browser `fetch()`. The UI shifts to `LoadingState`, displaying a spinner and rotating text ("Analyzing your taste..." → "Mapping the city..." → "Writing your itinerary...").
5. **FastAPI receives payload**: `main.py` validates the payload using Pydantic (`ItineraryRequest`).
6. **Taste mapping (Qloo)**: `qloo_client.py` requests matching venues in the chosen city based on the provided cultural anchors.
7. **Narrative synthesis (Gemini)**: `gemini_client.py` sends the combined user anchors and candidate venues to the Gemini API with instructions to return concise, evocative "Why It Fits Your Vibe" narratives for Morning, Afternoon, Evening, and Night.
8. **JSON response & timeline reveal**: FastAPI returns `ItineraryResponse`. The frontend receives the JSON, transitions out of `LoadingState`, and renders `TimelineView` with the 4 stops and visible vibe narratives.
9. **Reset**: Clicking "Plan Another Day" resets the React state, bringing the user smoothly back to `AnchorForm`.

---

## Stack

### Frontend
- **Framework**: [React 18](https://react.dev/) + [Vite](https://vitejs.dev/)
  - *Rationale*: Instant hot-module replacement, lightweight zero-config build, modern JSX component model.
  - *Tradeoff*: Requires Node.js tooling locally, but delivers the exact responsive single-page experience required by the PRD.
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
  - *Rationale*: Utility-first CSS enables pixel-accurate dark-mode editorial typography without writing separate custom CSS files.
- **Icons**: [Lucide React](https://lucide.dev/guide/packages/lucide-react)
  - *Rationale*: Minimalist, lightweight SVGs for the ✨ sparkles, timeline markers, and reload actions.

### Backend
- **Language**: Python 3.13 (running inside existing virtual environment `venv`)
- **API Framework**: [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
  - *Rationale*: High performance, automatic OpenAPI documentation, clean async route definitions, and native Pydantic validation.
  - *Tradeoff*: Asynchronous Python requires running an ASGI server (Uvicorn), but it handles multiple API requests seamlessly.
- **Data Validation**: [Pydantic v2](https://docs.pydantic.dev/)
  - *Rationale*: Strict type checking and JSON parsing for requests and responses.
- **HTTP Client**: [httpx](https://www.python-httpx.org/)
  - *Rationale*: Modern async HTTP library for calling Qloo and external APIs with built-in timeout controls.
- **Environment Management**: [python-dotenv](https://pypi.org/project/python-dotenv/)
  - *Rationale*: Loads `.env` secrets into environment variables without exposing keys in Git.

### External APIs
- **Taste Intelligence**: [Qloo Taste API](https://qloo.com/)
  - *Rationale*: Maps cross-domain cultural affinity (music/film/taste) to physical venues in Tokyo and New York.
- **Narrative Generation**: [Google Gemini API](https://ai.google.dev/gemini-api/docs) (via `google-genai` SDK or HTTP REST)
  - *Rationale*: Fast response times, generous free-tier limits, and strong creative synthesis for vibe explanations.

---

## Where It Runs and How Someone Tries It

### Runtime Environment
- Runs locally on macOS in two terminal windows.
- Backend requires: Python 3.13 (`venv`), `.env` file with `QLOO_API_KEY` and `GEMINI_API_KEY`.
- Frontend requires: Node.js (v24+ installed) and npm.

### Start Commands

**Terminal 1 — Backend (FastAPI):**
```bash
cd /Users/armitabora/Documents/qloo/VibeGuide/backend
source ../venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Frontend (React Vite):**
```bash
cd /Users/armitabora/Documents/qloo/VibeGuide/frontend
npm install
npm run dev
```

### Verification & Demo Recording
1. Open web browser to `http://localhost:5173`.
2. Inspect terminal logs at `http://localhost:8000` to show real-time incoming API requests.
3. Test recording using OBS or Mac QuickTime Screen Recording.

---

## Look and Feel Implementation

*Reference: `prd.md > Look and Feel`*

- **Background Canvas**: Deep charcoal `#121214` (Tailwind `bg-[#121214]`).
- **Surface Cards**: Muted dark charcoal `#18181b` (Tailwind `bg-zinc-900/60`).
- **Borders & Dividers**: Subtle zinc border `#27272a` (Tailwind `border-zinc-800`).
- **Typography**:
  - Headings: Serif/Display or crisp sans-serif with tracked letters (`tracking-tight text-zinc-100`).
  - Body & Labels: Soft off-white and muted zinc (`text-zinc-400`).
  - Inputs: Underlined minimal text inputs (`border-b border-zinc-700 focus:border-zinc-300 bg-transparent outline-none`).
- **Accent**: Soft gold / amber for vibe quotes (`border-amber-400/80 text-amber-200/90`).

---

## Components

### Frontend Components (`frontend/src/components/`)

#### 1. `AnchorForm.jsx`
- *Implements*: `prd.md > 1. Cultural Input & Validation`
- *Responsibilities*:
  - Manages local state for `city` (default "Tokyo"), `music`, `film`, and `vibe`.
  - Performs validation: verifies `city` is selected and `music || film || vibe` is non-empty.
  - Triggers shake animation on invalid submit.
  - Invokes `onSubmit(formData)` to trigger itinerary generation.

#### 2. `LoadingState.jsx`
- *Implements*: `prd.md > 2. Entertaining Loading State`
- *Responsibilities*:
  - Renders a minimalist animated spinner.
  - Automatically rotates status messages every 2.5 seconds using a `setInterval` hook:
    1. *"Analyzing your taste..."*
    2. *"Mapping the city..."*
    3. *"Writing your itinerary..."*

#### 3. `TimelineView.jsx`
- *Implements*: `prd.md > 3. Timeline Itinerary & Vibe Badges`
- *Responsibilities*:
  - Receives the 4 itinerary stops from API response.
  - Renders a continuous vertical timeline connected with a thin zinc line.
  - Displays each stop card with Phase label (MORNING, AFTERNOON, EVENING, NIGHT), venue name, category tag, and uncollapsed "Why It Fits Your Vibe" blockquote with ✨ badge.
  - Houses the "Plan Another Day" reset CTA at the bottom.

#### 4. `ErrorState.jsx`
- *Implements*: `prd.md > States and Boundaries > Error State`
- *Responsibilities*:
  - Renders a friendly editorial fallback when an unrecoverable network failure occurs: *"Vibe check failed. The city might be too sleepy right now, or our AI needs a coffee."*
  - Provides a "Try Different Anchors" button to reset the view.

---

### Backend Components (`backend/`)

#### 1. `main.py`
- *Implements*: `prd.md > The Core Journey`
- *Responsibilities*:
  - Initializes FastAPI application.
  - Configures `CORSMiddleware(allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])`.
  - Exposes health endpoint `GET /api/health`.
  - Exposes `POST /api/itinerary` routing to orchestrator.

#### 2. `services/qloo_client.py`
- *Implements*: `scope.md > Qloo API Integration Plan`
- *Responsibilities*:
  - Reads `QLOO_API_KEY` from environment.
  - Constructs geo-scoped entity queries for Tokyo and New York venues matching taste signals.
  - Returns parsed place records (name, category, address, vibes).

#### 3. `services/gemini_client.py`
- *Implements*: `scope.md > The Unique Kernel`
- *Responsibilities*:
  - Reads `GEMINI_API_KEY` from environment.
  - Formulates an editorial prompt supplying the user's cultural anchors and candidate venues.
  - Requests structured JSON returning the 4 specific stops with evocative "Why It Fits Your Vibe" explanations.

#### 4. `services/fallback_data.py` (The Demo Safety Net)
- *Implements*: `spec.md > Safety Net for the Hackathon Demo`
- *Responsibilities*:
  - Contains rich, authentic fallback itineraries for Tokyo and New York with pre-crafted cross-domain narratives.
  - Seamlessly activates if API timeouts or rate limits occur, preventing blank screens or errors during video recording.

#### 5. `models.py`
- *Implements*: Data contracts between frontend and backend.

---

## Data Model

### Request Schema (`ItineraryRequest`)
```python
class ItineraryRequest(BaseModel):
    city: str  # Must be "Tokyo" or "New York"
    music: Optional[str] = None
    film: Optional[str] = None
    vibe: Optional[str] = None
```

### Response Schema (`ItineraryResponse`)
```python
class ItineraryStop(BaseModel):
    phase: str  # "Morning", "Afternoon", "Evening", "Night"
    venue: str  # e.g. "Lion Kissaten"
    category: str  # e.g. "Historic Vinyl Cafe"
    vibe_narrative: str  # "Because you love Studio Ghibli and lo-fi aesthetics..."

class ItineraryResponse(BaseModel):
    city: str
    is_fallback: bool = False
    stops: List[ItineraryStop]
```

---

## File Structure

```
VibeGuide/
├── backend/
│   ├── main.py                  # FastAPI app entry point & CORS configuration
│   ├── models.py                # Pydantic schemas (Request & Response)
│   ├── requirements.txt         # Python dependencies (fastapi, uvicorn, httpx, etc.)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── qloo_client.py       # Qloo taste intelligence API wrapper
│   │   ├── gemini_client.py     # Gemini LLM narrative prompt service
│   │   └── fallback_data.py     # High-fidelity Tokyo & NYC safety net datasets
│   └── tests/
│       └── test_api.py          # Quick pytest for endpoint verification
├── frontend/
│   ├── index.html               # Main HTML wrapper with dark background
│   ├── package.json             # NPM dependencies (react, vite, tailwindcss)
│   ├── tailwind.config.js       # Tailwind color & font configuration
│   ├── postcss.config.js
│   ├── vite.config.js           # Vite dev server configuration
│   └── src/
│       ├── main.jsx             # React entry point
│       ├── App.jsx              # Core controller (manages form/loading/itinerary states)
│       ├── index.css            # Tailwind directives and custom scrollbar
│       └── components/
│           ├── AnchorForm.jsx   # Input fields & validation
│           ├── LoadingState.jsx # Cycling status copy & spinner
│           ├── TimelineView.jsx # 4-stop itinerary timeline
│           └── ErrorState.jsx   # Fallback error card
├── devpost/
│   ├── learner-profile.md       # Learner background and goals
│   ├── scope.md                 # Approved project scope
│   ├── scope.html
│   ├── prd.md                   # Approved Product Requirements Document
│   ├── prd.html
│   ├── spec.md                  # Approved Technical Specification (this doc)
│   └── spec.html                # Visual architecture companion
├── .gitignore                   # Ignores venv/, node_modules/, .env, learner-profile.md
├── .env.example                 # Template for required API keys (no secrets)
└── README.md                    # Project overview & running instructions
```

---

## External Services and Dependencies

1. **Qloo API**:
   - *Key*: `QLOO_API_KEY`
   - *Docs*: [Qloo API Documentation](https://qloo.com/)
   - *Usage*: Fetching culturally aligned venues filtered by city coordinates/names.
2. **Google Gemini API**:
   - *Key*: `GEMINI_API_KEY`
   - *Docs*: [Gemini API Reference](https://ai.google.dev/)
   - *Usage*: Generating the 4 vibe-matching narratives from prompt template.
3. **CORS Handling**:
   - FastAPI middleware configured to trust `http://localhost:5173`.

---

## Important Failure Modes & Mitigations

1. **API Rate Limiting or Network Timeout**:
   - *Failure*: Qloo or Gemini takes > 10 seconds or returns HTTP 429/500.
   - *Mitigation*: Backend catches the exception and transparently returns `fallback_data.py` with `is_fallback: True`. The user always sees a beautiful, cohesive itinerary.
2. **Empty Cultural Anchors**:
   - *Failure*: User clicks "Generate" without typing any anchors.
   - *Mitigation*: Handled on the client side in `AnchorForm.jsx` with an instant subtle shake animation before any network request is sent.
3. **Backend Not Running**:
   - *Failure*: User opens frontend but forgot to launch FastAPI.
   - *Mitigation*: React displays `ErrorState.jsx` with a clean retry button instead of a white crash screen.

---

## What Was Simplified and Why

- **Stateless in-memory requests instead of a Database**: Avoids managing SQLite migrations, table locks, or schema maintenance for a proof of concept.
- **Two Curated Cities (Tokyo & New York) instead of Global Geocoding**: Guarantees rich place density and eliminates obscure location edge cases.
- **Direct HTTP API calls instead of a Celery/Redis queue**: Keeps process management to two simple terminal windows.

---

## Decisions and Open Issues

- **CORS Setup**: Confirmed that `CORSMiddleware` in FastAPI bridges localhost:5173 to localhost:8000 without requiring complex reverse proxies.
- **Safety Net**: Confirmed that `fallback_data.py` will be included in the backend service so the hackathon video demo is guaranteed to run without hitches.
- **Build First Step**: Ready to transition to `5-build` to scaffold the backend and frontend directories and test the hello-world pipeline.
