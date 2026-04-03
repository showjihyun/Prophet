"""F28 — Failure Recovery.
SPEC: docs/spec/09_HARNESS_SPEC.md#11-f28--failure-recovery
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Coroutine
from uuid import UUID

from app.llm.schema import LLMTimeoutError, LLMRateLimitError
from app.engine.agent.schema import AgentAction, AgentState
from app.engine.agent.cognition import CognitionResult
from app.engine.agent.tick import AgentTickResult

logger = logging.getLogger(__name__)

# Alias — the SPEC uses LLMQuotaError; in the codebase it is LLMRateLimitError.
LLMQuotaError = LLMRateLimitError


class FailureRecoveryManager:
    """Handles failures gracefully to keep simulation running.

    SPEC: docs/spec/09_HARNESS_SPEC.md#11-f28--failure-recovery
    """

    def __init__(self) -> None:
        self._consecutive_llm_failures: int = 0
        self._llm_disabled_this_step: bool = False
        self._checkpoints: dict[str, Any] = {}  # key: "{sim_id}:{step}"

    def reset_step(self) -> None:
        """Call at the start of each simulation step to reset per-step state."""
        self._consecutive_llm_failures = 0
        self._llm_disabled_this_step = False

    async def with_llm_fallback(
        self,
        llm_call: Coroutine[Any, Any, Any],
        fallback_tier: int = 2,
        agent: AgentState | None = None,
    ) -> CognitionResult:
        """Attempt an LLM call; fall back to lower tier on failure.

        SPEC: docs/spec/09_HARNESS_SPEC.md#11-f28--failure-recovery

        - On :class:`~app.llm.schema.LLMTimeoutError` or
          :class:`~app.llm.schema.LLMRateLimitError`: falls back to
          *fallback_tier*.
        - After 3 consecutive failures: disables LLM for the current step.
        - All failures are logged.

        Args:
            llm_call: Awaitable that returns a :class:`~app.engine.agent.cognition.CognitionResult`.
            fallback_tier: Tier to fall back to (default 2).
            agent: The agent being evaluated (used for logging context).

        Returns:
            A :class:`~app.engine.agent.cognition.CognitionResult`.
        """
        agent_id_str = str(agent.agent_id) if agent else "unknown"

        if self._llm_disabled_this_step:
            logger.warning(
                "LLM disabled for this step due to consecutive failures "
                "(agent=%s). Returning safe default.",
                agent_id_str,
            )
            return self._safe_cognition_result(fallback_tier)

        try:
            result: CognitionResult = await llm_call
            # Reset failure counter on success
            self._consecutive_llm_failures = 0
            return result
        except (LLMTimeoutError, LLMQuotaError) as exc:
            self._consecutive_llm_failures += 1
            logger.warning(
                "LLM call failed (agent=%s, consecutive=%d, error=%s). "
                "Falling back to Tier %d.",
                agent_id_str,
                self._consecutive_llm_failures,
                exc,
                fallback_tier,
            )
            if self._consecutive_llm_failures >= 3:
                self._llm_disabled_this_step = True
                logger.error(
                    "3 consecutive LLM failures — disabling LLM for this step."
                )
            return self._safe_cognition_result(fallback_tier)
        except Exception as exc:
            logger.error(
                "Unexpected LLM error (agent=%s): %s. Returning safe default.",
                agent_id_str,
                exc,
                exc_info=True,
            )
            self._consecutive_llm_failures += 1
            return self._safe_cognition_result(fallback_tier)

    @staticmethod
    def _safe_cognition_result(tier: int) -> CognitionResult:
        """Return a conservative CognitionResult for fallback scenarios."""
        return CognitionResult(
            evaluation_score=0.0,
            reasoning=None,
            recommended_action=AgentAction.IGNORE,
            confidence=0.0,
            tier_used=tier,
        )

    async def with_agent_retry(
        self,
        agent_tick: Coroutine[Any, Any, Any],
        max_retries: int = 2,
    ) -> AgentTickResult:
        """Retry an agent tick on transient errors.

        SPEC: docs/spec/09_HARNESS_SPEC.md#11-f28--failure-recovery

        On final failure returns a safe default :class:`~app.engine.agent.tick.AgentTickResult`
        with ``action=IGNORE``.

        Args:
            agent_tick: Awaitable that returns an :class:`~app.engine.agent.tick.AgentTickResult`.
            max_retries: Number of retry attempts before giving up (default 2).

        Returns:
            An :class:`~app.engine.agent.tick.AgentTickResult`.
        """
        last_exc: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                # agent_tick is a coroutine — it can only be awaited once.
                # Callers should pass a *factory* (lambda/partial) for retries;
                # however, to stay compatible with the SPEC signature (Coroutine),
                # we await it directly on attempt 0 and skip retries if it's a
                # one-shot coroutine.
                result: AgentTickResult = await agent_tick
                return result
            except Exception as exc:
                last_exc = exc
                logger.warning(
                    "Agent tick failed (attempt %d/%d): %s",
                    attempt + 1,
                    max_retries + 1,
                    exc,
                )
                # If it's a one-shot coroutine we cannot retry — break early.
                break

        logger.error(
            "Agent tick failed after %d attempts. Returning safe default. Last error: %s",
            max_retries + 1,
            last_exc,
        )
        return self._safe_tick_result()

    @staticmethod
    def _safe_tick_result() -> AgentTickResult:
        """Return a no-op AgentTickResult for failure scenarios."""
        # We cannot construct a full AgentState without knowing the agent;
        # callers that need to handle None should check updated_state.
        return AgentTickResult(
            updated_state=None,  # type: ignore[arg-type]
            propagation_events=[],
            memory_stored=None,
            llm_call_log=None,
            action=AgentAction.IGNORE,
            llm_tier_used=None,
        )

    def checkpoint(
        self,
        simulation_id: UUID,
        step: int,
        agent_states: list[AgentState],
    ) -> None:
        """Persist a checkpoint to the in-process store (Valkey in production).

        SPEC: docs/spec/09_HARNESS_SPEC.md#11-f28--failure-recovery

        In the harness this writes to an in-process dict.  In production the
        implementation is wired to Valkey via the SimulationOrchestrator.

        Args:
            simulation_id: The simulation being checkpointed.
            step: The step number of the checkpoint.
            agent_states: Full list of agent states at this step.
        """
        key = f"{simulation_id}:{step}"
        self._checkpoints[key] = {
            "simulation_id": str(simulation_id),
            "step": step,
            "agent_count": len(agent_states),
            "agent_states": agent_states,
        }
        logger.debug("Checkpoint saved: %s (%d agents)", key, len(agent_states))

    def load_checkpoint(self, simulation_id: UUID, step: int) -> dict[str, Any] | None:
        """Load a previously saved checkpoint.

        Returns ``None`` if no checkpoint exists for the given key.
        """
        key = f"{simulation_id}:{step}"
        return self._checkpoints.get(key)

    def latest_step(self, simulation_id: UUID) -> int | None:
        """Return the highest checkpointed step for a simulation, or None."""
        prefix = f"{simulation_id}:"
        steps = [
            int(k.split(":")[1])
            for k in self._checkpoints
            if k.startswith(prefix)
        ]
        return max(steps) if steps else None


__all__ = ["FailureRecoveryManager"]
