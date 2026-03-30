"""Negative cascade model — amplifies negative event propagation.
SPEC: docs/spec/03_DIFFUSION_SPEC.md#negative-cascade-model
"""
from __future__ import annotations

import logging
from uuid import UUID

from app.engine.agent.schema import AgentState, AgentType
from app.engine.diffusion.schema import NegativeEvent

logger = logging.getLogger(__name__)


class NegativeCascadeModel:
    """Computes sentiment impact of a negative event on target community agents.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#negative-cascade-model

    Rules:
    - Base impact = -(event.controversy * agent.personality.skepticism)
    - SKEPTIC agents amplify the impact by 1.5x
    - EARLY_ADOPTER agents dampen the impact by 0.5x
    - All other agent types use base impact unchanged
    """

    def process_negative_event(
        self,
        event: NegativeEvent,
        agents: list[AgentState],
        network: object,  # SocialNetwork — unused for now; reserved for future graph traversal
    ) -> list[tuple[UUID, float]]:
        """Compute per-agent sentiment deltas for a negative event.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#negative-cascade-model

        Args:
            event:   The negative event to propagate.
            agents:  Agents in the target communities.
            network: The social network (reserved for future community filtering).

        Returns:
            List of (agent_id, sentiment_delta) pairs where sentiment_delta <= 0.
        """
        results: list[tuple[UUID, float]] = []

        for agent in agents:
            base_delta = -(event.controversy * agent.personality.skepticism)

            if agent.agent_type == AgentType.SKEPTIC:
                delta = base_delta * 1.5
            elif agent.agent_type == AgentType.EARLY_ADOPTER:
                delta = base_delta * 0.5
            else:
                delta = base_delta

            results.append((agent.agent_id, delta))
            logger.debug(
                "NegativeCascade: agent=%s type=%s delta=%.4f",
                agent.agent_id,
                agent.agent_type,
                delta,
            )

        return results


__all__ = ["NegativeCascadeModel"]
