"""Layer 1: Perception — filters and weights incoming stimuli.
SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer
"""
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

from app.engine.agent.schema import AgentAction, AgentState, ACTION_WEIGHT


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

    def observe(
        self,
        agent: AgentState,
        environment_events: list[EnvironmentEvent],
        neighbor_actions: list[NeighborAction],
    ) -> PerceptionResult:
        """Filters and weights incoming stimuli from the environment.

        SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perceptionlayer

        Determinism: Pure function. Same inputs -> same output. No RNG.
        Side Effects: None.
        """
        # Step 1: Compute exposure_score per event
        scored_events: list[tuple[float, int, EnvironmentEvent]] = []
        for idx, event in enumerate(environment_events):
            event_weight = _EVENT_TYPE_WEIGHT.get(event.event_type, 1.0)
            channel_weight = _CHANNEL_WEIGHT.get(event.channel, 1.0)
            affinity = (agent.personality.openness + agent.emotion.interest) / 2.0
            exposure_score = event_weight * channel_weight * affinity
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

        # Step 4: Extract social_signals
        social_signals = []
        for na in neighbor_actions:
            action_weight = ACTION_WEIGHT.get(na.action, 0.0)
            edge_weight = 1.0
            weighted_score = action_weight * edge_weight
            social_signals.append(SocialSignal(
                neighbor_id=na.agent_id,
                action=na.action,
                edge_weight=edge_weight,
                weighted_score=weighted_score,
            ))

        # Step 5: Extract expert_signals from expert_review events
        expert_signals = []
        for event in environment_events:
            if event.event_type == "expert_review":
                expert_signals.append(ExpertSignal(
                    expert_id=event.source_agent_id if event.source_agent_id else event.content_id,
                    opinion_score=0.5,
                    credibility=0.8,
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
