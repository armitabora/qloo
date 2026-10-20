"""Qloo-backed tools exposed to the Gemini agent."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from config import PHASES
from models import AnchorResolution, ItineraryResponse, ItineraryStop
from qloo.categories import CategoryResolver
from qloo.client import QlooClient
from qloo.places import PlaceFinder
from qloo.resolver import AnchorResolver

logger = logging.getLogger("vibe.agent.tools")

TOOL_DECLARATIONS: list[dict[str, Any]] = [
    {
        "name": "resolve_anchor",
        "description": "Resolve a free-text cultural anchor (music, film, or vibe) to a Qloo entity or tag ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "kind": {
                    "type": "string",
                    "enum": ["music", "film", "vibe"],
                    "description": "Anchor kind",
                },
                "text": {"type": "string", "description": "Free-text anchor"},
            },
            "required": ["kind", "text"],
        },
    },
    {
        "name": "find_places",
        "description": "Find place recommendations in a city for a day phase using taste signals.",
        "parameters": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "enum": ["Tokyo", "New York"]},
                "phase": {
                    "type": "string",
                    "enum": ["MORNING", "AFTERNOON", "EVENING", "NIGHT"],
                },
                "entity_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Qloo entity IDs for signal.interests.entities",
                },
                "tag_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Qloo tag IDs for signal.interests.tags",
                },
                "exclude_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                },
                "take": {"type": "integer"},
            },
            "required": ["city", "phase"],
        },
    },
    {
        "name": "place_details",
        "description": "Return details for a stop already on the itinerary by phase.",
        "parameters": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "enum": ["MORNING", "AFTERNOON", "EVENING", "NIGHT"],
                }
            },
            "required": ["phase"],
        },
    },
    {
        "name": "swap_stop",
        "description": "Replace one itinerary phase with a new venue from find_places results.",
        "parameters": {
            "type": "object",
            "properties": {
                "phase": {
                    "type": "string",
                    "enum": ["MORNING", "AFTERNOON", "EVENING", "NIGHT"],
                },
                "entity_id": {"type": "string"},
                "venue": {"type": "string"},
                "category": {"type": "string"},
                "vibe_narrative": {"type": "string"},
                "address": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "affinity": {"type": "number"},
            },
            "required": ["phase", "venue", "vibe_narrative"],
        },
    },
]


class AgentToolContext:
    def __init__(
        self,
        client: QlooClient,
        itinerary: ItineraryResponse,
        resolutions: Optional[list[AnchorResolution]] = None,
    ):
        self.client = client
        self.itinerary = itinerary.model_copy(deep=True)
        self.resolutions = resolutions or list(itinerary.anchors_resolved)
        self.categories = CategoryResolver(client)
        self.finder = PlaceFinder(client, self.categories)
        self.resolver = AnchorResolver(client)

    async def execute(self, name: str, args: dict[str, Any]) -> str:
        handler = {
            "resolve_anchor": self._resolve_anchor,
            "find_places": self._find_places,
            "place_details": self._place_details,
            "swap_stop": self._swap_stop,
        }.get(name)
        if not handler:
            return json.dumps({"error": f"Unknown tool: {name}"})
        try:
            result = await handler(args)
            return json.dumps(result)
        except Exception as exc:
            logger.exception("tool %s failed", name)
            return json.dumps({"error": str(exc)})

    async def _resolve_anchor(self, args: dict[str, Any]) -> dict[str, Any]:
        kind = args["kind"]
        text = args["text"]
        if kind == "music":
            res = await self.resolver.resolve_music(text)
        elif kind == "film":
            res = await self.resolver.resolve_film(text)
        else:
            res = await self.resolver.resolve_vibe(text)
        # Upsert into resolutions
        self.resolutions = [r for r in self.resolutions if not (r.kind == kind and r.input == text)]
        self.resolutions.append(res)
        return res.model_dump()

    async def _find_places(self, args: dict[str, Any]) -> dict[str, Any]:
        city = args["city"]
        phase = args["phase"].upper()
        entity_ids = args.get("entity_ids") or AnchorResolver.signal_entity_ids(self.resolutions)
        tag_ids = args.get("tag_ids") or AnchorResolver.signal_tag_ids(self.resolutions)
        # Build temporary resolutions if IDs provided directly.
        resolutions = list(self.resolutions)
        if args.get("entity_ids") and not resolutions:
            resolutions = [
                AnchorResolution(
                    input=eid,
                    kind="music",
                    resolved=True,
                    matched_name=eid,
                    entity_id=eid,
                )
                for eid in entity_ids
            ]
        if not entity_ids and not tag_ids and not resolutions:
            return {"places": [], "error": "No taste signals available"}

        # Inject synthetic resolutions for explicit IDs.
        if entity_ids:
            for eid in entity_ids:
                if not any(r.entity_id == eid for r in resolutions):
                    resolutions.append(
                        AnchorResolution(
                            input=eid,
                            kind="music",
                            resolved=True,
                            matched_name=eid,
                            entity_id=eid,
                        )
                    )

        places = await self.finder.find_for_phase(
            city=city,
            phase=phase,
            resolutions=resolutions,
            exclude_ids=args.get("exclude_ids") or [
                s.entity_id for s in self.itinerary.stops if s.entity_id
            ],
            take=int(args.get("take") or 5),
        )
        return {
            "places": [
                {
                    "entity_id": p.entity_id,
                    "venue": p.name,
                    "category": p.category,
                    "address": p.address,
                    "tags": p.tags,
                    "affinity": p.affinity,
                    "influenced_by": [i.model_dump() for i in p.influenced_by],
                }
                for p in places[:5]
            ]
        }

    async def _place_details(self, args: dict[str, Any]) -> dict[str, Any]:
        phase = args["phase"].upper()
        for stop in self.itinerary.stops:
            if stop.phase.upper() == phase:
                return stop.model_dump()
        return {"error": f"No stop for phase {phase}"}

    async def _swap_stop(self, args: dict[str, Any]) -> dict[str, Any]:
        phase = args["phase"].upper()
        if phase not in PHASES:
            return {"error": f"Invalid phase {phase}"}
        new_stop = ItineraryStop(
            phase=phase,
            venue=args["venue"],
            vibe_narrative=args["vibe_narrative"],
            category=args.get("category") or "",
            entity_id=args.get("entity_id"),
            address=args.get("address"),
            tags=list(args.get("tags") or []),
            affinity=args.get("affinity"),
            source="qloo",
        )
        stops = []
        replaced = False
        for stop in self.itinerary.stops:
            if stop.phase.upper() == phase:
                stops.append(new_stop)
                replaced = True
            else:
                stops.append(stop)
        if not replaced:
            stops.append(new_stop)
        # Keep phase order
        by_phase = {s.phase.upper(): s for s in stops}
        ordered = [by_phase[p] for p in PHASES if p in by_phase]
        self.itinerary = self.itinerary.model_copy(
            update={
                "stops": ordered,
                "anchors_resolved": self.resolutions,
                "is_fallback": False,
            }
        )
        return {"ok": True, "stop": new_stop.model_dump()}
