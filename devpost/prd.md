---
doc: prd
status: approved
---

# VibeGuide — Product Requirements

A taste-intelligent travel concierge that transforms personal cultural affinities into a curated, 1-day city itinerary with cross-domain vibe explanations.
Source: `scope.md > VibeGuide` and `scope.md > The Core Loop`.

## The Core Journey

1. **Arrival**: The user lands on a clean, single-page web app with a centered column, generous whitespace, and a minimalist dark-mode editorial layout (deep charcoal background with soft off-white typography).
2. **First Impression**: The eye is drawn to the bold header "VibeGuide." and subheadline "Enter your cultural anchors. Discover your city."
3. **Input Selection**:
   - Destination selector: Pre-selected with "Tokyo" (toggle/dropdown with "Tokyo" and "New York").
   - Three minimalist underlined input fields:
     - Field 1 (Music): "e.g., Radiohead, Daft Punk..." (Label: Favorite Music)
     - Field 2 (Film): "e.g., Studio Ghibli, Wes Anderson..." (Label: Favorite Film/Director)
     - Field 3 (Vibe): "e.g., Cyberpunk neon, Cozy lo-fi..." (Label: Desired Vibe)
4. **Validation**: The user must select a city and provide at least one cultural anchor. If invalid, the fields show a subtle red underline or gentle shake; no disruptive modal popups.
5. **Generation Trigger**: The user clicks the high-contrast primary CTA button "Generate My Day ✨".
6. **Dynamic Loading**: The button transitions into a loading spinner. Below the spinner, cycling status messages appear every few seconds ("Analyzing your taste..." → "Mapping the city..." → "Writing your itinerary...").
7. **Itinerary Reveal**:
   - The input section smoothly fades out/slides up.
   - Header fades in: "Your Vibe in [City]".
   - A vertical timeline is displayed with a subtle connecting line down the left edge.
   - Four distinct stops are revealed in chronological order:
     - **Morning**: Café
     - **Afternoon**: Cultural stop (gallery, bookstore, or record shop)
     - **Evening**: Dining spot
     - **Night**: Venue or hangout
8. **Vibe Storytelling**: Every stop prominently features an indented "Why It Fits Your Vibe" blockquote starting with a ✨ icon, revealing cross-domain reasoning directly without accordion or click friction.
9. **Loop Back**: At the bottom of the timeline, a ghost-style button "Plan Another Day" / "Change Vibe" resets the view smoothly back to the input state.

## Screens and Layout

- **Single Surface (SPA)**: Everything happens on a single responsive view with no page reloads.
- **Initial Viewport**: Fits entirely above the fold without scrolling, keeping user focus on the inputs and primary CTA.
- **Results Viewport**: Clean vertical scroll with persistent narrative cards and a return button at the bottom.

## Look and Feel

- **Theme**: Dark mode aesthetic, editorial zine / Are.na / Notion styling.
- **Palette**: Deep charcoal background (`#121214` / `#18181b`), subtle borders (`#27272a`), soft white headings (`#f4f4f5`), muted gray labels (`#a1a1aa`), accent highlights (`#e4e4e7` / gold/violet shimmer for badges).
- **Typography**: Clean, high-legibility sans-serif with refined tracking and editorial weight contrasts.
- **Micro-interactions**: Subtle focus underlines, gentle button hover states, smooth CSS fades between input and results.

## Features and Behavior

### 1. Cultural Input & Validation
- **Behavior**: Accepts city selection (Tokyo, New York) and up to three optional cultural anchors (Music, Film, Vibe). Requires at least 1 anchor to submit.
- **Acceptance Criteria**:
  - [x] Submitting with 0 anchors displays subtle inline validation warning and stops submission.
  - [x] Submitting with 1, 2, or 3 anchors proceeds to generation.

### 2. Entertaining Loading State
- **Behavior**: Displays an animated spinner accompanied by sequential status copy that cycles every 2–3 seconds while backend queries Qloo and the LLM.
- **Acceptance Criteria**:
  - [x] Button changes to disabled state with loading spinner.
  - [x] Text rotates through "Analyzing your taste...", "Mapping the city...", and "Writing your itinerary...".

### 3. Timeline Itinerary & Vibe Badges
- **Behavior**: Renders 4 structured cards along a continuous vertical timeline. Each card contains Phase (MORNING, AFTERNOON, EVENING, NIGHT), Venue Name, Category Tag, and the uncollapsed "Why It Fits Your Vibe" narrative.
- **Acceptance Criteria**:
  - [x] Exactly 4 cards are rendered representing the complete day.
  - [x] Each card displays the venue name and category.
  - [x] "Why It Fits Your Vibe" explanation is directly readable on screen without click-to-expand.

### 4. Reset & Re-generation
- **Behavior**: "Plan Another Day" button resets the view to allow trying new anchors or changing cities.
- **Acceptance Criteria**:
  - [x] Clicking reset returns smoothly to the input form with previous inputs preserved or cleared.

## States and Boundaries

- **Default State**: Clean empty input form, destination set to Tokyo.
- **Validating State**: Subtle error indication if submitted empty.
- **Loading State**: Spinner with cycling status copy.
- **Success State**: "Your Vibe in [City]" with 4 timeline cards.
- **Error State**: Friendly dark-mode fallback banner: "Vibe check failed. The city might be too sleepy right now, or our AI needs a coffee." with a "Try Different Anchors" button to reset.

## Product Decisions

- **Visible Vibe Explanations**: Kept visible by default rather than tucked into accordions to maximize impact during the 60-second hackathon demo video.
- **Cycling Loading Text**: Keeps the user engaged during the 5–10s combined latency of Qloo taste queries + LLM prompt completions.
- **Two Cities Only**: Tokyo & New York ensure high-density place data and reliable recommendations for the MVP.
- **Stateless Architecture**: No user login, no persistent database; keeps the POC lightweight, reliable, and fast to execute.

## What We're Building

- Single-page React frontend with Tailwind CSS (editorial dark theme).
- Fast, accessible input form with validation.
- Animated multi-stage loading state.
- Chronological 4-stop timeline with prominent vibe narrative blocks.
- Resilient error card with retry button.

## Deferred From the POC

- Multi-day itineraries (2-day, weekend, week-long).
- Interactive map integration (Leaflet/Mapbox).
- Dynamic city search beyond Tokyo and New York.
- Social sharing and downloadable PDF/image cards.

## Non-Goals

- User account registration or profile management.
- Live booking, reservation, or ticketing integrations.
- Turn-by-turn navigation or transit directions.
- Native mobile applications (iOS/Android).

## Open Questions

- *Resolved*: LLM choice for narrative generation — fast, lightweight model (Gemini or Groq API).
- *Resolved*: Qloo endpoints to target for venue retrieval by taste affinity in Tokyo/NYC.
