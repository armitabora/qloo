"""Pydantic request and response schemas for the VibeGuide API."""

from typing import Optional, List
from pydantic import BaseModel, model_validator


class ItineraryRequest(BaseModel):
    """Incoming request from the frontend."""
    city: str  # Must be "Tokyo" or "New York"
    music: Optional[str] = None
    film: Optional[str] = None
    vibe: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one_anchor(self):
        if not any([self.music, self.film, self.vibe]):
            raise ValueError("At least one cultural anchor (music, film, or vibe) is required.")
        if self.city not in ("Tokyo", "New York"):
            raise ValueError("City must be 'Tokyo' or 'New York'.")
        return self


class ItineraryStop(BaseModel):
    """A single stop in the day itinerary."""
    phase: str       # "Morning", "Afternoon", "Evening", "Night"
    venue: str       # e.g. "Lion Kissaten"
    category: str    # e.g. "Historic Vinyl Cafe"
    vibe_narrative: str  # The "Why It Fits Your Vibe" paragraph


class ItineraryResponse(BaseModel):
    """Complete itinerary returned to the frontend."""
    city: str
    is_fallback: bool = False
    stops: List[ItineraryStop]
