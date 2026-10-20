"""Shared pytest fixtures."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import Settings, clear_settings_cache  # noqa: E402
from qloo.client import QlooClient  # noqa: E402


@pytest.fixture
def settings() -> Settings:
    clear_settings_cache()
    return Settings(
        qloo_api_key="test-qloo-key",
        qloo_base_url="https://hackathon.api.qloo.com",
        gemini_api_key="",
        gemini_model="gemini-2.0-flash",
        allowed_origins=("http://localhost:5173",),
        qloo_timeout_seconds=2.0,
        qloo_max_retries=2,
        qloo_cache_ttl_seconds=60.0,
        agent_max_steps=4,
    )


@pytest.fixture
def qloo_client(settings: Settings) -> QlooClient:
    return QlooClient(settings=settings)


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch: pytest.MonkeyPatch):
    """Avoid leaking developer .env into unit tests."""
    monkeypatch.setenv("QLOO_API_KEY", "test-qloo-key")
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    clear_settings_cache()
    yield
    clear_settings_cache()
