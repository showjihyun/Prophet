"""LLM Response Cache (in-memory for Phase 5, Valkey in Phase 6).
SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
"""
from __future__ import annotations

import hashlib
import json
import time
from typing import Any
from uuid import UUID

from app.llm.schema import LLMPrompt, LLMResponse


class LLMResponseCache:
    """Caches LLM responses to reduce cost in Monte Carlo runs and repeated scenarios.

    SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey

    Phase 5: in-memory dict implementation.
    Phase 6: will migrate to Valkey.
    """

    def __init__(self) -> None:
        """SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey"""
        self._store: dict[str, tuple[LLMResponse, float]] = {}  # key -> (response, expires_at)
        # Track simulation-specific keys for invalidation
        self._simulation_keys: dict[str, set[str]] = {}  # simulation_id -> {keys}

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

        SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
        """
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

        SPEC: docs/spec/05_LLM_SPEC.md#6-llm-response-cache-valkey
        """
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
        keys = self._simulation_keys.pop(sid, set())
        for key in keys:
            self._store.pop(key, None)


__all__ = ["LLMResponseCache"]
