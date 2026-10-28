"""Environment settings and city registry for VibeGuide."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load backend/.env then repo-root .env (later files do not override).
_BACKEND_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _BACKEND_DIR.parent
_CITIES_PATH = _BACKEND_DIR / "data" / "cities.json"
load_dotenv(_BACKEND_DIR / ".env")
load_dotenv(_REPO_ROOT / ".env")

REGION_LABELS: dict[str, str] = {
    "us": "United States",
    "europe": "Europe",
    "asia": "Asia",
    "india": "India",
    "oceania": "Oceania",
}

VALID_REGIONS = frozenset(REGION_LABELS.keys())


@dataclass(frozen=True)
class CityConfig:
    """How we address a destination in Qloo location filters and the UI."""

    name: str
    location_query: str
    region: str
    country: str
    lat: float
    lng: float
    aliases: tuple[str, ...] = ()


def _parse_city(raw: dict[str, Any]) -> CityConfig:
    city_id = str(raw.get("id") or "").strip()
    if not city_id:
        raise ValueError("City entry missing id")
    region = str(raw.get("region") or "").strip().lower()
    if region not in VALID_REGIONS:
        raise ValueError(f"City {city_id!r} has invalid region {region!r}")
    aliases_raw = raw.get("aliases") or []
    if not isinstance(aliases_raw, list):
        raise ValueError(f"City {city_id!r} aliases must be a list")
    return CityConfig(
        name=city_id,
        location_query=str(raw.get("location_query") or city_id).strip(),
        region=region,
        country=str(raw.get("country") or "").strip(),
        lat=float(raw["lat"]),
        lng=float(raw["lng"]),
        aliases=tuple(str(a).strip() for a in aliases_raw if str(a).strip()),
    )


def load_city_registry(path: Path | None = None) -> dict[str, CityConfig]:
    """Load cities from JSON. Fail fast if the file is missing or invalid."""
    cities_path = path or _CITIES_PATH
    if not cities_path.is_file():
        raise FileNotFoundError(f"City registry not found: {cities_path}")
    data = json.loads(cities_path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        raise ValueError(f"City registry must be a non-empty list: {cities_path}")
    registry: dict[str, CityConfig] = {}
    for item in data:
        if not isinstance(item, dict):
            raise ValueError("Each city entry must be an object")
        cfg = _parse_city(item)
        if cfg.name in registry:
            raise ValueError(f"Duplicate city id: {cfg.name!r}")
        registry[cfg.name] = cfg
    return registry


CITY_REGISTRY: dict[str, CityConfig] = load_city_registry()


def city_ids() -> list[str]:
    """Stable sorted list of city ids for API enums and validation messages."""
    return sorted(CITY_REGISTRY.keys())


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
    qloo_timeout_seconds: float = 6.0
    qloo_max_retries: int = 1
    qloo_cache_ttl_seconds: float = 900.0
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
        qloo_timeout_seconds=float(os.getenv("QLOO_TIMEOUT_SECONDS", "6")),
        qloo_max_retries=int(os.getenv("QLOO_MAX_RETRIES", "1")),
        qloo_cache_ttl_seconds=float(os.getenv("QLOO_CACHE_TTL_SECONDS", "900")),
        agent_max_steps=int(os.getenv("AGENT_MAX_STEPS", "4")),
    )


def clear_settings_cache() -> None:
    """Test helper: reload settings after mutating env."""
    get_settings.cache_clear()
