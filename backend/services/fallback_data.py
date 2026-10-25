"""
High-fidelity fallback itineraries for Tokyo and New York.

These are pre-computed, authentic datasets that serve as the demo safety net.
If the Qloo API or Gemini LLM is unavailable (timeout, rate-limit, network drop),
FastAPI transparently returns this data so the hackathon demo never breaks.
"""

FALLBACK_ITINERARIES = {
    "Tokyo": [
        {
            "phase": "Morning",
            "venue": "Lion Kissaten",
            "category": "Historic Vinyl Listening Cafe",
            "vibe_narrative": (
                "Because you gravitate toward lo-fi atmospheres and cinematic "
                "stillness, Lion's cathedral-like wooden interior: dim lighting, "
                "vintage speakers stacked floor to ceiling, and a strict no-talking "
                "policy. It feels like stepping into a Studio Ghibli scene where time "
                "slows down and every record played is chosen with reverence."
            ),
        },
        {
            "phase": "Afternoon",
            "venue": "Flash Disc Ranch",
            "category": "Underground Record Shop",
            "vibe_narrative": (
                "Tucked on the second floor of a Shimokitazawa side street, Flash "
                "Disc Ranch mirrors the deep-crate ethos behind your favorite music. "
                "The owner curates rare Japanese city pop, ambient, and shoegaze vinyl, "
                "genres that share DNA with lo-fi production and the dreamy aesthetics "
                "of the films you love."
            ),
        },
        {
            "phase": "Evening",
            "venue": "Afuri Ramen",
            "category": "Minimalist Yuzu Ramen Bar",
            "vibe_narrative": (
                "Afuri strips ramen down to its essence: a translucent yuzu-salt "
                "broth, clean design, and open kitchen, matching the restraint and "
                "intentionality you appreciate in both music production and film "
                "direction. It's the culinary equivalent of a well-mixed lo-fi track: "
                "nothing wasted, everything in its place."
            ),
        },
        {
            "phase": "Night",
            "venue": "Bar Martha",
            "category": "Hidden Jazz & Vinyl Bar",
            "vibe_narrative": (
                "Down a narrow Golden Gai alley, Bar Martha seats eight people around "
                "a candlelit counter while the bartender spins jazz and soul vinyl. "
                "The intimacy and analog warmth echo your taste for lo-fi textures and "
                "the moody, back-alley cinematography of Wong Kar-wai. It's a place that "
                "feels like a secret meant just for you."
            ),
        },
    ],
    "New York": [
        {
            "phase": "Morning",
            "venue": "Devoción",
            "category": "Colombian Craft Coffee & Gallery",
            "vibe_narrative": (
                "Devoción's Williamsburg greenhouse: raw brick walls draped in "
                "living plants, skylights flooding the room with natural light, and "
                "single-origin beans roasted on-site. It matches the organic warmth and "
                "artistic intentionality you value. It's a morning ritual that feels "
                "curated, not commercial."
            ),
        },
        {
            "phase": "Afternoon",
            "venue": "Rough Trade NYC",
            "category": "Indie Record Store & Performance Space",
            "vibe_narrative": (
                "Rough Trade bridges the gap between your music taste and physical "
                "exploration: a sprawling Rockefeller Center outpost stocking vinyl, "
                "hosting in-store performances, and curating staff picks that lean "
                "toward the indie, experimental, and lo-fi scenes you're drawn to."
            ),
        },
        {
            "phase": "Evening",
            "venue": "Xi'an Famous Foods",
            "category": "Hand-Pulled Noodle Counter",
            "vibe_narrative": (
                "No reservations, no pretense. Just fiery cumin lamb noodles pulled "
                "to order at a tight counter. Xi'an Famous Foods carries the same "
                "unpretentious authenticity as the underground music scenes and raw "
                "filmmaking you admire: substance over spectacle, flavor over flash."
            ),
        },
        {
            "phase": "Night",
            "venue": "Nowadays",
            "category": "Indoor-Outdoor DJ Venue & Garden",
            "vibe_narrative": (
                "Ridgewood's Nowadays balances an eclectic DJ lineup with an expansive "
                "outdoor garden lit by string lights, bridging your love of curated "
                "sonic experiences with the atmospheric, almost filmic quality of a "
                "space that feels both intentional and free. It's where lo-fi meets "
                "real life."
            ),
        },
    ],
}


def get_fallback_itinerary(city: str) -> list[dict] | None:
    """Return curated fallback stops for the city, or None if none exist.

    Only Tokyo and New York have curated fallbacks. Other cities must not
    silently reuse another city's venues.
    """
    return FALLBACK_ITINERARIES.get(city)


def degraded_fallback_slots(city: str) -> list[dict]:
    """Honest placeholder stops when Qloo is unavailable and no curated data exists."""
    note = (
        f"We could not load live recommendations for {city} right now. "
        "Try again shortly, or pick Tokyo or New York for a curated demo day."
    )
    phases = ("Morning", "Afternoon", "Evening", "Night")
    labels = (
        "Morning stop unavailable",
        "Afternoon stop unavailable",
        "Evening stop unavailable",
        "Night stop unavailable",
    )
    return [
        {
            "phase": phase,
            "venue": label,
            "category": "Unavailable",
            "vibe_narrative": note,
        }
        for phase, label in zip(phases, labels)
    ]
