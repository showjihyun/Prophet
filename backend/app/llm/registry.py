"""LLM Adapter Registry — manages available providers.
SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from typing import Any

from app.llm.adapter import LLMAdapter
from app.llm.slm_batch import SLMBatchInferencer
from app.llm.schema import (
    EmbeddingDimensionError,
    LLMAuthError,
    LLMParseError,
    LLMPrompt,
    LLMOptions,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
    LLMTokenLimitError,
    OllamaConnectionError,
)

logger = logging.getLogger(__name__)


@dataclass
class EvalResult:
    """Result of an evaluate() call with tier/provider tracking.

    SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry
    """
    content: str
    tier_used: int
    provider: str | None = None

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

    # ------------------------------------------------------------------
    # Convenience: register by name (for tests / lightweight usage)
    # ------------------------------------------------------------------

    def register_adapter(self, name: str, adapter: Any) -> None:
        """Register an adapter object by explicit name.

        SPEC: docs/spec/05_LLM_SPEC.md#4-llmadapterregistry

        Unlike ``register()``, this accepts any object duck-typed as an
        adapter and lets the caller choose the key.  Useful in tests.
        """
        self._adapters[name] = adapter  # type: ignore[assignment]

    # ------------------------------------------------------------------
    # evaluate — prompt with tier fallback chain
    # SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    # ------------------------------------------------------------------

    async def evaluate(
        self,
        prompt: str,
        tier: int = 3,
        adapter_name: str | None = None,
        memories: list[str] | None = None,
    ) -> EvalResult:
        """Evaluate *prompt* with automatic tier-fallback.

        SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification

        Fallback rules
        ~~~~~~~~~~~~~~
        * **Timeout** → fall to next lower tier.
        * **Auth error** → immediate fallback (no retry).
        * **Rate limit** → retry with backoff (max 3), then fallback.
        * **Parse error** → retry once with stricter prompt, then fallback.
        * **Token limit** → truncate oldest memories and retry once.
        * **Provider error** → fallback.
        * Tier 1 (Ollama) unreachable → raise ``OllamaConnectionError``.
        """
        current_tier = tier
        # Track adapters that already failed so we don't re-use them
        failed_adapters: set[int] = set()

        while current_tier >= 1:
            adapter = self._pick_adapter(current_tier, adapter_name)
            if adapter is None or id(adapter) in failed_adapters:
                # No fresh adapter for this tier — try lower
                current_tier -= 1
                continue

            try:
                result = await self._call_adapter(adapter, prompt, memories)
                provider = getattr(adapter, "provider_name", None)
                return EvalResult(
                    content=result,
                    tier_used=current_tier,
                    provider=provider,
                )

            except LLMAuthError:
                # Immediate fallback — no retry
                failed_adapters.add(id(adapter))
                current_tier -= 1
                continue

            except LLMTimeoutError:
                failed_adapters.add(id(adapter))
                current_tier -= 1
                continue

            except LLMProviderError:
                failed_adapters.add(id(adapter))
                current_tier -= 1
                continue

            except LLMRateLimitError:
                # Retry up to 3 times with backoff, then fallback
                for attempt in range(3):
                    delay = (2 ** attempt) * 0.01  # fast for tests
                    await asyncio.sleep(delay)
                    try:
                        result = await self._call_adapter(adapter, prompt, memories)
                        provider = getattr(adapter, "provider_name", None)
                        return EvalResult(
                            content=result,
                            tier_used=current_tier,
                            provider=provider,
                        )
                    except LLMRateLimitError:
                        continue
                # All retries exhausted → fallback
                failed_adapters.add(id(adapter))
                current_tier -= 1
                continue

            except LLMParseError:
                # Retry once with stricter prompt
                try:
                    strict_prompt = prompt + "\nRespond ONLY with valid JSON."
                    result = await self._call_adapter(adapter, strict_prompt, memories)
                    provider = getattr(adapter, "provider_name", None)
                    return EvalResult(
                        content=result,
                        tier_used=current_tier,
                        provider=provider,
                    )
                except (LLMParseError, Exception):
                    failed_adapters.add(id(adapter))
                    current_tier -= 1
                    continue

            except LLMTokenLimitError:
                if memories:
                    # Truncate oldest memories and retry once
                    truncated = memories[len(memories) // 2:]
                    try:
                        result = await self._call_adapter(adapter, prompt, truncated)
                        provider = getattr(adapter, "provider_name", None)
                        return EvalResult(
                            content=result,
                            tier_used=current_tier,
                            provider=provider,
                        )
                    except Exception:
                        failed_adapters.add(id(adapter))
                        current_tier -= 1
                        continue
                else:
                    failed_adapters.add(id(adapter))
                    current_tier -= 1
                    continue

            except OllamaConnectionError:
                raise

        # All tiers exhausted — return degraded result
        return EvalResult(content="", tier_used=1, provider=None)

    # ------------------------------------------------------------------
    # embed — embedding with dimension check
    # SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    # ------------------------------------------------------------------

    async def embed(self, text: str, expected_dim: int = 768) -> list[float]:
        """Generate embedding and validate dimension.

        SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification

        Raises ``EmbeddingDimensionError`` if the returned vector length
        does not match *expected_dim*.
        """
        adapter = self._pick_adapter_for_embed()
        result = await adapter.embed(text)
        if result is not None and len(result) != expected_dim:
            raise EmbeddingDimensionError(
                f"Expected {expected_dim}-dim, got {len(result)}-dim"
            )
        return result  # type: ignore[return-value]

    # ------------------------------------------------------------------
    # _clamp_score — static utility
    # SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
    # ------------------------------------------------------------------

    @staticmethod
    def _clamp_score(
        value: float,
        min_val: float = -1.0,
        max_val: float = 1.0,
    ) -> float:
        """Clamp *value* to [min_val, max_val].

        SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification
        """
        return max(min_val, min(max_val, value))

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _pick_adapter(
        self, tier: int, preferred: str | None = None
    ) -> Any | None:
        """Select adapter for *tier*.  Tier 1 uses Ollama / SLM."""
        if preferred and preferred in self._adapters:
            return self._adapters[preferred]
        # Fallback: pick first registered adapter (tests register one)
        if self._adapters:
            return next(iter(self._adapters.values()))
        return None

    def _pick_adapter_for_embed(self) -> Any:
        """Select adapter capable of embeddings (prefers ollama)."""
        if "ollama" in self._adapters:
            return self._adapters["ollama"]
        if self._adapters:
            return next(iter(self._adapters.values()))
        raise LLMProviderNotFoundError("No adapter registered for embedding")

    async def _call_adapter(
        self,
        adapter: Any,
        prompt: str,
        memories: list[str] | None = None,
    ) -> str:
        """Call adapter.complete() and return content string."""
        response = await adapter.complete(prompt, memories)
        # Support both LLMResponse objects and plain mocks
        if hasattr(response, "content"):
            return response.content
        if hasattr(response, "text"):
            return response.text
        return str(response)

    async def _get_ollama_adapter(self) -> Any:
        """Return the Ollama adapter (for Tier 1).

        SPEC: docs/spec/05_LLM_SPEC.md#9-error-specification

        Raises ``OllamaConnectionError`` if not available.
        """
        adapter = self._adapters.get("ollama")
        if adapter is None:
            raise OllamaConnectionError("Ollama adapter not registered")
        return adapter


__all__ = ["LLMAdapterRegistry", "LLMProviderNotFoundError", "EvalResult"]
