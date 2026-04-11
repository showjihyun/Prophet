"""Layer 6: Influence — models how agent actions propagate to network neighbors.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer
SPEC: docs/spec/26_DIFFUSION_CALIBRATION_SPEC.md (Round 7-d calibration)
"""
import random as stdlib_random
from dataclasses import dataclass
from uuid import UUID

from app.engine.agent.schema import AgentAction, AgentEmotion, AgentState
from app.engine.agent.emotion import EmotionLayer
from app.engine.diffusion.propagation_calibration import propagation_probability


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
        """Aggregate score. Range [0.0, 1.0].

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influencelayer
        SPEC: docs/spec/26_DIFFUSION_CALIBRATION_SPEC.md (Round 8-3)

        Signed-weight formula with stronger coefficients so the campaign
        design dimensions (novelty, utility, controversy) can actually
        produce extreme adoption outcomes — "stuck at 12%" on one end
        and "viral cascade" on the other.

        Formula:
            0.6·utility + 0.5·novelty − 0.7·controversy + 0.3

        Properties:
        - All-neutral  (0.5 / 0.5 / 0.5) → 0.50   (baseline)
        - Best case    (util=1, nov=1, cont=0) → 1.40 → clamp 1.0
        - Worst case   (util=0, nov=0, cont=1) → −0.40 → clamp 0.0
        - Reframed     (0.5 / 0.8 / 0.2) → 0.86   (primes viral cascade)
        - High-contro. (0.5 / 0.4 / 0.7) → 0.31   (primes stall/collapse)

        History:
        - Round 7 baseline used the naïve mean ``(n+c+u)/3`` which
          rewarded controversy — verification pilot showed reframed
          campaigns underperforming baseline. Bug.
        - Round 7-d flipped the controversy sign with coefficients
          ±0.4 and a +0.5 baseline. Spread was 0.94 vs 0.58 (1.62×) —
          directionally correct but not expressive enough for the
          README's "stuck at 12%" scenario: the worst possible input
          still produced score=0.10, keeping diffusion alive.
        - Round 8-3 increases coefficients to 0.6/0.5/−0.7 and lowers
          the baseline to +0.3. Spread is now 0.86 vs 0.31 (2.77×) and
          the worst case actually saturates at 0 — enough headroom to
          reproduce stalled-adoption scenarios without touching the
          other factors in the propagation product.
        """
        raw = 0.6 * self.utility + 0.5 * self.novelty - 0.7 * self.controversy + 0.3
        return max(0.0, min(1.0, raw))

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
            # Round 7-d calibration — single source of truth in
            # ``app.engine.diffusion.propagation_calibration``. The same
            # formula was previously duplicated here and in
            # ``propagation_model.py``; only one copy got the fix last time,
            # and low-centrality agents stopped propagating for months.
            p = propagation_probability(
                influence_score=source_agent.influence_score,
                trust=trust_ij,
                emotion_factor=emotion_f,
                message_strength=message_strength.score,
            )

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
