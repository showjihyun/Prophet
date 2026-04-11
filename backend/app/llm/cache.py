"""LLM Response Cache — Valkey-backed with in-memory fallback.
SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import logging
import time
from typing import Any
from uuid import UUID

from app.llm.schema import LLMPrompt, LLMResponse

logger = logging.getLogger(__name__)


class ValkeyCacheBackend:
    """Async Valkey (Redis-compatible) cache backend.

    SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
    """

    def __init__(self, url: str, ttl: int = 3600) -> None:
        """Connect to Valkey at *url* with a default TTL of *ttl* seconds."""
        import valkey.asyncio as valkey_asyncio

        self._client = valkey_asyncio.from_url(url, decode_responses=True)
        self._default_ttl = ttl

    async def get(self, key: str) -> str | None:
        """Return the cached string value, or None on miss/error."""
        try:
            return await self._client.get(key)
        except Exception as exc:
            logger.warning("Valkey GET failed: %s", exc)
            return None

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        """Store *value* under *key* with an optional TTL (seconds)."""
        effective_ttl = ttl if ttl is not None else self._default_ttl
        try:
            await self._client.setex(key, effective_ttl, value)
        except Exception as exc:
            logger.warning("Valkey SET failed: %s", exc)

    async def delete(self, key: str) -> None:
        """Delete a single key, ignoring errors."""
        try:
            await self._client.delete(key)
        except Exception as exc:
            logger.warning("Valkey DELETE failed: %s", exc)

    async def ping(self) -> bool:
        """Return True if the Valkey server is reachable."""
        try:
            await self._client.ping()
            return True
        except Exception:
            return False

    async def aclose(self) -> None:
        """Close the underlying connection pool."""
        try:
            await self._client.aclose()
        except Exception:
            pass


class LLMResponseCache:
    """Caches LLM responses to reduce cost in repeated scenarios.

    Uses Valkey when available; falls back transparently to an in-memory dict
    when the Valkey server is unreachable.

    SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
    """

    # Re-probe Valkey every 5 minutes after initial failure
    _REPROBE_INTERVAL_SECONDS: float = 300.0

    def __init__(self) -> None:
        """Initialise cache, connecting to Valkey lazily on first use.

        SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
        """
        # In-memory fallback store: key -> (LLMResponse, expires_at)
        self._store: dict[str, tuple[LLMResponse, float]] = {}
        # Track simulation-specific keys for invalidation (in-memory only)
        self._simulation_keys: dict[str, set[str]] = {}

        # Valkey backend — initialised lazily in _backend()
        self._valkey: ValkeyCacheBackend | None = None
        self._valkey_ok: bool | None = None  # None = not yet probed
        self._last_probe_time: float = 0.0

        # Observability counters
        self._valkey_failures: int = 0
        self._fallback_gets: int = 0
        self._fallback_sets: int = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _backend(self) -> ValkeyCacheBackend | None:
        """Return a live ValkeyCacheBackend, or None if unavailable.

        Re-probes periodically after failure to allow recovery.
        """
        now = time.time()

        # Re-probe after failure if enough time has passed
        if self._valkey_ok is False:
            if now - self._last_probe_time < self._REPROBE_INTERVAL_SECONDS:
                return None  # still in cooldown
            logger.info("LLMResponseCache: re-probing Valkey after cooldown")
            self._valkey_ok = None  # trigger fresh probe

        if self._valkey is None:
            try:
                from app.config import settings
                self._valkey = ValkeyCacheBackend(
                    url=settings.valkey_url,
                    ttl=settings.llm_cache_ttl,
                )
            except Exception as exc:
                logger.warning("Could not create Valkey backend: %s", exc)
                self._valkey_ok = False
                self._last_probe_time = now
                self._valkey_failures += 1
                return None

        if self._valkey_ok is None:
            # Probe reachability
            self._last_probe_time = now
            self._valkey_ok = await self._valkey.ping()
            if self._valkey_ok:
                logger.info("LLMResponseCache: Valkey backend connected")
            else:
                self._valkey_failures += 1
                logger.warning(
                    "LLMResponseCache: Valkey unreachable (failure #%d) "
                    "— using in-memory fallback. Will re-probe in %ds.",
                    self._valkey_failures,
                    int(self._REPROBE_INTERVAL_SECONDS),
                )

        return self._valkey if self._valkey_ok else None

    @staticmethod
    def _serialize(response: LLMResponse) -> str:
        """Serialise a dataclass LLMResponse to a JSON string."""
        return json.dumps(dataclasses.asdict(response))

    @staticmethod
    def _deserialize(raw: str) -> LLMResponse:
        """Deserialise a JSON string back to an LLMResponse dataclass."""
        return LLMResponse(**json.loads(raw))

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def cache_key(
        self,
        prompt: LLMPrompt,
        provider: str,
        model: str,
    ) -> str:
        """SHA256 hash of (provider + model + system + user content).

        SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
        """
        raw = f"{provider}:{model}:{prompt.system}:{prompt.user}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def get(self, key: str) -> LLMResponse | None:
        """Retrieve cached response, returning None if expired or missing.

        Tries Valkey first; falls back to in-memory store.

        SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
        """
        backend = await self._backend()

        if backend is not None:
            raw = await backend.get(key)
            if raw is not None:
                try:
                    return self._deserialize(raw)
                except Exception as exc:
                    logger.warning("Valkey deserialise error for key %s: %s", key, exc)

        # In-memory fallback
        self._fallback_gets += 1
        entry = self._store.get(key)
        if entry is None:
            return None
        response, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return response

    async def set(
        self,
        key: str,
        response: LLMResponse,
        ttl: int = 3600,
        simulation_id: str | None = None,
    ) -> None:
        """Cache a response with TTL.

        Writes to Valkey when available; always writes to in-memory store so
        that the fallback path stays warm.

        SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
        """
        backend = await self._backend()

        if backend is not None:
            await backend.set(key, self._serialize(response), ttl=ttl)
            # Also track in simulation_keys for invalidation
            if simulation_id:
                sim_key = f"sim_keys:{simulation_id}"
                await backend.set(f"{sim_key}:{key}", "1", ttl=ttl)

        # Always write in-memory fallback
        expires_at = time.time() + ttl
        self._store[key] = (response, expires_at)
        if simulation_id:
            if simulation_id not in self._simulation_keys:
                self._simulation_keys[simulation_id] = set()
            self._simulation_keys[simulation_id].add(key)

    async def invalidate_simulation(self, simulation_id: UUID) -> None:
        """Clear all cache entries for a simulation.

        SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
        """
        sid = str(simulation_id)

        backend = await self._backend()
        if backend is not None:
            # Delete known keys from Valkey
            for key in list(self._simulation_keys.get(sid, [])):
                await backend.delete(key)

        # Always clear in-memory
        keys = self._simulation_keys.pop(sid, set())
        for key in keys:
            self._store.pop(key, None)


    def health_status(self) -> dict[str, Any]:
        """Return cache health status for observability.

        SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
        """
        return {
            "valkey_connected": self._valkey_ok is True,
            "valkey_failures": self._valkey_failures,
            "fallback_gets": self._fallback_gets,
            "fallback_sets": self._fallback_sets,
            "inmemory_entries": len(self._store),
        }


__all__ = ["LLMResponseCache", "ValkeyCacheBackend"]
