"""Agent refine endpoint / tool-loop tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from agent.agent import AgentUnavailableError, refine_itinerary
from agent.tools import AgentToolContext
from config import Settings, clear_settings_cache
from models import ItineraryResponse, ItineraryStop, RefineRequest
from qloo.client import QlooClient
from tests.fixtures.synthetic import insights_places, place_entity, search_artist

BASE = "https://hackathon.api.qloo.com"


def _sample_itinerary() -> ItineraryResponse:
    return ItineraryResponse(
        city="Tokyo",
        stops=[
            ItineraryStop(phase="MORNING", venue="Cafe A", vibe_narrative="a", entity_id="a", source="qloo"),
            ItineraryStop(phase="AFTERNOON", venue="Shop B", vibe_narrative="b", entity_id="b", source="qloo"),
            ItineraryStop(phase="EVENING", venue="Ramen C", vibe_narrative="c", entity_id="c", source="qloo"),
            ItineraryStop(phase="NIGHT", venue="Bar D", vibe_narrative="d", entity_id="d", source="qloo"),
        ],
    )


@pytest.mark.asyncio
@respx.mock
async def test_swap_stop_tool():
    settings = Settings(qloo_api_key="test", qloo_base_url=BASE)
    async with QlooClient(settings=settings) as client:
        ctx = AgentToolContext(client, _sample_itinerary())
        result = json.loads(
            await ctx.execute(
                "swap_stop",
                {
                    "phase": "NIGHT",
                    "venue": "Quiet Jazz Den",
                    "vibe_narrative": "A quieter night for your lo-fi taste.",
                    "entity_id": "p-quiet",
                    "category": "Jazz Club",
                },
            )
        )
    assert result["ok"] is True
    night = next(s for s in ctx.itinerary.stops if s.phase == "NIGHT")
    assert night.venue == "Quiet Jazz Den"


@pytest.mark.asyncio
async def test_refine_without_gemini_raises():
    settings = Settings(qloo_api_key="test", gemini_api_key="", qloo_base_url=BASE)
    with pytest.raises(AgentUnavailableError):
        await refine_itinerary(
            RefineRequest(instruction="make night quieter", itinerary=_sample_itinerary()),
            settings=settings,
            client=QlooClient(settings=settings),
        )


class _FakeFC:
    def __init__(self, name: str, args: dict[str, Any]):
        self.name = name
        self.args = args


class _FakePart:
    def __init__(self, function_call=None, text=None):
        self.function_call = function_call
        self.text = text


class _FakeContent:
    def __init__(self, parts):
        self.parts = parts
        self.role = "model"


class _FakeCandidate:
    def __init__(self, content):
        self.content = content


class _FakeResponse:
    def __init__(self, parts, text=""):
        self.candidates = [_FakeCandidate(_FakeContent(parts))]
        self.text = text


@pytest.mark.asyncio
@respx.mock
async def test_mocked_tool_loop_swaps_night(monkeypatch):
    settings = Settings(
        qloo_api_key="test",
        gemini_api_key="fake",
        gemini_model="gemini-2.0-flash",
        qloo_base_url=BASE,
        agent_max_steps=4,
        qloo_cache_ttl_seconds=0,
    )

    respx.get(f"{BASE}/search").mock(
        return_value=httpx.Response(200, json=search_artist())
    )
    respx.get(f"{BASE}/v2/tags").mock(
        return_value=httpx.Response(
            200, json={"results": {"tags": [{"id": "urn:tag:genre:place:bar", "name": "Bar"}]}}
        )
    )
    respx.get(f"{BASE}/v2/insights").mock(
        return_value=httpx.Response(
            200,
            json=insights_places(
                [place_entity(entity_id="p-quiet", name="Quiet Jazz Den", tag="Jazz Club")]
            ),
        )
    )

    # Patch google genai pieces used inside refine_itinerary / _tool_config
    calls_made = {"n": 0}

    class FakeModels:
        def generate_content(self, **kwargs):
            calls_made["n"] += 1
            if calls_made["n"] == 1:
                return _FakeResponse(
                    [
                        _FakePart(
                            function_call=_FakeFC(
                                "find_places",
                                {"city": "Tokyo", "phase": "NIGHT", "take": 3},
                            )
                        )
                    ]
                )
            if calls_made["n"] == 2:
                return _FakeResponse(
                    [
                        _FakePart(
                            function_call=_FakeFC(
                                "swap_stop",
                                {
                                    "phase": "NIGHT",
                                    "entity_id": "p-quiet",
                                    "venue": "Quiet Jazz Den",
                                    "category": "Jazz Club",
                                    "vibe_narrative": "A quieter close that still fits Nujabes.",
                                },
                            )
                        )
                    ]
                )
            return _FakeResponse([_FakePart(text="Done.")], text="Done.")

    class FakeClient:
        models = FakeModels()

    # Stub types used when building tool config
    import agent.agent as agent_mod

    class FakeFunctionDeclaration:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeTool:
        def __init__(self, function_declarations=None):
            self.function_declarations = function_declarations

    class FakePart:
        @staticmethod
        def from_text(text=""):
            return SimpleNamespace(text=text)

        @staticmethod
        def from_function_response(name="", response=None):
            return SimpleNamespace(name=name, response=response)

    class FakeContent:
        def __init__(self, role=None, parts=None):
            self.role = role
            self.parts = parts

    class FakeGenerateContentConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    fake_types = SimpleNamespace(
        FunctionDeclaration=FakeFunctionDeclaration,
        Tool=FakeTool,
        Part=FakePart,
        Content=FakeContent,
        GenerateContentConfig=FakeGenerateContentConfig,
    )
    fake_genai = SimpleNamespace(Client=lambda api_key=None: FakeClient())

    monkeypatch.setitem(__import__("sys").modules, "google.genai", SimpleNamespace(types=fake_types))
    monkeypatch.setitem(__import__("sys").modules, "google", SimpleNamespace(genai=fake_genai))
    # Also patch local imports inside function by injecting attributes
    monkeypatch.setattr(agent_mod, "_tool_config", lambda: FakeTool())

    async with QlooClient(settings=settings) as client:
        result = await refine_itinerary(
            RefineRequest(
                instruction="make the night stop quieter",
                itinerary=_sample_itinerary(),
            ),
            client=client,
            settings=settings,
            gemini_client=FakeClient(),
        )

    night = next(s for s in result.stops if s.phase == "NIGHT")
    assert night.venue == "Quiet Jazz Den"
    assert calls_made["n"] >= 2


def test_api_refine_503_without_gemini(monkeypatch):
    monkeypatch.setenv("QLOO_API_KEY", "test")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    clear_settings_cache()
    # Import app after env tweak
    import importlib
    import main as main_mod

    importlib.reload(main_mod)
    client = TestClient(main_mod.app)
    resp = client.post(
        "/api/refine",
        json={
            "instruction": "make night quieter",
            "itinerary": _sample_itinerary().model_dump(),
        },
    )
    assert resp.status_code == 503
    clear_settings_cache()


def test_health_endpoint(monkeypatch):
    monkeypatch.setenv("QLOO_API_KEY", "test")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    clear_settings_cache()
    import importlib
    import main as main_mod

    importlib.reload(main_mod)
    client = TestClient(main_mod.app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["qloo_configured"] is True
    assert body["gemini_configured"] is False
    clear_settings_cache()
