"""Community Sentiment Model.
SPEC: docs/spec/03_DIFFUSION_SPEC.md#sentimentmodel
"""
import logging
from uuid import UUID

from app.engine.agent.schema import AgentState
from app.engine.diffusion.schema import CommunitySentiment, ExpertOpinion

logger = logging.getLogger(__name__)

# Default expert influence factor (alpha)
_DEFAULT_EXPERT_ALPHA = 0.3


class SentimentModel:
    """Tracks and updates community-level sentiment.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#sentimentmodel

    sentiment = mean(belief_i for agent_i in community)
    sentiment_variance = var(belief_i)
    Expert influence: E_i(t+1) = E_i(t) + alpha * O_k

    Empty community -> 0.0 sentiment (guarded).
    """

    def __init__(self, expert_alpha: float = _DEFAULT_EXPERT_ALPHA) -> None:
        self._expert_alpha = expert_alpha

    def update_community_sentiment(
        self,
        community_id: UUID,
        agent_states: list[AgentState],
        expert_opinions: list[ExpertOpinion],
    ) -> CommunitySentiment:
        """Update sentiment for a community.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#sentimentmodel

        Returns CommunitySentiment with mean_belief, variance, adoption_rate.
        Empty community returns 0.0 for all metrics.
        """
        # Filter agents belonging to this community
        community_agents = [
            a for a in agent_states if a.community_id == community_id
        ]

        if not community_agents:
            logger.warning(
                "Empty community %s, returning 0.0 sentiment", community_id
            )
            return CommunitySentiment(
                community_id=community_id,
                mean_belief=0.0,
                sentiment_variance=0.0,
                adoption_rate=0.0,
                step=0,
            )

        # Collect beliefs
        beliefs = [a.belief for a in community_agents]

        # Apply expert opinion influence
        # E_i(t+1) = E_i(t) + alpha * O_k
        relevant_opinions = [
            op for op in expert_opinions
            if community_id in op.affects_communities
        ]

        if relevant_opinions:
            expert_adjustment = sum(
                op.score * op.confidence for op in relevant_opinions
            ) / len(relevant_opinions)

            beliefs = [
                max(-1.0, min(1.0, b + self._expert_alpha * expert_adjustment))
                for b in beliefs
            ]

        # Mean belief
        n = len(beliefs)
        mean_belief = sum(beliefs) / n

        # Variance
        if n > 1:
            variance = sum((b - mean_belief) ** 2 for b in beliefs) / n
        else:
            variance = 0.0

        # Adoption rate
        adopted_count = sum(1 for a in community_agents if a.adopted)
        adoption_rate = adopted_count / n

        # Step: use max step from agents
        step = max(a.step for a in community_agents)

        return CommunitySentiment(
            community_id=community_id,
            mean_belief=mean_belief,
            sentiment_variance=variance,
            adoption_rate=adoption_rate,
            step=step,
        )

    def detect_polarization(
        self,
        communities: list[CommunitySentiment],
        threshold: float = 0.4,
    ) -> bool:
        """Detect if any community is polarized.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#sentimentmodel

        Returns True if any community's sentiment_variance > threshold.
        """
        return any(c.sentiment_variance > threshold for c in communities)


__all__ = ["SentimentModel"]
