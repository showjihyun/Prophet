"""Quota & Rate Management for LLM calls.
SPEC: docs/spec/05_LLM_SPEC.md#7-quota--rate-management
"""
from __future__ import annotations

import asyncio
import logging
import time
from uuid import UUID

logger = logging.getLogger(__name__)

# Default max ratio of agents that can use Tier 3 LLM per step
_DEFAULT_TIER3_RATIO = 0.10


class LLMQuotaManager:
    """Enforces per-step LLM budget and handles rate limiting.

    SPEC: docs/spec/05_LLM_SPEC.md#7-quota--rate-management
    """

    def __init__(self, tier3_ratio: float = _DEFAULT_TIER3_RATIO) -> None:
        """SPEC: docs/spec/05_LLM_SPEC.md#7-quota--rate-management"""
        self._tier3_ratio = tier3_ratio
        # provider -> (disabled_until timestamp)
        self._disabled_providers: dict[str, float] = {}

    def can_call_llm(
        self,
        simulation_id: UUID,
        step: int,
        current_llm_call_count: int,
        total_agents: int,
    ) -> bool:
        """Returns False if current_llm_call_count / total_agents > LLM_TIER3_RATIO.

        SPEC: docs/spec/05_LLM_SPEC.md#7-quota--rate-management

        Enforces per-step LLM budget.
        """
        if total_agents <= 0:
            return False
        ratio = current_llm_call_count / total_agents
        allowed = ratio < self._tier3_ratio
        if not allowed:
            logger.info(
                "Quota exceeded for simulation %s step %d: %d/%d (%.1f%% >= %.1f%%)",
                simulation_id, step, current_llm_call_count, total_agents,
                ratio * 100, self._tier3_ratio * 100,
            )
        return allowed

    async def handle_rate_limit(
        self,
        provider: str,
        retry_after: float,
    ) -> None:
        """Log rate limit event and temporarily disable provider.

        SPEC: docs/spec/05_LLM_SPEC.md#7-quota--rate-management

        Temporarily disables provider for retry_after seconds.
        """
        disabled_until = time.time() + retry_after
        self._disabled_providers[provider] = disabled_until
        logger.warning(
            "Provider %s rate limited — disabled for %.1fs",
            provider, retry_after,
        )

    def is_provider_available(self, provider: str) -> bool:
        """Check if a provider is currently available (not rate-limited)."""
        disabled_until = self._disabled_providers.get(provider)
        if disabled_until is None:
            return True
        if time.time() >= disabled_until:
            del self._disabled_providers[provider]
            return True
        return False


__all__ = ["LLMQuotaManager"]
