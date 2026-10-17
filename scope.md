# VibeGuide — Project Scope

## Project Name
**VibeGuide** — AI Travel Concierge Powered by Cultural Taste Intelligence

## Problem Statement
Generic travel guides ignore personal taste — they serve the same "Top 10" lists to everyone regardless of who they are. A jazz-loving street-art enthusiast gets the same restaurant recommendations as a fine-dining opera fan. **VibeGuide** uses Qloo's cultural AI to build city itineraries that match your unique preferences in food, music, art, and nightlife — so every trip *feels like you*.

## Target User
**Millennial / Gen-Z Explorers (ages 22–35)**
- Culturally curious travelers who prioritize authentic, experience-rich trips over tourist traps
- Travel 2–4 times per year; rely on word-of-mouth and social discovery
- Value personalization, aesthetics, and "hidden gem" recommendations
- Comfortable with AI-powered tools and sharing taste preferences

## Core Features (MVP)

### 1. Taste Profile Onboarding
User selects a handful of artists, restaurants, cuisines, or vibes they love. Qloo's API builds a multi-dimensional cultural taste profile behind the scenes — no lengthy questionnaires required.

### 2. City Match & Itinerary Generator
Given a destination city, VibeGuide generates a day-by-day itinerary of restaurants, bars, galleries, music venues, and attractions that align with the user's taste profile. Each suggestion includes a "taste match %" score.

### 3. Multi-Category Taste Matching
Instead of recommending within a single category, VibeGuide uses Qloo across multiple entity types (restaurants, music, film, attractions) to build a *holistic vibe*. Loving Radiohead can influence which cocktail bar gets recommended.

### 4. Real-Time Refine (Thumbs Up / Thumbs Down)
Users can thumbs-up or thumbs-down individual suggestions within the itinerary. VibeGuide sends this feedback to Qloo's similarity API and re-ranks the remaining suggestions on the fly — the itinerary gets smarter as you interact with it.

## Technology Stack

| Layer       | Technology                     | Purpose                                      |
|-------------|--------------------------------|----------------------------------------------|
| Backend     | **Python 3.13 + FastAPI**      | API server, Qloo integration, taste logic    |
| Frontend    | **React (Vite)**               | Onboarding UI, interactive itinerary view    |
| Database    | **SQLite**                     | User profiles, saved itineraries (lightweight)|
| Styling     | **Tailwind CSS**               | Rapid, responsive UI design                  |
| API         | **Qloo Taste API**             | Cultural intelligence & recommendations      |
| VCS         | **Git**                        | Version control                              |

## Qloo API Integration Plan

### Deep Multi-Endpoint Integration

1. **Taste Profile Construction** (`/predict` or `/recommend`)
   - Accept user seed preferences (favorite artists, cuisines, films, places)
   - Build a taste vector that captures the user's cultural identity across categories

2. **Cross-Category Recommendations** (entity-to-entity similarity)
   - Map taste signals across domains: music → dining → nightlife → attractions
   - E.g., "loves Radiohead + ramen + indie film" → suggest a specific vinyl bar with lo-fi ambiance

3. **Location-Aware Filtering** (geo parameters)
   - Scope all recommendations to the target destination city
   - Ensure every suggestion is a real, visitable place in the chosen location

4. **Real-Time Re-Ranking** (feedback loop)
   - Send thumbs-up/thumbs-down signals back to Qloo
   - Dynamically re-rank remaining itinerary suggestions based on refined taste signals
   - The itinerary improves with every interaction

## Success Criteria (Hackathon Demo)
- [ ] User can complete taste onboarding in < 60 seconds
- [ ] Itinerary generates for at least 3 major cities
- [ ] Cross-category recommendations are visibly powered by Qloo
- [ ] Thumbs-up/down feedback visibly changes the itinerary
- [ ] Clean, demo-ready UI with taste match scores

## Out of Scope (Post-Hackathon)
- User authentication / accounts
- Booking integrations (hotels, flights, reservations)
- Mobile native app
- Multi-user group trip planning
- Offline mode

---

*Generated: 2026-10-17 | VibeGuide Hackathon Planning — Stage 1 Complete*
