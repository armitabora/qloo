"""Itinerary orchestration: resolve → place phases → narratives → response."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Optional

from config import PHASES, get_settings
from models import (
    AnchorResolution,
    ItineraryRequest,
    ItineraryResponse,
    ItineraryStop,
    ResponseMeta,
)
from narrative.engine import NarrativeEngine
from qloo.categories import CategoryResolver
from qloo.client import QlooClient, QlooError
from qloo.places import PlaceCandidate, PlaceFinder
from qloo.resolver import AnchorResolver
from services.fallback_data import degraded_fallback_slots, get_fallback_itinerary

logger = logging.getLogger("vibe.pipeline")


class NoAnchorsResolvedError(Exception):
    """Raised when every cultural anchor fails to resolve."""

    def __init__(self, resolutions: list[AnchorResolution]):
        super().__init__("None of the cultural anchors could be resolved in Qloo.")
        self.resolutions = resolutions


async def _pick_phase_place(
    finder: PlaceFinder,
    *,
    city: str,
    phase: str,
    resolutions: list[AnchorResolution],
    exclude_ids: list[str],
) -> tuple[Optional[PlaceCandidate], int]:
    """Try strict tags → broad tags → signals-only. Returns (place, extra_calls)."""
    extra = 0
    attempts = (
        {"use_broad_tags": False, "skip_tags": False},
        {"use_broad_tags": True, "skip_tags": False},
        {"use_broad_tags": False, "skip_tags": True},
    )
    for kwargs in attempts:
        try:
            candidates = await finder.find_for_phase(
                city=city,
                phase=phase,
                resolutions=resolutions,
                exclude_ids=exclude_ids or None,
                take=10,
                **kwargs,
            )
            extra += 1
        except QlooError as exc:
            logger.warning("phase %s attempt failed: %s", phase, exc)
            extra += 1
            continue
        for cand in candidates:
            if cand.entity_id not in exclude_ids:
                return cand, extra
    return None, extra


async def _build_places(
    client: QlooClient,
    request: ItineraryRequest,
    resolutions: list[AnchorResolution],
) -> tuple[list[Optional[PlaceCandidate]], int]:
    """
    Build one place per phase.

    Phases run with a light sequential exclude chain so we can dedupe:
    we fetch MORNING first, then fan out the rest in parallel with that ID excluded,
    then resolve residual collisions.
    """
    categories = CategoryResolver(client)
    finder = PlaceFinder(client, categories)

    # Warm category tags once (counts as cached subsequent calls).
    await categories.warm_all()

    places: list[Optional[PlaceCandidate]] = [None] * len(PHASES)
    used: list[str] = []
    calls = 0

    # Morning first to seed exclusions.
    morning, extra = await _pick_phase_place(
        finder,
        city=request.city,
        phase="MORNING",
        resolutions=resolutions,
        exclude_ids=[],
    )
    calls += extra
    places[0] = morning
    if morning:
        used.append(morning.entity_id)

    async def _one(index: int, phase: str) -> tuple[int, Optional[PlaceCandidate], int]:
        place, extra_calls = await _pick_phase_place(
            finder,
            city=request.city,
            phase=phase,
            resolutions=resolutions,
            exclude_ids=list(used),
        )
        return index, place, extra_calls

    tasks = [
        _one(i, phase)
        for i, phase in enumerate(PHASES)
        if i > 0
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for result in results:
        if isinstance(result, Exception):
            logger.warning("phase task error: %s", result)
            continue
        index, place, extra_calls = result
        calls += extra_calls
        if place and place.entity_id in used:
            # Collision — retry with stricter exclude.
            place2, extra2 = await _pick_phase_place(
                finder,
                city=request.city,
                phase=PHASES[index],
                resolutions=resolutions,
                exclude_ids=used + [place.entity_id],
            )
            calls += extra2
            place = place2
        places[index] = place
        if place:
            used.append(place.entity_id)

    return places, calls


def _fallback_slots_for_city(city: str) -> list[dict]:
    """Curated slots when available; otherwise honest degraded placeholders."""
    curated = get_fallback_itinerary(city)
    if curated:
        return curated
    return degraded_fallback_slots(city)


def _fallback_response(
    request: ItineraryRequest,
    resolutions: list[AnchorResolution],
    *,
    latency_ms: int,
    qloo_calls: int,
) -> ItineraryResponse:
    raw = _fallback_slots_for_city(request.city)
    stops = [
        ItineraryStop(
            phase=item["phase"].upper() if item["phase"].lower() in {p.lower() for p in PHASES} else item["phase"],
            venue=item["venue"],
            category=item.get("category", ""),
            vibe_narrative=item["vibe_narrative"],
            source="fallback",
        )
        for item in raw
    ]
    # Normalize phase labels to MORNING/…
    normalized = []
    for stop, phase in zip(stops, PHASES):
        normalized.append(stop.model_copy(update={"phase": phase}))
    return ItineraryResponse(
        city=request.city,
        stops=normalized,
        is_fallback=True,
        anchors_resolved=resolutions,
        meta=ResponseMeta(
            qloo_calls=qloo_calls,
            latency_ms=latency_ms,
            narrative_engine="template",
        ),
    )


async def generate_itinerary(
    request: ItineraryRequest,
    *,
    client: Optional[QlooClient] = None,
    narrative: Optional[NarrativeEngine] = None,
    settings=None,
) -> ItineraryResponse:
    started = time.perf_counter()
    owns_client = client is None
    if settings is None:
        settings = client.settings if client is not None else get_settings()
    client = client or QlooClient(settings=settings)
    narrative = narrative or NarrativeEngine(settings=settings)
    qloo_calls_before = client.call_count

    try:
        if not settings.has_qloo_key:
            logger.warning("No QLOO_API_KEY — serving fallback itinerary")
            return _fallback_response(
                request,
                [],
                latency_ms=int((time.perf_counter() - started) * 1000),
                qloo_calls=0,
            )

        resolver = AnchorResolver(client)
        resolutions = await resolver.resolve_all(
            music=request.music,
            film=request.film,
            vibe=request.vibe,
        )
        if not AnchorResolver.any_resolved(resolutions):
            raise NoAnchorsResolvedError(resolutions)

        try:
            places, _ = await _build_places(client, request, resolutions)
        except QlooError as exc:
            logger.error("Qloo pipeline failure, using fallback: %s", exc)
            return _fallback_response(
                request,
                resolutions,
                latency_ms=int((time.perf_counter() - started) * 1000),
                qloo_calls=client.call_count - qloo_calls_before,
            )

        if not any(places):
            logger.error("No places returned for any phase — fallback")
            return _fallback_response(
                request,
                resolutions,
                latency_ms=int((time.perf_counter() - started) * 1000),
                qloo_calls=client.call_count - qloo_calls_before,
            )

        # Fill missing phases from curated fallback only (never another city's venues).
        curated_slots = get_fallback_itinerary(request.city)
        chosen: list[tuple[str, Optional[PlaceCandidate], Optional[dict]]] = []
        for i, phase in enumerate(PHASES):
            place = places[i] if i < len(places) else None
            if place is None and curated_slots is not None:
                chosen.append((phase, None, curated_slots[i]))
            else:
                chosen.append((phase, place, None))

        # If every phase is empty and there is no curated fallback, degrade honestly.
        if not any(c[1] for c in chosen) and curated_slots is None:
            return _fallback_response(
                request,
                resolutions,
                latency_ms=int((time.perf_counter() - started) * 1000),
                qloo_calls=client.call_count - qloo_calls_before,
            )

        # Drop phases with neither a place nor a curated slot (should not happen
        # when curated exists; when mixed qloo+gaps without curated, skip gap).
        chosen = [c for c in chosen if c[1] is not None or c[2] is not None]
        if not chosen:
            return _fallback_response(
                request,
                resolutions,
                latency_ms=int((time.perf_counter() - started) * 1000),
                qloo_calls=client.call_count - qloo_calls_before,
            )

        narratives, engine_name = await narrative.write(
            request=request,
            resolutions=resolutions,
            places=[c[1] for c in chosen],
            fallback_slots=[c[2] for c in chosen],
        )

        stops: list[ItineraryStop] = []
        for i, (phase, place, fb) in enumerate(chosen):
            if place is not None:
                stops.append(
                    ItineraryStop(
                        phase=phase,
                        venue=place.name,
                        category=place.category,
                        vibe_narrative=narratives[i],
                        entity_id=place.entity_id,
                        address=place.address,
                        tags=place.tags,
                        affinity=place.affinity,
                        influenced_by=place.influenced_by,
                        image_url=place.image_url,
                        source="qloo",
                    )
                )
            else:
                assert fb is not None
                stops.append(
                    ItineraryStop(
                        phase=phase,
                        venue=fb["venue"],
                        category=fb.get("category", ""),
                        vibe_narrative=narratives[i],
                        source="fallback",
                    )
                )

        is_fallback = all(s.source == "fallback" for s in stops)
        return ItineraryResponse(
            city=request.city,
            stops=stops,
            is_fallback=is_fallback,
            anchors_resolved=resolutions,
            meta=ResponseMeta(
                qloo_calls=client.call_count - qloo_calls_before,
                latency_ms=int((time.perf_counter() - started) * 1000),
                narrative_engine=engine_name,  # type: ignore[arg-type]
            ),
        )
    finally:
        if owns_client:
            await client.aclose()
