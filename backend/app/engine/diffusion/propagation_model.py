"""Propagation Model — models how actions spread through the network.
SPEC: docs/spec/03_DIFFUSION_SPEC.md#propagationmodel
"""
import logging
import random
from uuid import UUID, uuid4

from app.engine.agent.schema import AgentAction, AgentState
from app.engine.network.schema import SocialNetwork
from app.engine.diffusion.schema import ContextualPacket, PropagationEvent

logger = logging.getLogger(__name__)

# Actions that generate propagation events
_PROPAGATION_ACTIONS = {
    AgentAction.COMMENT,
    AgentAction.SHARE,
    AgentAction.REPOST,
    AgentAction.ADOPT,
}


class PropagationModel:
    """Models how agent actions propagate through the social network.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#propagationmodel

    Actions that generate propagation events:
        COMMENT  -> Active propagation to top-5 neighbors (subset)
        SHARE    -> Active propagation to all neighbors (with endorsement)
        REPOST   -> Active propagation to all neighbors (lower trust)
        ADOPT    -> Passive propagation (P * 0.5)

    P(i->j) = influence_i * trust_ij * emotion_factor * message_strength
    Probability is clamped to [0.0, 1.0].
    """

    def propagate(
        self,
        source_agent: AgentState,
        action: AgentAction,
        graph: SocialNetwork,
        message_id: UUID,
        step: int,
        seed: int | None = None,
        campaign_message: str = "",
    ) -> list[PropagationEvent]:
        """Generate propagation events based on agent action.

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#propagationmodel

        Only COMMENT/SHARE/REPOST/ADOPT generate events.
        Returns empty list for other actions.

        A ``ContextualPacket`` is attached to each event when ``campaign_message``
        is provided (non-empty). The packet captures the sender's emotional state
        and reasoning so downstream agents can model emergent text mutation.
        """
        if action not in _PROPAGATION_ACTIONS:
            return []

        rng = random.Random(seed)
        nx_graph = graph.graph

        source_node = self._find_agent_node(source_agent, nx_graph)
        if source_node is None:
            return []

        neighbors = list(nx_graph.neighbors(source_node))
        if not neighbors:
            return []

        # Select target neighbors based on action type
        if action == AgentAction.COMMENT:
            # Top-5 neighbors by edge weight
            neighbor_weights = []
            for n in neighbors:
                w = nx_graph[source_node][n].get("weight", 0.5)
                neighbor_weights.append((n, w))
            neighbor_weights.sort(key=lambda x: x[1], reverse=True)
            targets = [n for n, _ in neighbor_weights[:5]]
        elif action in (AgentAction.SHARE, AgentAction.REPOST, AgentAction.ADOPT):
            targets = neighbors
        else:
            targets = []

        events: list[PropagationEvent] = []
        # Apply a floor so low-influence agents still have a chance to propagate.
        # influence_score is 0.1–0.9 in typical agents, but guard against edge cases.
        influence = max(0.1, source_agent.influence_score)

        # Emotion factor: excitement - skepticism
        emotion_factor = (
            source_agent.emotion.excitement - source_agent.emotion.skepticism
        )

        # Message strength approximation (based on action weight)
        message_strength = {
            AgentAction.COMMENT: 0.6,
            AgentAction.SHARE: 0.8,
            AgentAction.REPOST: 0.7,
            AgentAction.ADOPT: 1.0,
        }.get(action, 0.5)

        # Build contextual packet once for all events from this source agent.
        # Only attached when a campaign_message is available.
        contextual_packet: ContextualPacket | None = None
        if campaign_message:
            emotion_summary = (
                f"interest={source_agent.emotion.interest:.1f}, "
                f"trust={source_agent.emotion.trust:.1f}, "
                f"excitement={source_agent.emotion.excitement:.1f}"
            )
            reasoning = (
                f"Shared because belief={source_agent.belief:.2f}, "
                f"action={action.value}"
            )
            contextual_packet = ContextualPacket(
                original_content=campaign_message,
                sender_emotion_summary=emotion_summary,
                sender_reasoning=reasoning,
                mutation_depth=0,
            )

        for target_node in targets:
            edge_data = nx_graph[source_node][target_node]
            trust = edge_data.get("weight", 0.5)

            # Lower trust for REPOST (no endorsement)
            if action == AgentAction.REPOST:
                trust *= 0.7

            # P(i→j) = influence_i * trust_ij * emotion_factor * message_strength
            prob = influence * trust * max(0.0, emotion_factor) * message_strength

            # ADOPT: passive propagation → P * 0.5
            if action == AgentAction.ADOPT:
                prob *= 0.5

            # Clamp to [0.0, 1.0]
            if prob > 1.0:
                logger.warning(
                    "Propagation probability %.4f > 1.0, clamping to 1.0 "
                    "(source=%s, target_node=%s)",
                    prob, source_agent.agent_id, target_node,
                )
                prob = 1.0
            elif prob < 0.0:
                logger.warning(
                    "Propagation probability %.4f < 0.0, clamping to 0.0 "
                    "(source=%s, target_node=%s)",
                    prob, source_agent.agent_id, target_node,
                )
                prob = 0.0

            # Stochastic: event only generated if random check passes
            if rng.random() < prob:
                target_agent_id = nx_graph.nodes[target_node].get("agent_id")
                if target_agent_id is not None:
                    events.append(
                        PropagationEvent(
                            source_agent_id=source_agent.agent_id,
                            target_agent_id=target_agent_id,
                            action_type=action.value,
                            probability=prob,
                            step=step,
                            message_id=message_id,
                            contextual_packet=contextual_packet,
                        )
                    )

        return events

    def compute_diffusion_rate(
        self,
        adoption_history: list[int],
    ) -> float:
        """Compute current diffusion rate R(t) = N(t) - N(t-1).

        SPEC: docs/spec/03_DIFFUSION_SPEC.md#propagationmodel

        Returns 0.0 if history has fewer than 2 entries or rate is negative.
        """
        if len(adoption_history) < 2:
            return 0.0

        rate = adoption_history[-1] - adoption_history[-2]

        if rate < 0:
            logger.warning(
                "Negative diffusion rate %d, clamping to 0.0", rate
            )
            return 0.0

        return float(rate)

    @staticmethod
    def _find_agent_node(agent: AgentState, nx_graph) -> int | None:  # noqa: ANN001
        """Find the networkx node ID for an agent."""
        for node, data in nx_graph.nodes(data=True):
            if data.get("agent_id") == agent.agent_id:
                return node
        return None


__all__ = ["PropagationModel"]
