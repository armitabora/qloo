"""VibeGuide FastAPI entrypoint — thin routes over the Qloo pipeline."""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from agent.agent import AgentUnavailableError, refine_itinerary
from config import CITY_REGISTRY, REGION_LABELS, city_ids, get_settings
from models import (
    CitiesResponse,
    CityOption,
    HealthResponse,
    ItineraryRequest,
    ItineraryResponse,
    RefineRequest,
    RegionMeta,
)
from pipeline import NoAnchorsResolvedError, generate_itinerary

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("vibe")

settings = get_settings()

app = FastAPI(
    title="VibeGuide",
    description="Taste-intelligent travel concierge powered by Qloo + Gemini",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    s = get_settings()
    return HealthResponse(
        status="ok",
        qloo_configured=s.has_qloo_key,
        gemini_configured=s.has_gemini_key,
        cities=city_ids(),
    )


@app.get("/api/cities", response_model=CitiesResponse)
async def list_cities() -> CitiesResponse:
    cities = [
        CityOption(
            id=cfg.name,
            label=cfg.name,
            location_query=cfg.location_query,
            region=cfg.region,
            country=cfg.country,
            lat=cfg.lat,
            lng=cfg.lng,
            aliases=list(cfg.aliases),
        )
        for cfg in sorted(CITY_REGISTRY.values(), key=lambda c: (c.region, c.name))
    ]
    regions = [
        RegionMeta(id=rid, label=label)
        for rid, label in REGION_LABELS.items()
    ]
    return CitiesResponse(cities=cities, regions=regions)


@app.post("/api/generate-itinerary", response_model=ItineraryResponse)
@app.post("/api/itinerary", response_model=ItineraryResponse)
async def api_generate_itinerary(payload: ItineraryRequest) -> ItineraryResponse:
    logger.info(
        "generate city=%s music=%r film=%r vibe=%r",
        payload.city,
        payload.music,
        payload.film,
        payload.vibe,
    )
    try:
        return await generate_itinerary(payload)
    except NoAnchorsResolvedError as exc:
        raise HTTPException(
            status_code=422,
            detail={
                "message": str(exc),
                "anchors_resolved": [r.model_dump() for r in exc.resolutions],
            },
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("generate failed")
        raise HTTPException(status_code=500, detail=f"Itinerary generation failed: {exc}") from exc


@app.post("/api/refine", response_model=ItineraryResponse)
async def api_refine(payload: RefineRequest) -> ItineraryResponse:
    logger.info("refine instruction=%r city=%s", payload.instruction, payload.itinerary.city)
    try:
        return await refine_itinerary(payload)
    except AgentUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("refine failed")
        raise HTTPException(status_code=500, detail=f"Refine failed: {exc}") from exc
