"""Layer 1: Perception — filters and weights incoming stimuli.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#sq-01-sq-03
"""
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID

from app.engine.agent.schema import AgentAction, AgentState, ACTION_WEIGHT
from app.engine.agent.fatigue import ExposureFatigue


@dataclass
class EnvironmentEvent:
    """A single event in the simulation environment.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
    """
    event_type: Literal["campaign_ad", "influencer_post", "expert_review", "community_discussion"]
    content_id: UUID
    message: str
    source_agent_id: UUID | None
    channel: str
    timestamp: int
    target_communities: list[str] = field(default_factory=list)
    controversy: float = 0.5  # [0.0, 1.0] — SQ-03: 전문가 의견 점수 동적 계산에 사용


@dataclass
class FeedItem:
    """A single item in the agent's perception feed.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
    """
    content_id: UUID
    event_type: str
    message: str
    source_agent_id: UUID | None
    exposure_score: float
    channel: str


@dataclass
class SocialSignal:
    """Weighted neighbor action signal.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
    """
    neighbor_id: UUID
    action: AgentAction
    edge_weight: float
    weighted_score: float


@dataclass
class ExpertSignal:
    """Expert opinion extracted from expert_review events.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
    """
    expert_id: UUID
    opinion_score: float
    credibility: float
    content_id: UUID


@dataclass
class NeighborAction:
    """Action taken by a neighbor agent this step.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
    """
    agent_id: UUID
    action: AgentAction
    content_id: UUID
    step: int


@dataclass
class PerceptionResult:
    """Output of PerceptionLayer.observe().

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
    """
    feed_items: list[FeedItem]
    social_signals: list[SocialSignal]
    expert_signals: list[ExpertSignal]
    total_exposure_score: float


_CHANNEL_WEIGHT: dict[str, float] = {
    "social_feed": 1.0,
    "search": 0.8,
    "direct": 1.2,
}

_EVENT_TYPE_WEIGHT: dict[str, float] = {
    "campaign_ad": 0.8,
    "influencer_post": 1.0,
    "expert_review": 1.2,
    "community_discussion": 0.9,
}


class PerceptionLayer:
    """Filters and weights incoming stimuli from the environment.

    SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
    """

    def __init__(self, feed_capacity: int = 20):
        """SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer"""
        if feed_capacity <= 0:
            raise ValueError(f"feed_capacity must be > 0, got {feed_capacity}")
        self._feed_capacity = feed_capacity
        self._fatigue = ExposureFatigue()  # SQ-01: 피로/포화 모델

    def observe(
        self,
        agent: AgentState,
        environment_events: list[EnvironmentEvent],
        neighbor_actions: list[NeighborAction],
        edge_weights: dict[UUID, float] | None = None,
    ) -> PerceptionResult:
        """Filters and weights incoming stimuli from the environment.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
        SPEC: docs/spec/21_SIMULATION_QUALITY_SPEC.md#sq-01-sq-03

        Args:
            edge_weights: neighbor_id -> trust weight from network (SQ-02).
                          None이면 1.0 fallback (하위 호환).

        Determinism: Pure function. Same inputs -> same output. No RNG.
        Side Effects: None.
        """
        # SQ-01: 피로/포화 배율 계산
        fatigue_factor = self._fatigue.compute_fatigue_factor(agent.exposure_count)

        # Step 1: Compute exposure_score per event (피로 배율 적용)
        scored_events: list[tuple[float, int, EnvironmentEvent]] = []
        for idx, event in enumerate(environment_events):
            event_weight = _EVENT_TYPE_WEIGHT.get(event.event_type, 1.0)
            channel_weight = _CHANNEL_WEIGHT.get(event.channel, 1.0)
            affinity = (agent.personality.openness + agent.emotion.interest) / 2.0
            exposure_score = event_weight * channel_weight * affinity * fatigue_factor
            scored_events.append((exposure_score, idx, event))

        # Step 2: Sort by exposure_score DESC, stable via idx
        scored_events.sort(key=lambda x: (-x[0], x[1]))

        # Step 3: Truncate to feed_capacity
        scored_events = scored_events[:self._feed_capacity]

        # Convert to FeedItems
        feed_items = [
            FeedItem(
                content_id=ev.content_id,
                event_type=ev.event_type,
                message=ev.message,
                source_agent_id=ev.source_agent_id,
                exposure_score=score,
                channel=ev.channel,
            )
            for score, _, ev in scored_events
        ]

        # Step 4: Extract social_signals (SQ-02: 실제 edge_weight 반영)
        social_signals = []
        for na in neighbor_actions:
            action_weight = ACTION_WEIGHT.get(na.action, 0.0)
            # SQ-02: edge_weights dict에서 neighbor의 신뢰 가중치 조회, 없으면 1.0
            edge_weight = (edge_weights or {}).get(na.agent_id, 1.0)
            weighted_score = action_weight * edge_weight
            social_signals.append(SocialSignal(
                neighbor_id=na.agent_id,
                action=na.action,
                edge_weight=edge_weight,
                weighted_score=weighted_score,
            ))

        # Step 5: Extract expert_signals from expert_review events (SQ-03: 동적 계산)
        expert_signals = []
        for event in environment_events:
            if event.event_type == "expert_review":
                # SQ-03: credibility = 1.0 - agent.skepticism (회의주의에 반비례)
                credibility = max(0.0, min(1.0, 1.0 - agent.personality.skepticism))
                # SQ-03: opinion_score = controversy * (1 - skepticism) * channel_boost
                channel_boost = 1.2 if event.channel == "direct" else 1.0
                opinion_score = max(0.0, min(1.0,
                    event.controversy * (1.0 - agent.personality.skepticism) * channel_boost
                ))
                expert_signals.append(ExpertSignal(
                    expert_id=event.source_agent_id if event.source_agent_id else event.content_id,
                    opinion_score=opinion_score,
                    credibility=credibility,
                    content_id=event.content_id,
                ))

        # Step 6: total_exposure_score
        total_exposure_score = sum(item.exposure_score for item in feed_items)

        return PerceptionResult(
            feed_items=feed_items,
            social_signals=social_signals,
            expert_signals=expert_signals,
            total_exposure_score=total_exposure_score,
        )


__all__ = [
    "PerceptionLayer",
    "EnvironmentEvent",
    "FeedItem",
    "SocialSignal",
    "ExpertSignal",
    "NeighborAction",
    "PerceptionResult",
]
