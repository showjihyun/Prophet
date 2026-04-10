"""Layer 6: Influence — models how agent actions propagate to network neighbors.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer
"""
import random as stdlib_random
from dataclasses import dataclass
from uuid import UUID

from app.engine.agent.schema import AgentAction, AgentEmotion, AgentState
from app.engine.agent.emotion import EmotionLayer


@dataclass
class MessageStrength:
    """Content properties affecting propagation probability.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer

    Invariants: all fields in [0.0, 1.0].
    """
    novelty: float
    controversy: float
    utility: float

    @property
    def score(self) -> float:
        """Aggregate score. Returns mean of all dimensions. Range [0.0, 1.0].

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer
        """
        return (self.novelty + self.controversy + self.utility) / 3.0

    def __post_init__(self):
        for f in ['novelty', 'controversy', 'utility']:
            v = getattr(self, f)
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"MessageStrength.{f} must be in [0.0, 1.0], got {v}")


@dataclass
class ContextualPacket:
    """Structured propagation payload — carries source agent's reasoning context.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer
    """
    source_agent_id: UUID
    source_emotion: AgentEmotion
    source_summary: str
    message_strength: MessageStrength
    sentiment_polarity: float
    action_taken: AgentAction
    step: int


@dataclass
class PropagationEvent:
    """A single propagation from source to target.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer
    """
    source_agent_id: UUID
    target_agent_id: UUID
    content_id: UUID
    probability: float
    packet: ContextualPacket
    step: int
    action_type: str = "share"
    generated_content: str | None = None


# Actions that generate propagation events
_PROPAGATING_ACTIONS = {AgentAction.COMMENT, AgentAction.SHARE, AgentAction.REPOST, AgentAction.ADOPT}


def build_contextual_packet(
    source_agent: AgentState,
    action: AgentAction,
    message_strength: MessageStrength,
) -> ContextualPacket:
    """Builds a ContextualPacket from agent state.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer

    sentiment_polarity = (excitement + trust - skepticism) / 2.0, clamped to [-1, 1]
    """
    polarity = (
        source_agent.emotion.excitement
        + source_agent.emotion.trust
        - source_agent.emotion.skepticism
    ) / 2.0
    polarity = max(-1.0, min(1.0, polarity))

    return ContextualPacket(
        source_agent_id=source_agent.agent_id,
        source_emotion=source_agent.emotion,
        source_summary=f"Agent {source_agent.agent_id} took {action.value}",
        message_strength=message_strength,
        sentiment_polarity=polarity,
        action_taken=action,
        step=source_agent.step,
    )


class InfluenceLayer:
    """Models how agent actions propagate to network neighbors.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer

    Propagation occurs ONLY for: COMMENT, SHARE, REPOST, ADOPT.
    """

    def __init__(self):
        """SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer"""
        self._emotion_layer = EmotionLayer()

    def propagate(
        self,
        source_agent: AgentState,
        action: AgentAction,
        target_agent_ids: list[UUID],
        graph_edges: dict[tuple[UUID, UUID], float],
        message_strength: MessageStrength,
        step_seed: int,
    ) -> list[PropagationEvent]:
        """Computes propagation probability for each target and generates events.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer

        Algorithm:
            If action not in {COMMENT, SHARE, REPOST, ADOPT}: return []

            scope = select_targets(action, target_agent_ids, graph_edges)
            For each target:
                P = influence * trust_ij * max(emotion_factor, 0) * message_strength.score
                If ADOPT: P *= 0.5
                P = clamp(P, 0.0, 1.0)
                rng-based threshold check

        Determinism: Deterministic for same step_seed + inputs.
        Side Effects: None.
        """
        if action not in _PROPAGATING_ACTIONS:
            return []

        if not target_agent_ids:
            return []

        # Select targets based on action type
        scope = self._select_targets(action, source_agent.agent_id, target_agent_ids, graph_edges)

        emotion_f = self._emotion_layer.emotion_factor(source_agent.emotion)
        packet = build_contextual_packet(source_agent, action, message_strength)

        # Use a deterministic content_id (from first feed item or agent step)
        content_id = source_agent.agent_id  # placeholder content_id

        events = []
        for target_id in scope:
            trust_ij = graph_edges.get((source_agent.agent_id, target_id), 0.0)
            p = source_agent.influence_score * trust_ij * max(emotion_f, 0.0) * message_strength.score

            if action == AgentAction.ADOPT:
                p *= 0.5

            p = max(0.0, min(1.0, p))

            # Deterministic RNG per target
            rng = stdlib_random.Random(step_seed ^ hash(target_id))
            if rng.random() < p:
                events.append(PropagationEvent(
                    source_agent_id=source_agent.agent_id,
                    target_agent_id=target_id,
                    content_id=content_id,
                    probability=p,
                    packet=packet,
                    step=source_agent.step,
                    action_type=action.value,
                ))

        return events

    def _select_targets(
        self,
        action: AgentAction,
        source_id: UUID,
        target_agent_ids: list[UUID],
        graph_edges: dict[tuple[UUID, UUID], float],
    ) -> list[UUID]:
        """Select propagation targets based on action type.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer

        COMMENT -> top-5 neighbors by edge weight
        SHARE   -> all neighbors
        REPOST  -> all neighbors
        ADOPT   -> all neighbors
        """
        if action == AgentAction.COMMENT:
            # Top-5 by edge weight
            weighted = [
                (graph_edges.get((source_id, t), 0.0), t)
                for t in target_agent_ids
            ]
            weighted.sort(key=lambda x: x[0], reverse=True)
            return [t for _, t in weighted[:5]]
        else:
            # SHARE, REPOST, ADOPT: all neighbors
            return list(target_agent_ids)


__all__ = [
    "InfluenceLayer",
    "MessageStrength",
    "PropagationEvent",
    "ContextualPacket",
    "build_contextual_packet",
]
