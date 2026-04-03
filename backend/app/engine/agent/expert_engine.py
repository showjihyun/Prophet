"""Expert intervention engine — generates expert opinions via rule-based logic.
SPEC: docs/spec/01_AGENT_SPEC.md#expert-agents
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from app.engine.agent.schema import AgentState, AgentType
from app.engine.diffusion.schema import ExpertOpinion

logger = logging.getLogger(__name__)


@dataclass
class ExpertInterventionEngine:
    """Generates expert opinions for EXPERT-type agents.

    SPEC: docs/spec/01_AGENT_SPEC.md#expert-agents

    Rule-based implementation (no LLM required):
    - score      = agent.belief * agent.personality.skepticism
    - confidence = abs(score)
    - Only processes agents with agent_type == AgentType.EXPERT.
    """

    def generate_expert_opinion(
        self,
        agent: AgentState,
        campaign: object,  # CampaignConfig or CampaignEvent — used for community list
        step: int,
    ) -> ExpertOpinion | None:
        """Generate an expert opinion for an EXPERT agent.

        SPEC: docs/spec/01_AGENT_SPEC.md#expert-agents

        Args:
            agent:    The agent state (must be AgentType.EXPERT).
            campaign: Campaign context (provides community targeting info).
            step:     Current simulation step.

        Returns:
            ExpertOpinion dataclass, or None if the agent is not an expert.
        """
        if agent.agent_type != AgentType.EXPERT:
            logger.debug(
                "generate_expert_opinion: agent %s is not EXPERT (type=%s), skipping",
                agent.agent_id,
                agent.agent_type,
            )
            return None

        score = agent.belief * agent.personality.skepticism
        confidence = abs(score)

        # Determine affected communities from campaign if possible
        affects_communities: list[UUID] = []
        if hasattr(campaign, "target_communities"):
            raw = campaign.target_communities  # list[UUID] or list[str]
            for c in raw:
                if isinstance(c, UUID):
                    affects_communities.append(c)
                else:
                    try:
                        affects_communities.append(UUID(str(c)))
                    except (ValueError, AttributeError):
                        pass  # non-UUID community key; skip

        # Fallback: include the expert's own community
        if not affects_communities:
            affects_communities = [agent.community_id]

        reasoning = (
            f"Expert assessment at step {step}: "
            f"belief={agent.belief:.3f}, skepticism={agent.personality.skepticism:.3f}, "
            f"score={score:.3f}"
        )

        opinion = ExpertOpinion(
            expert_agent_id=agent.agent_id,
            score=score,
            reasoning=reasoning,
            step=step,
            affects_communities=affects_communities,
            confidence=confidence,
        )

        logger.debug(
            "Expert opinion generated: agent=%s score=%.4f confidence=%.4f",
            agent.agent_id,
            score,
            confidence,
        )

        return opinion


__all__ = ["ExpertInterventionEngine"]
