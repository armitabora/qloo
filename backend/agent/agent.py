"""Gemini function-calling loop for itinerary refinement."""

from __future__ import annotations

import json
import logging
from typing import Any, Optional

from config import Settings, get_settings
from models import ItineraryResponse, RefineRequest
from agent.tools import TOOL_DECLARATIONS, AgentToolContext
from qloo.client import QlooClient

logger = logging.getLogger("vibe.agent")


class AgentUnavailableError(Exception):
    pass


class AgentStepLimitError(Exception):
    pass


def _tool_config():
    """Build google-genai Tool declarations."""
    from google.genai import types

    functions = []
    for decl in TOOL_DECLARATIONS:
        functions.append(
            types.FunctionDeclaration(
                name=decl["name"],
                description=decl["description"],
                parameters=decl["parameters"],
            )
        )
    return types.Tool(function_declarations=functions)


def _extract_function_calls(response: Any) -> list[tuple[str, dict[str, Any]]]:
    calls: list[tuple[str, dict[str, Any]]] = []
    candidates = getattr(response, "candidates", None) or []
    for cand in candidates:
        content = getattr(cand, "content", None)
        parts = getattr(content, "parts", None) or []
        for part in parts:
            fc = getattr(part, "function_call", None)
            if fc is None:
                continue
            name = getattr(fc, "name", None)
            args = getattr(fc, "args", None) or {}
            if hasattr(args, "items"):
                args = dict(args)
            elif not isinstance(args, dict):
                try:
                    args = json.loads(str(args))
                except Exception:
                    args = {}
            if name:
                calls.append((name, args))
    return calls


def _response_text(response: Any) -> str:
    text = getattr(response, "text", None)
    if text:
        return str(text)
    return ""


async def refine_itinerary(
    request: RefineRequest,
    *,
    client: Optional[QlooClient] = None,
    settings: Optional[Settings] = None,
    gemini_client: Any = None,
) -> ItineraryResponse:
    settings = settings or get_settings()
    if not settings.has_gemini_key and gemini_client is None:
        raise AgentUnavailableError(
            "GEMINI_API_KEY is not configured; /api/refine requires Gemini tool calling."
        )

    owns_client = client is None
    client = client or QlooClient(settings=settings)
    ctx = AgentToolContext(client, request.itinerary)

    try:
        from google import genai
        from google.genai import types

        gclient = gemini_client or genai.Client(api_key=settings.gemini_api_key)
        tool = _tool_config()

        system = (
            "You refine a cultural day itinerary using Qloo-backed tools. "
            "Prefer swap_stop after find_places. Keep exactly 4 phases "
            "(MORNING, AFTERNOON, EVENING, NIGHT). When done, reply with a short "
            "confirmation sentence and do not call more tools."
        )
        user_prompt = (
            f"Instruction: {request.instruction}\n"
            f"City: {request.itinerary.city}\n"
            f"Current itinerary JSON: {request.itinerary.model_dump_json()}\n"
        )

        contents: list[Any] = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=user_prompt)],
            )
        ]

        for step in range(settings.agent_max_steps):
            response = gclient.models.generate_content(
                model=settings.gemini_model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    tools=[tool],
                    temperature=0.4,
                ),
            )
            calls = _extract_function_calls(response)
            if not calls:
                logger.info("Agent finished without tools at step %s: %s", step, _response_text(response)[:200])
                break

            # Append model turn
            model_content = response.candidates[0].content
            contents.append(model_content)

            # Execute tools and append function responses
            fn_response_parts = []
            for name, args in calls:
                logger.info("Agent tool call step=%s name=%s args=%s", step, name, args)
                result_json = await ctx.execute(name, args)
                fn_response_parts.append(
                    types.Part.from_function_response(
                        name=name,
                        response=json.loads(result_json),
                    )
                )
            contents.append(types.Content(role="user", parts=fn_response_parts))
        else:
            # Exhausted steps — still return best-effort itinerary
            logger.warning("Agent hit max steps (%s)", settings.agent_max_steps)

        return ctx.itinerary
    finally:
        if owns_client:
            await client.aclose()
