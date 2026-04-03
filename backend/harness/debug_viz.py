"""F25 — Debug Visualization.
SPEC: docs/spec/09_HARNESS_SPEC.md#9-f25--debug-visualization
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.engine.agent.schema import AgentAction, AgentEmotion


@dataclass
class AgentDecisionTrace:
    """Full trace of a single agent tick decision.

    SPEC: docs/spec/09_HARNESS_SPEC.md#9-f25--debug-visualization
    """
    agent_id: UUID
    step: int
    tier_used: int
    perception_summary: str
    memories_retrieved: list[dict[str, Any]]  # memory + retrieval score
    emotion_before: AgentEmotion
    emotion_after: AgentEmotion
    cognition_score_components: dict[str, float]
    social_pressure: float
    action_probabilities: dict[str, float]
    chosen_action: AgentAction
    llm_prompt: str | None
    llm_response: str | None
    reasoning: str | None

    def to_dict(self) -> dict[str, Any]:
        """Serialise trace to a JSON-safe dict."""
        return {
            "agent_id": str(self.agent_id),
            "step": self.step,
            "tier_used": self.tier_used,
            "perception_summary": self.perception_summary,
            "memories_retrieved": self.memories_retrieved,
            "emotion_before": {
                "interest": self.emotion_before.interest,
                "trust": self.emotion_before.trust,
                "skepticism": self.emotion_before.skepticism,
                "excitement": self.emotion_before.excitement,
            },
            "emotion_after": {
                "interest": self.emotion_after.interest,
                "trust": self.emotion_after.trust,
                "skepticism": self.emotion_after.skepticism,
                "excitement": self.emotion_after.excitement,
            },
            "cognition_score_components": self.cognition_score_components,
            "social_pressure": self.social_pressure,
            "action_probabilities": self.action_probabilities,
            "chosen_action": self.chosen_action.value,
            "llm_prompt": self.llm_prompt,
            "llm_response": self.llm_response,
            "reasoning": self.reasoning,
        }


class AgentDecisionDebugger:
    """Produces structured debug output of a single agent tick.

    Used to inspect why an agent made a specific decision.
    SPEC: docs/spec/09_HARNESS_SPEC.md#9-f25--debug-visualization
    """

    def explain_tick(self, tick_result: Any) -> AgentDecisionTrace:
        """Extract and return a full decision trace from a tick result.

        SPEC: docs/spec/09_HARNESS_SPEC.md#9-f25--debug-visualization

        Args:
            tick_result: An :class:`~app.engine.agent.tick.AgentTickResult`
                produced by :meth:`~app.engine.agent.tick.AgentTick.tick`
                or ``async_tick``.

        Returns:
            :class:`AgentDecisionTrace` with all available fields populated.
            Fields that cannot be derived from *tick_result* are set to
            sensible defaults (empty list / ``None`` / 0.0).
        """
        updated: Any = tick_result.updated_state

        # --- Perception summary -------------------------------------------------
        perception_summary = (
            f"action={tick_result.action.value}, "
            f"belief={updated.belief:.3f}, "
            f"exposure={updated.exposure_count}"
        )

        # --- Memories -----------------------------------------------------------
        memories_retrieved: list[dict[str, Any]] = []
        # tick_result does not carry raw memory records in its public API;
        # the memory_stored field holds only the single newly stored record.
        if tick_result.memory_stored is not None:
            mem = tick_result.memory_stored
            memories_retrieved = [{
                "content": getattr(mem, "content", repr(mem)),
                "memory_type": getattr(mem, "memory_type", "unknown"),
                "score": getattr(mem, "retrieval_score", 1.0),
                "step": getattr(mem, "step", updated.step),
            }]

        # --- Emotions -----------------------------------------------------------
        # The updated_state carries emotion_after; we reconstruct a plausible
        # emotion_before from what's available (unchanged fields).
        emotion_after: AgentEmotion = updated.emotion

        # If the tick_result exposes a pre-tick state we use it; otherwise clone.
        emotion_before: AgentEmotion = getattr(
            tick_result, "_emotion_before", emotion_after
        )

        # --- Cognition components -----------------------------------------------
        # Derive a minimal score breakdown from what the tick exposes.
        tier_used: int = tick_result.llm_tier_used if tick_result.llm_tier_used is not None else 1
        cognition_score_components: dict[str, float] = {
            "tier_used": float(tier_used),
        }

        # --- LLM payload --------------------------------------------------------
        llm_prompt: str | None = None
        llm_response: str | None = None
        reasoning: str | None = None
        call_log = getattr(tick_result, "llm_call_log", None)
        if call_log is not None:
            llm_prompt = getattr(call_log, "prompt", None)
            llm_response = getattr(call_log, "response", None)
            reasoning = getattr(call_log, "reasoning", None)

        # --- Action probability placeholder ------------------------------------
        # A full probability vector requires access to the DecisionLayer internals.
        # We surface the chosen action with probability 1.0 as a safe default.
        action_probabilities: dict[str, float] = {
            tick_result.action.value: 1.0,
        }

        return AgentDecisionTrace(
            agent_id=updated.agent_id,
            step=updated.step,
            tier_used=tier_used,
            perception_summary=perception_summary,
            memories_retrieved=memories_retrieved,
            emotion_before=emotion_before,
            emotion_after=emotion_after,
            cognition_score_components=cognition_score_components,
            social_pressure=0.0,  # not exposed on tick result directly
            action_probabilities=action_probabilities,
            chosen_action=tick_result.action,
            llm_prompt=llm_prompt,
            llm_response=llm_response,
            reasoning=reasoning,
        )


__all__ = ["AgentDecisionDebugger", "AgentDecisionTrace"]
