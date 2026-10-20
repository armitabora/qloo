"""Pick Gemini or template narratives."""

from __future__ import annotations

import logging
from typing import Literal, Optional

from config import Settings, get_settings
from models import AnchorResolution, ItineraryRequest
from narrative import gemini as gemini_mod
from narrative import template as template_mod
from qloo.places import PlaceCandidate

logger = logging.getLogger("vibe.narrative")

EngineName = Literal["gemini", "template"]


class NarrativeEngine:
    def __init__(self, settings: Optional[Settings] = None, gemini_client=None):
        self.settings = settings or get_settings()
        self.gemini_client = gemini_client

    async def write(
        self,
        *,
        request: ItineraryRequest,
        resolutions: list[AnchorResolution],
        places: list[Optional[PlaceCandidate]],
        fallback_slots: list[Optional[dict]],
    ) -> tuple[list[str], EngineName]:
        if self.settings.has_gemini_key or self.gemini_client is not None:
            try:
                narratives = await gemini_mod.generate_with_gemini(
                    request=request,
                    resolutions=resolutions,
                    places=places,
                    fallback_slots=fallback_slots,
                    settings=self.settings,
                    client=self.gemini_client,
                )
                return narratives, "gemini"
            except gemini_mod.GeminiNarrativeError as exc:
                logger.warning("Gemini narrative failed, using template: %s", exc)

        narratives = template_mod.build_narratives(
            request=request,
            resolutions=resolutions,
            places=places,
            fallback_slots=fallback_slots,
        )
        return narratives, "template"
