---
doc: scope
status: approved
---

# VibeGuide

A taste-intelligent travel concierge: enter a city and a few cultural anchors you love, get a curated 1-day itinerary where every stop comes with a personalized explanation of *why* it fits your vibe — powered by Qloo's cultural AI and an LLM storyteller.

## The Unique Kernel

The cross-domain "Why It Fits Your Vibe" explanation. Plenty of apps recommend places; VibeGuide is the one that tells you *"Because you love Studio Ghibli and lo-fi hip hop, you'll appreciate the hand-painted signage, warm wood interior, and quiet back-alley location of this kissaten."* The magic isn't the recommendation — it's the narrative bridge between your taste in film, music, and aesthetics and a physical place you've never been. Qloo provides the taste intelligence; an LLM synthesizes it into a story that feels like a hip local friend explaining why you'd love this spot.

## Who It's For

An independent, culturally curious traveler (early 20s–30s) arriving in an unfamiliar major city. They're overwhelmed by generic "Top 10" tourist lists that are completely blind to personal taste. Today they scroll TripAdvisor or Google Maps and get the same crowded recommendations as everyone else. They want a personalized cheat sheet that *gets* them — not a database search.

## The Core Loop

1. Pick a city from a dropdown (Tokyo or New York).
2. Enter 2–3 cultural anchors: a favorite artist/band, a film or director, and/or a vibe tag.
3. Hit **"Generate My Day."**
4. Read a 4-stop itinerary (Morning → Afternoon → Evening → Night), each with a venue and a "Why It Fits Your Vibe" paragraph.

They come back because different anchors produce a completely different day in the same city.

## Inspiration & Identity

Minimalist, dark mode or warm editorial aesthetic — clean and sleek, not cluttered. The feel of a curated zine or a hip local's handwritten recommendation list, not a travel booking app. Think the visual restraint of Are.na or a well-designed Notion page.

## Why This Matters to the Learner

> "Win this hackathon." First full-stack app, first time using an AI agent to plan and build. The goal is a polished, working proof of concept that impresses judges.

## What "Working" Looks Like

The 60-second demo:

- **(0:00–0:10)** Open the localhost app. Select "Tokyo." Type "Studio Ghibli" and "Lo-fi Hip Hop" as anchors.
- **(0:10–0:20)** Click "Generate My Day." A sleek loading state (spinner or skeleton) shows while Qloo + LLM process.
- **(0:20–0:50)** The itinerary loads: 4 stops (Morning café, Afternoon cultural spot, Evening dining, Night venue). Scroll through, pause to highlight a "Why It Fits Your Vibe" paragraph so judges can read the cross-domain reasoning.
- **(0:50–1:00)** Switch to VS Code terminal, show logs proving Qloo API and LLM were actually invoked — not hardcoded data.

**Technical "done":** runs flawlessly on localhost, API keys work, UI is presentable, public GitHub repo has code + `devpost/` planning files + a clear `README.md` with run instructions.

## The PoC Boundary

- Single-page app: one screen, one flow
- Exactly 2 cities (Tokyo, New York) via dropdown — guarantees dense, high-quality Qloo data
- 2–3 cultural anchor inputs (music artist, film/director, vibe tag)
- 4-stop 1-day itinerary (Morning, Afternoon, Evening, Night)
- "Why It Fits Your Vibe" LLM-generated narrative per stop
- Graceful loading state during Qloo + LLM processing
- Backend flow: FastAPI → Qloo API (taste data) → LLM (Gemini or Groq, free tier) → narrative
- Localhost only — deployment optional

## Later

- More cities (London, Paris, etc.) once the core loop is proven
- Thumbs-up/thumbs-down feedback to refine results
- Shareable itinerary cards (exportable link or visual)
- "Surprise Me" mode — skip the city, let VibeGuide pick based on vibe + budget
- User accounts and saved itineraries

## Explicitly Cut

- **User authentication / accounts** — unnecessary friction for a taste-in, itinerary-out PoC
- **Database** — no persistence needed; every generation is stateless
- **Booking integrations** — not a travel agent, it's a taste concierge
- **Mobile app** — web on localhost is sufficient for the demo
- **More than 2 cities** — depth over breadth; thin results in obscure cities would hurt the demo
- **Multi-user / group trips** — one person, one vibe, one day
