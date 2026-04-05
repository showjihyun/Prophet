"""F30 — Hybrid Execution Mode: per-step LLM provider routing.
SPEC: docs/spec/09_HARNESS_SPEC.md#13-f30

Allows simulations to use different LLM providers at different steps
for A/B testing, cost scheduling, and resilience.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Literal, TYPE_CHECKING

from app.llm.schema import LLMProviderError

if TYPE_CHECKING:
    from app.llm.registry import LLMAdapterRegistry

logger = logging.getLogger(__name__)

ProviderName = Literal["ollama", "claude", "openai", "gemini", "vllm", "mock"]


@dataclass
class HybridSchedule:
    """Per-step provider assignment policy.

    SPEC: docs/spec/09_HARNESS_SPEC.md#13-f30
    """
    # Static mapping: step number -> provider name
    step_provider_map: dict[int, ProviderName] = field(default_factory=dict)

    # Default provider when no mapping exists for the current step
    default_provider: ProviderName = "ollama"

    # Optional dynamic selector (step, agent_count) -> provider
    # Takes precedence over step_provider_map if set.
    dynamic_selector: Callable[[int, int], ProviderName] | None = None


@dataclass
class HybridStepResult:
    """Result of a hybrid-routed step.

    SPEC: docs/spec/09_HARNESS_SPEC.md#13-f30
    """
    step: int
    provider_used: ProviderName
    was_fallback: bool = False
    fallback_reason: str | None = None


class HybridExecRouter:
    """Per-step LLM provider routing for simulations.

    SPEC: docs/spec/09_HARNESS_SPEC.md#13-f30

    Integrates with LLMAdapterRegistry.evaluate(adapter_name=...)
    to route each step's Tier 3 calls to the scheduled provider.
    """

    def __init__(self, schedule: HybridSchedule) -> None:
        self._schedule = schedule
        self._log: list[HybridStepResult] = []

    def select_provider(self, step: int, agent_count: int = 0) -> ProviderName:
        """Return provider for the given step.

        Priority: dynamic_selector > step_provider_map > default_provider.

        SPEC: docs/spec/09_HARNESS_SPEC.md#13-f30
        """
        # 1. Dynamic selector has highest priority
        if self._schedule.dynamic_selector is not None:
            return self._schedule.dynamic_selector(step, agent_count)

        # 2. Static step map
        if step in self._schedule.step_provider_map:
            return self._schedule.step_provider_map[step]

        # 3. Default
        return self._schedule.default_provider

    async def execute_step(
        self,
        step: int,
        agent_count: int,
        registry: LLMAdapterRegistry,
    ) -> HybridStepResult:
        """Select provider for this step and validate availability.

        SPEC: docs/spec/09_HARNESS_SPEC.md#13-f30

        If selected provider is not healthy, fall back to default_provider.
        Returns HybridStepResult with provider_used and fallback info.
        """
        selected = self.select_provider(step, agent_count)

        # Check health of selected provider
        adapter = registry.get(selected)
        healthy = await adapter.health_check()

        if healthy:
            result = HybridStepResult(
                step=step,
                provider_used=selected,
                was_fallback=False,
            )
            self._log.append(result)
            return result

        # Fallback to default_provider
        logger.warning(
            "F30: provider %r unhealthy at step %d, falling back to %r",
            selected, step, self._schedule.default_provider,
        )
        fallback = self._schedule.default_provider
        fallback_adapter = registry.get(fallback)
        fallback_healthy = await fallback_adapter.health_check()

        if not fallback_healthy:
            raise LLMProviderError(
                f"F30: No healthy providers — "
                f"primary {selected!r} and fallback {fallback!r} both unhealthy"
            )

        result = HybridStepResult(
            step=step,
            provider_used=fallback,
            was_fallback=True,
            fallback_reason=f"{selected!r} unhealthy, fell back to {fallback!r}",
        )
        self._log.append(result)
        return result

    def execution_log(self) -> list[HybridStepResult]:
        """Return all step results logged so far.

        SPEC: docs/spec/09_HARNESS_SPEC.md#13-f30
        """
        return list(self._log)


__all__ = ["HybridSchedule", "HybridStepResult", "HybridExecRouter", "ProviderName"]
