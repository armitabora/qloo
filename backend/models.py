"""Pydantic request and response schemas for the VibeGuide API."""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from config import CITY_REGISTRY


class ItineraryRequest(BaseModel):
    """Incoming request from the frontend."""

    city: str
    music: Optional[str] = None
    film: Optional[str] = None
    vibe: Optional[str] = None

    @model_validator(mode="after")
    def at_least_one_anchor(self) -> "ItineraryRequest":
        music = (self.music or "").strip() or None
        film = (self.film or "").strip() or None
        vibe = (self.vibe or "").strip() or None
        object.__setattr__(self, "music", music)
        object.__setattr__(self, "film", film)
        object.__setattr__(self, "vibe", vibe)
        if not any([music, film, vibe]):
            raise ValueError(
                "At least one cultural anchor (music, film, or vibe) is required."
            )
        if self.city not in CITY_REGISTRY:
            raise ValueError(
                f"Unknown city {self.city!r}. See GET /api/cities for supported destinations."
            )
        return self

    def anchor_pairs(self) -> list[tuple[str, str]]:
        """Return (kind, text) pairs for non-empty anchors."""
        pairs: list[tuple[str, str]] = []
        if self.music:
            pairs.append(("music", self.music))
        if self.film:
            pairs.append(("film", self.film))
        if self.vibe:
            pairs.append(("vibe", self.vibe))
        return pairs


class Influence(BaseModel):
    """Which resolved anchor contributed to a place recommendation."""

    anchor: str
    matched_name: str
    score: float = 0.0


class AnchorResolution(BaseModel):
    """How a free-text cultural anchor mapped onto Qloo IDs."""

    input: str
    kind: Literal["music", "film", "vibe"]
    resolved: bool = False
    matched_name: Optional[str] = None
    entity_id: Optional[str] = None
    tag_id: Optional[str] = None
    entity_type: Optional[str] = None


class ItineraryStop(BaseModel):
    """A single stop in the day itinerary."""

    phase: str
    venue: str
    vibe_narrative: str
    category: str = ""
    entity_id: Optional[str] = None
    address: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    affinity: Optional[float] = None
    influenced_by: list[Influence] = Field(default_factory=list)
    image_url: Optional[str] = None
    source: Literal["qloo", "fallback"] = "qloo"


class ResponseMeta(BaseModel):
    qloo_calls: int = 0
    latency_ms: int = 0
    narrative_engine: Literal["gemini", "template"] = "template"


class ItineraryResponse(BaseModel):
    """Complete itinerary returned to the frontend (backward compatible)."""

    city: str
    stops: list[ItineraryStop]
    is_fallback: bool = False
    anchors_resolved: list[AnchorResolution] = Field(default_factory=list)
    meta: ResponseMeta = Field(default_factory=ResponseMeta)


class RefineRequest(BaseModel):
    """Agentic refinement of an existing itinerary."""

    instruction: str
    itinerary: ItineraryResponse
    city: Optional[str] = None
    music: Optional[str] = None
    film: Optional[str] = None
    vibe: Optional[str] = None

    @model_validator(mode="after")
    def instruction_required(self) -> "RefineRequest":
        if not (self.instruction or "").strip():
            raise ValueError("instruction is required.")
        object.__setattr__(self, "instruction", self.instruction.strip())
        return self


class HealthResponse(BaseModel):
    status: str = "ok"
    qloo_configured: bool = False
    gemini_configured: bool = False
    cities: list[str] = Field(default_factory=list)


class CityOption(BaseModel):
    id: str
    label: str
    location_query: str
    region: str
    country: str
    lat: float
    lng: float
    aliases: list[str] = Field(default_factory=list)


class RegionMeta(BaseModel):
    id: str
    label: str


class CitiesResponse(BaseModel):
    cities: list[CityOption]
    regions: list[RegionMeta] = Field(default_factory=list)


class ErrorBody(BaseModel):
    detail: str
    code: Optional[str] = None
    extra: dict[str, Any] = Field(default_factory=dict)
