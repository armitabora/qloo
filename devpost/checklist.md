---
doc: checklist
status: approved
---

# Build Checklist

Build mode: fast

## Slices

- [ ] **1. Full-stack end-to-end foundation & safety net itinerary**
  Becomes usable: Both backend (FastAPI) and frontend (React + Tailwind) run locally on your Mac. Entering a city (Tokyo or New York) and cultural anchors immediately generates and displays the 4-stop vertical timeline with rich, authentic "Why It Fits Your Vibe" narratives served via our built-in safety net data.
  Why now: Proves the whole full-stack path on the very first slice — project bootstrapping, FastAPI CORS setup, React Vite setup, dark editorial styling, input form, and timeline rendering — so every subsequent slice has a working app to build on.
  PRD ref: `prd.md > The Core Journey`, `prd.md > Screens and Layout`, `prd.md > 3. Timeline Itinerary & Vibe Badges`
  Spec ref: `spec.md > Stack`, `spec.md > Components`, `spec.md > Where It Runs and How Someone Tries It`, `spec.md > services/fallback_data.py`
  Build: Scaffold `backend/` and `frontend/` folders, install dependencies, configure Tailwind dark theme, create Pydantic models, implement `/api/itinerary` with Tokyo/NYC safety net data, create `AnchorForm.jsx` and `TimelineView.jsx` with visible vibe quotes.
  Verify (mechanical): Start Uvicorn backend and test `POST /api/itinerary` via curl to verify HTTP 200 and schema; run `npm run build` on frontend to verify clean JSX compilation.
  Learner check: Start both dev servers, open `http://localhost:5173`, choose Tokyo, enter "Studio Ghibli" and "Lo-fi Hip Hop", click Generate, and observe the 4-stop vertical timeline.
  Commit: `Scaffold full-stack app and render end-to-end itinerary with safety net`

- [ ] **2. Cycling loading state, validation, and error resilience**
  Becomes usable: Submitting without an anchor triggers a subtle shake animation without page reload. On valid submission, the CTA transforms into an animated loading spinner that cycles through the three status lines (*"Analyzing your taste..."* → *"Mapping the city..."* → *"Writing your itinerary..."*) to mask API latency. "Plan Another Day" smoothly resets the view.
  Why now: Polishes the user experience and masks the 5–10s latency before connecting live external APIs, ensuring the UI remains lively and resilient.
  PRD ref: `prd.md > 1. Cultural Input & Validation`, `prd.md > 2. Entertaining Loading State`, `prd.md > 4. Reset & Re-generation`, `prd.md > States and Boundaries > Error State`
  Spec ref: `spec.md > Components > 2. LoadingState.jsx`, `spec.md > Components > 4. ErrorState.jsx`
  Build: Create `LoadingState.jsx` with rotating timer messages, implement inline shake validation in `AnchorForm.jsx`, add reset action in `TimelineView.jsx`, and create `ErrorState.jsx` for network failure handling.
  Verify (mechanical): Verify timer state transitions in `LoadingState` and verify validation rejection on empty input payload.
  Learner check: Try submitting an empty form to observe the subtle shake, then enter an anchor and watch the animated cycling copy smoothly transition into the timeline.
  Commit: `Add cycling loading state, anchor validation, and error fallback`

- [ ] **3. Live Qloo Taste Intelligence & Gemini Storytelling Integration**
  Becomes usable: The backend communicates with the live Qloo API to extract cultural affinity mappings in Tokyo/NYC and prompts Google Gemini to write personalized "Why It Fits Your Vibe" narratives on the fly, while automatically falling back to safety net data if an API is unavailable or rate-limited.
  Why now: Wires the live AI intelligence into an already stable, beautiful frontend, completing the unique kernel needed for the hackathon demo.
  PRD ref: `prd.md > Features and Behavior`, `scope.md > The Unique Kernel`, `scope.md > Qloo API Integration Plan`
  Spec ref: `spec.md > External Services and Dependencies`, `spec.md > services/qloo_client.py`, `spec.md > services/gemini_client.py`
  Build: Implement `qloo_client.py` for geo-scoped venue recommendations, implement `gemini_client.py` for narrative synthesis, wire environment variable handling from `.env`, and wrap the pipeline with transparent fallback error handling.
  Verify (mechanical): Execute backend integration test verifying Qloo payload parsing, Gemini response formatting, and fallback invocation on network error.
  Learner check: Run a generation in the browser while watching your terminal output to view the real-time API logs confirming live Qloo & Gemini execution for your 60-second video demo.
  Commit: `Integrate live Qloo taste intelligence and Gemini narrative pipeline`

## Hands-on Checkpoints

- [ ] Early usable behavior explored — Slice 1: full-stack app running locally, form inputs generate 4-stop timeline
- [ ] Final kick-the-tires exploration and feedback completed — Slice 3: complete live AI app tested end to end

## Final Review

- [ ] Final review complete — feedback resolved and learner confirms ready to ship

## Code Tour and App Map

- [ ] Learning activity complete — guided route, focused alternative, prior practice connected, or brief recap
- [ ] Optional edit and transfer reflection addressed — offered/declined/already covered/not applicable as appropriate
- [ ] `devpost/app-map.html` generated from finished code, checked, and shown, including a project-grounded practice to reuse

Activity and evidence: 
Route and stops: 
Edit outcome: 
Reflection: 
Activity mode: 

## Revisions
