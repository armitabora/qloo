"""Environment settings and city registry for VibeGuide."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load backend/.env then repo-root .env (later files do not override).
_BACKEND_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _BACKEND_DIR.parent
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_REPO_ROOT / ".env")


@dataclass(frozen=True)
class CityConfig:
    """How we address a destination in Qloo location filters."""

    name: str
    location_query: str


CITY_REGISTRY: dict[str, CityConfig] = {
    "Tokyo": CityConfig(name="Tokyo", location_query="Tokyo"),
    "New York": CityConfig(name="New York", location_query="New York City"),
}

PHASES: tuple[str, ...] = ("MORNING", "AFTERNOON", "EVENING", "NIGHT")

# Free-text queries used to discover category tag IDs via /v2/tags.
# Resolved IDs are cached; these strings are never sent as filter.tags.
PHASE_CATEGORY_QUERIES: dict[str, tuple[str, ...]] = {
    "MORNING": ("cafe", "coffee shop", "bakery"),
    "AFTERNOON": ("museum", "art gallery", "bookstore", "record store"),
    "EVENING": ("restaurant",),
    "NIGHT": ("bar", "cocktail bar", "jazz club", "music venue"),
}

# Broader fallback category queries when a phase returns empty.
PHASE_BROAD_CATEGORY_QUERIES: dict[str, tuple[str, ...]] = {
    "MORNING": ("cafe", "coffee", "bakery", "tea"),
    "AFTERNOON": ("museum", "gallery", "bookstore", "shop", "attraction"),
    "EVENING": ("restaurant", "dining", "food"),
    "NIGHT": ("bar", "nightlife", "club", "venue"),
}


@dataclass(frozen=True)
class Settings:
    qloo_api_key: str = ""
    qloo_base_url: str = "https://hackathon.api.qloo.com"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    allowed_origins: tuple[str, ...] = ("http://localhost:5173", "http://127.0.0.1:5173")
    qloo_timeout_seconds: float = 8.0
    qloo_max_retries: int = 2
    qloo_cache_ttl_seconds: float = 300.0
    agent_max_steps: int = 4

    @property
    def has_qloo_key(self) -> bool:
        return bool(self.qloo_api_key.strip())

    @property
    def has_gemini_key(self) -> bool:
        return bool(self.gemini_api_key.strip())


def _parse_origins(raw: str | None) -> tuple[str, ...]:
    if not raw or not raw.strip():
        return ("http://localhost:5173", "http://127.0.0.1:5173")
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return tuple(parts) if parts else ("http://localhost:5173", "http://127.0.0.1:5173")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        qloo_api_key=os.getenv("QLOO_API_KEY", "").strip(),
        qloo_base_url=os.getenv("QLOO_BASE_URL", "https://hackathon.api.qloo.com").rstrip("/"),
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip() or "gemini-3.8-flash",
        allowed_origins=_parse_origins(os.getenv("ALLOWED_ORIGINS")),
        qloo_timeout_seconds=float(os.getenv("QLOO_TIMEOUT_SECONDS", "12")),
        qloo_max_retries=int(os.getenv("QLOO_MAX_RETRIES", "2")),
        qloo_cache_ttl_seconds=float(os.getenv("QLOO_CACHE_TTL_SECONDS", "300")),
        agent_max_steps=int(os.getenv("AGENT_MAX_STEPS", "4")),
    )


def clear_settings_cache() -> None:
    """Test helper: reload settings after mutating env."""
    get_settings.cache_clear()
