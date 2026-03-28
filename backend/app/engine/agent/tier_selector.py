"""LLM Tier Selection Algorithm — assigns inference tier to each agent.
SPEC: docs/spec/01_AGENT_SPEC.md#tier-selection
"""
import random as stdlib_random
from dataclasses import dataclass
from math import ceil
from uuid import UUID

from app.engine.agent.schema import AgentState, AgentType


@dataclass
class TierConfig:
    """Configuration for tier selection ratios.

    SPEC: docs/spec/01_AGENT_SPEC.md#tier-selection

    Invariant: max_tier3_ratio + max_tier2_ratio <= 0.5
    """
    max_tier3_ratio: float = 0.10
    max_tier2_ratio: float = 0.10
    slm_llm_ratio_override: float | None = None

    def __post_init__(self):
        if self.max_tier3_ratio + self.max_tier2_ratio > 0.5:
            raise ValueError("Tier 2+3 ratio must not exceed 50%")


class TierSelector:
    """Assigns inference tier (1, 2, or 3) to each agent for this step.

    SPEC: docs/spec/01_AGENT_SPEC.md#tier-selection
    """

    def assign_tiers(
        self,
        agents: list[AgentState],
        config: TierConfig,
        step_seed: int,
    ) -> dict[UUID, int]:
        """Assigns inference tier to each agent.

        SPEC: docs/spec/01_AGENT_SPEC.md#tier-selection

        Algorithm:
            Phase 1: Tier 3 selection (priority order: Expert, high-influence, critical decision)
            Phase 2: Tier 2 selection (influence > 0.5 or skeptic with high skepticism)
            Phase 3: Everyone else -> Tier 1

        Determinism: Deterministic for same step_seed + agent states.
        Side Effects: None.
        """
        if not agents:
            raise ValueError("agents list must not be empty")

        rng = stdlib_random.Random(step_seed)
        max_tier3 = ceil(len(agents) * config.max_tier3_ratio)
        max_tier2 = ceil(len(agents) * config.max_tier2_ratio)

        # Phase 1: Tier 3 selection (priority order)
        tier3_ids: set[UUID] = set()
        tier3_candidates: list[AgentState] = []

        # Priority 1: Expert agents
        for a in agents:
            if a.agent_type == AgentType.EXPERT:
                tier3_candidates.append(a)

        # Priority 2: High-influence agents
        for a in agents:
            if (a.agent_type == AgentType.INFLUENCER
                    and a.influence_score > 0.7
                    and a.agent_id not in {c.agent_id for c in tier3_candidates}):
                tier3_candidates.append(a)

        # Priority 3: Critical decision agents
        for a in agents:
            if (abs(a.belief) < 0.2
                    and a.exposure_count > 3
                    and not a.adopted
                    and a.agent_id not in {c.agent_id for c in tier3_candidates}):
                tier3_candidates.append(a)

        # Cap
        if len(tier3_candidates) > max_tier3:
            tier3 = tier3_candidates[:max_tier3]
        else:
            tier3 = tier3_candidates

        tier3_ids = {a.agent_id for a in tier3}

        # Phase 2: Tier 2 selection
        remaining = [a for a in agents if a.agent_id not in tier3_ids]
        tier2_candidates = [
            a for a in remaining
            if a.influence_score > 0.5
            or (a.agent_type == AgentType.SKEPTIC and a.emotion.skepticism > 0.7)
        ]

        if len(tier2_candidates) > max_tier2:
            tier2 = rng.sample(tier2_candidates, max_tier2)
        else:
            tier2 = tier2_candidates

        tier2_ids = {a.agent_id for a in tier2}

        # Phase 3: Tier 1 = everyone else
        result: dict[UUID, int] = {}
        for a in agents:
            if a.agent_id in tier3_ids:
                result[a.agent_id] = 3
            elif a.agent_id in tier2_ids:
                result[a.agent_id] = 2
            else:
                result[a.agent_id] = 1

        return result


__all__ = ["TierSelector", "TierConfig"]
