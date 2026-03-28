"""LLM Adapter Registry — manages available providers.
SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry
"""
from __future__ import annotations

import logging
import os
from typing import Any

from app.llm.adapter import LLMAdapter
from app.llm.slm_batch import SLMBatchInferencer
from app.llm.schema import LLMProviderError

logger = logging.getLogger(__name__)

# Priority order for fallback
_PROVIDER_PRIORITY = ["ollama", "claude", "openai"]


class LLMProviderNotFoundError(LLMProviderError):
    """Raised when a requested provider is not registered.

    SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry
    """


class LLMAdapterRegistry:
    """Manages available LLM providers.

    SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry

    Simulation config specifies default.
    Individual agents can override via agent.llm_provider.
    """

    def __init__(self) -> None:
        self._adapters: dict[str, LLMAdapter] = {}
        self._slm: SLMBatchInferencer | None = None

    def register(self, adapter: LLMAdapter) -> None:
        """Register an LLM adapter by its provider_name.

        SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry
        """
        self._adapters[adapter.provider_name] = adapter

    def register_slm(self, slm: SLMBatchInferencer) -> None:
        """Register the Tier 1 SLM batch inferencer.

        SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry
        """
        self._slm = slm

    def get(self, provider_name: str) -> LLMAdapter:
        """Get adapter by provider name.

        SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry

        Raises LLMProviderNotFoundError if not registered.
        """
        adapter = self._adapters.get(provider_name)
        if adapter is None:
            raise LLMProviderNotFoundError(
                f"Provider '{provider_name}' not registered. "
                f"Available: {list(self._adapters.keys())}"
            )
        return adapter

    def get_default(self) -> LLMAdapter:
        """Returns adapter for DEFAULT_LLM_PROVIDER env var.

        SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry

        Falls back to 'ollama' if env var not set.
        """
        default_name = os.environ.get("DEFAULT_LLM_PROVIDER", "ollama")
        return self.get(default_name)

    async def get_healthy(self) -> LLMAdapter:
        """Returns first healthy provider from priority list [ollama, claude, openai].

        SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry

        Used for fallback when primary is unavailable.
        """
        for name in _PROVIDER_PRIORITY:
            adapter = self._adapters.get(name)
            if adapter is None:
                continue
            try:
                if await adapter.health_check():
                    return adapter
            except Exception:
                logger.warning("Health check failed for provider %s", name)
                continue

        raise LLMProviderNotFoundError(
            "No healthy LLM provider found. "
            f"Checked: {_PROVIDER_PRIORITY}"
        )

    def get_slm(self) -> SLMBatchInferencer:
        """Returns the Tier 1 SLM batch inferencer (always local Ollama).

        SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry
        """
        if self._slm is None:
            raise LLMProviderNotFoundError("SLM batch inferencer not registered")
        return self._slm

    @property
    def providers(self) -> list[str]:
        """List of registered provider names."""
        return list(self._adapters.keys())


__all__ = ["LLMAdapterRegistry", "LLMProviderNotFoundError"]
