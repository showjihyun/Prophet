"""Layer 4: Cognition — evaluates content and produces action recommendations.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-4-cognitionlayer
"""
from dataclasses import dataclass
from typing import Literal

from app.engine.agent.schema import AgentAction, AgentState
from app.engine.agent.perception import PerceptionResult
from app.engine.agent.memory import MemoryRecord


@dataclass
class CognitionResult:
    """Output of CognitionLayer.evaluate().

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-4-cognitionlayer

    Invariants:
      - evaluation_score in [-2.0, 2.0]
      - confidence in [0.0, 1.0]
      - reasoning is None for Tier 1/2, non-empty str for Tier 3
    """
    evaluation_score: float
    reasoning: str | None
    recommended_action: AgentAction
    confidence: float
    tier_used: int


def _map_score_to_action(score: float) -> AgentAction:
    """Score-to-Action Mapping from SPEC.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-4-cognitionlayer

      [-2.0, -1.0)  -> MUTE
      [-1.0, -0.5)  -> IGNORE
      [-0.5,  0.0)  -> VIEW
      [ 0.0,  0.3)  -> LIKE
      [ 0.3,  0.5)  -> SAVE
      [ 0.5,  0.8)  -> COMMENT
      [ 0.8,  1.2)  -> SHARE
      [ 1.2,  2.0]  -> ADOPT
    """
    if score < -1.0:
        return AgentAction.MUTE
    elif score < -0.5:
        return AgentAction.IGNORE
    elif score < 0.0:
        return AgentAction.VIEW
    elif score < 0.3:
        return AgentAction.LIKE
    elif score < 0.5:
        return AgentAction.SAVE
    elif score < 0.8:
        return AgentAction.COMMENT
    elif score < 1.2:
        return AgentAction.SHARE
    else:
        return AgentAction.ADOPT


class CognitionLayer:
    """Evaluates content and produces action recommendations.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-4-cognitionlayer

    Three tiers with IDENTICAL output shape (CognitionResult):
        Tier 1: Rule Engine
        Tier 2: Heuristic (Tier 1 + personality adjustment)
        Tier 3: LLM (falls back to Tier 2 in Phase 2)
    """

    def evaluate(
        self,
        agent: AgentState,
        perception: PerceptionResult,
        memories: list[MemoryRecord],
        cognition_tier: Literal[1, 2, 3],
        community_bias: float = 0.0,
    ) -> CognitionResult:
        """Evaluates content and returns CognitionResult.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-4-cognitionlayer

        Determinism:
            Tier 1/2: Pure function (deterministic).
            Tier 3: Falls back to Tier 2 in Phase 2.
        """
        if cognition_tier not in (1, 2, 3):
            raise ValueError(f"cognition_tier must be 1, 2, or 3, got {cognition_tier}")

        # Clamp community_bias
        community_bias = max(-1.0, min(1.0, community_bias))

        # memory_weight = mean(m.emotion_weight for m in memories) or 0.0
        if memories:
            memory_weight = sum(m.emotion_weight for m in memories) / len(memories)
        else:
            memory_weight = 0.0

        # Tier 1: Rule Engine
        # Raw evaluation per SPEC formula, then scaled to use full [-2, 2] range
        raw_evaluation = (
            agent.emotion.interest * 0.3
            + agent.emotion.trust * 0.25
            - agent.emotion.skepticism * 0.25
            + community_bias * 0.1
            + memory_weight * 0.1
        )
        # Scale to utilize the full [-2.0, 2.0] range
        # Raw range is approximately [-0.35, 0.75], center ~0.2
        # Map to [-2, 2] by scaling factor
        evaluation = raw_evaluation * 4.0
        evaluation = max(-2.0, min(2.0, evaluation))

        tier_used = 1

        if cognition_tier >= 2:
            # Tier 2: Heuristic (Tier 1 + personality adjustment)
            personality_adj = (
                agent.personality.openness * 0.3
                - agent.personality.skepticism * 0.3
                + agent.personality.trend_following * 0.2
                + agent.personality.brand_loyalty * 0.2
            )
            evaluation = max(-2.0, min(2.0, evaluation + personality_adj * 0.5))
            tier_used = 2

        if cognition_tier == 3:
            # Tier 3: LLM — Phase 2 fallback to Tier 2
            tier_used = 2  # Fallback: Tier 3 -> Tier 2 in Phase 2

        confidence = abs(evaluation) / 2.0
        confidence = max(0.0, min(1.0, confidence))

        recommended_action = _map_score_to_action(evaluation)

        return CognitionResult(
            evaluation_score=evaluation,
            reasoning=None,  # None for Tier 1/2
            recommended_action=recommended_action,
            confidence=confidence,
            tier_used=tier_used,
        )


__all__ = ["CognitionLayer", "CognitionResult"]
