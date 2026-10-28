"""Async Qloo HTTP client with retries, TTL cache, and typed errors."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Optional
from urllib.parse import urlencode

import httpx

from config import Settings, get_settings

logger = logging.getLogger("vibe.qloo")


class QlooError(Exception):
    """Base error for Qloo API failures."""

    def __init__(self, message: str, status_code: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class QlooAuthError(QlooError):
    """401 / missing or invalid API key."""


class QlooForbiddenError(QlooError):
    """403 — unsupported entity type or permission denied."""


class QlooRateLimitError(QlooError):
    """429 — rate limited."""


class QlooNotFoundError(QlooError):
    """404 — no results / missing resource."""


class _CacheEntry:
    __slots__ = ("expires_at", "value")

    def __init__(self, value: Any, ttl: float):
        self.value = value
        self.expires_at = time.monotonic() + ttl


# Shared across request-scoped clients so search/insights hits survive
# generate-itinerary round trips within the TTL window.
_PROCESS_CACHE: dict[str, _CacheEntry] = {}


class QlooClient:
    """Thin async wrapper around the hackathon Qloo API."""

    def __init__(
        self,
        settings: Optional[Settings] = None,
        client: Optional[httpx.AsyncClient] = None,
    ):
        self.settings = settings or get_settings()
        self._client = client
        self._owns_client = client is None
        self.call_count = 0

    @property
    def base_url(self) -> str:
        return self.settings.qloo_base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        key = self.settings.qloo_api_key.strip()
        if not key:
            raise QlooAuthError("QLOO_API_KEY is not configured.")
        return {"X-Api-Key": key, "Accept": "application/json"}

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            read = self.settings.qloo_timeout_seconds
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(connect=3.0, read=read, write=read, pool=3.0),
            )
            self._owns_client = True
        return self._client

    async def aclose(self) -> None:
        if self._owns_client and self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "QlooClient":
        await self._ensure_client()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    @staticmethod
    def _cache_key(method: str, path: str, params: dict[str, Any]) -> str:
        # Sort params for stable keys; drop None values.
        cleaned = {k: v for k, v in sorted(params.items()) if v is not None}
        raw = f"{method}:{path}?{urlencode(cleaned, doseq=True)}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _cache_get(self, key: str) -> Any | None:
        entry = _PROCESS_CACHE.get(key)
        if entry is None:
            return None
        if entry.expires_at < time.monotonic():
            _PROCESS_CACHE.pop(key, None)
            return None
        return entry.value

    def _cache_set(self, key: str, value: Any) -> None:
        ttl = self.settings.qloo_cache_ttl_seconds
        if ttl <= 0:
            return
        _PROCESS_CACHE[key] = _CacheEntry(value, ttl)

    def clear_cache(self) -> None:
        _PROCESS_CACHE.clear()

    @classmethod
    def clear_process_cache(cls) -> None:
        """Test helper: drop shared cache between cases."""
        _PROCESS_CACHE.clear()

    async def get(
        self,
        path: str,
        params: Optional[dict[str, Any]] = None,
        *,
        use_cache: bool = True,
    ) -> Any:
        params = dict(params or {})
        # Flatten list/tuple values into comma-separated strings (Qloo query style).
        flat: dict[str, Any] = {}
        for k, v in params.items():
            if v is None or v == "" or v == []:
                continue
            if isinstance(v, (list, tuple)):
                flat[k] = ",".join(str(x) for x in v if x is not None and x != "")
            elif isinstance(v, bool):
                flat[k] = "true" if v else "false"
            else:
                flat[k] = v

        cache_key = self._cache_key("GET", path, flat) if use_cache else None
        if cache_key:
            cached = self._cache_get(cache_key)
            if cached is not None:
                logger.debug("qloo cache hit path=%s", path)
                return cached

        client = await self._ensure_client()
        retries = max(0, self.settings.qloo_max_retries)
        last_error: Exception | None = None

        for attempt in range(retries + 1):
            self.call_count += 1
            try:
                logger.info(
                    "qloo GET %s params=%s attempt=%s",
                    path,
                    _redact_params(flat),
                    attempt + 1,
                )
                response = await client.get(
                    path,
                    params=flat,
                    headers=self._headers(),
                )
            except httpx.TimeoutException as exc:
                last_error = QlooError(f"Qloo timeout on {path}: {exc}")
                if attempt < retries:
                    await asyncio.sleep(0.4 * (2**attempt))
                    continue
                raise last_error from exc
            except httpx.HTTPError as exc:
                last_error = QlooError(f"Qloo network error on {path}: {exc}")
                if attempt < retries:
                    await asyncio.sleep(0.4 * (2**attempt))
                    continue
                raise last_error from exc

            if response.status_code == 429 or response.status_code >= 500:
                last_error = self._map_error(response)
                if attempt < retries:
                    retry_after = response.headers.get("Retry-After")
                    delay = float(retry_after) if retry_after and retry_after.isdigit() else 0.5 * (2**attempt)
                    await asyncio.sleep(delay)
                    continue
                raise last_error

            if response.status_code >= 400:
                raise self._map_error(response)

            # 404 with empty body is treated as no results by callers of search.
            try:
                data = response.json()
            except json.JSONDecodeError as exc:
                raise QlooError(
                    f"Qloo returned non-JSON on {path}",
                    status_code=response.status_code,
                    body=response.text[:500],
                ) from exc

            if cache_key:
                self._cache_set(cache_key, data)
            return data

        raise last_error or QlooError(f"Qloo request failed: {path}")

    def _map_error(self, response: httpx.Response) -> QlooError:
        try:
            body: Any = response.json()
        except Exception:
            body = response.text[:500]

        message = f"Qloo HTTP {response.status_code}"
        if isinstance(body, dict):
            message = str(
                body.get("error")
                or body.get("message")
                or body.get("detail")
                or message
            )

        if response.status_code in (401,):
            return QlooAuthError(message, status_code=401, body=body)
        if response.status_code == 403:
            return QlooForbiddenError(message, status_code=403, body=body)
        if response.status_code == 404:
            return QlooNotFoundError(message, status_code=404, body=body)
        if response.status_code == 429:
            return QlooRateLimitError(message, status_code=429, body=body)
        return QlooError(message, status_code=response.status_code, body=body)

    # --- Convenience endpoints -------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        types: Optional[str | list[str]] = None,
        take: int = 6,
    ) -> list[dict[str, Any]]:
        """GET /search — resolve free-text names to entity records."""
        params: dict[str, Any] = {"query": query, "take": take}
        if types:
            params["types"] = types
        try:
            data = await self.get("/search", params)
        except QlooNotFoundError:
            return []

        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            results = data.get("results") or data.get("entities") or []
            if isinstance(results, dict):
                # Some payloads nest entities under results.entities
                results = results.get("entities") or results.get("results") or []
            return [x for x in results if isinstance(x, dict)]
        return []

    async def tags(
        self,
        query: str,
        *,
        take: int = 10,
        tag_types: Optional[str | list[str]] = None,
    ) -> list[dict[str, Any]]:
        """GET /v2/tags — resolve free-text to tag IDs."""
        params: dict[str, Any] = {"filter.query": query, "take": take}
        if tag_types:
            params["filter.tag.types"] = tag_types
        try:
            data = await self.get("/v2/tags", params)
        except QlooNotFoundError:
            return []

        if isinstance(data, dict):
            results = data.get("results") or {}
            if isinstance(results, dict):
                tags = results.get("tags") or []
            elif isinstance(results, list):
                tags = results
            else:
                tags = data.get("tags") or []
            return [t for t in tags if isinstance(t, dict)]
        if isinstance(data, list):
            return [t for t in data if isinstance(t, dict)]
        return []

    async def insights(self, params: dict[str, Any]) -> dict[str, Any]:
        """GET /v2/insights — recommendations / taste analysis."""
        data = await self.get("/v2/insights", params, use_cache=True)
        if isinstance(data, dict):
            return data
        return {"results": data}


def _redact_params(params: dict[str, Any]) -> dict[str, Any]:
    """Log-safe params (truncate long ID lists)."""
    out: dict[str, Any] = {}
    for k, v in params.items():
        s = str(v)
        if len(s) > 120:
            out[k] = s[:117] + "..."
        else:
            out[k] = v
    return out
