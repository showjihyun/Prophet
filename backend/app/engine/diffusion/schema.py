"""Diffusion engine data types.
SPEC: docs/spec/03_DIFFUSION_SPEC.md
"""
from dataclasses import dataclass, field
from typing import Literal
from uuid import UUID


@dataclass
class RecSysConfig:
    """Configurable recommendation algorithm weights.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용

    Invariant: sum of weights (w_recency + w_social_affinity + w_interest_match
    + w_engagement_signal + w_ad_boost) == 1.0 (±0.01 tolerance).
    Violation: raise ValueError — do not auto-normalize.
    """
    feed_capacity: int = 20
    w_recency: float = 0.2
    w_social_affinity: float = 0.3
    w_interest_match: float = 0.2
    w_engagement_signal: float = 0.2
    w_ad_boost: float = 0.1
    enable_filter_bubble: bool = True
    diversity_penalty: float = 0.05

    def __post_init__(self) -> None:
        weight_sum = (
            self.w_recency
            + self.w_social_affinity
            + self.w_interest_match
            + self.w_engagement_signal
            + self.w_ad_boost
        )
        if abs(weight_sum - 1.0) > 0.01:
            raise ValueError(
                f"RecSysConfig weight sum must be 1.0 (±0.01), got {weight_sum}"
            )


@dataclass
class FeedItem:
    """A single item in an agent's social feed.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용
    """
    source_agent_id: UUID | None
    campaign_id: UUID | None
    feed_rank_score: float
    recency_score: float = 0.0
    social_affinity_score: float = 0.0
    interest_match_score: float = 0.0
    engagement_signal_score: float = 0.0
    ad_boost_score: float = 0.0


@dataclass
class CampaignEvent:
    """A marketing campaign event in the simulation.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#interface-contracts
    """
    campaign_id: UUID
    name: str
    message: str
    channels: list[str]
    novelty: float
    controversy: float
    utility: float
    budget: float
    target_communities: list[UUID]
    start_step: int
    end_step: int


@dataclass
class ExposureResult:
    """Result of exposure computation for a single agent.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#exposuremodel-recsys-inspired-oasis-차용
    """
    agent_id: UUID
    exposure_score: float
    exposed_events: list[CampaignEvent]
    social_feed: list[FeedItem]
    suppressed_count: int
    is_directly_exposed: bool
    feed_diversity_score: float


@dataclass
class ContextualPacket:
    """Text context passed between agents during propagation.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#contextual-packet

    Enables emergent text mutation as messages spread through the network.
    Each agent adds their emotional interpretation before forwarding.
    """
    original_content: str         # Original campaign/event message
    sender_emotion_summary: str   # e.g., "interest=0.8, trust=0.6"
    sender_reasoning: str         # SLM-generated 1-line summary of why they shared
    mutation_depth: int = 0       # How many agents the packet has passed through


@dataclass
class PropagationEvent:
    """A propagation event between two agents.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#propagationmodel
    """
    source_agent_id: UUID
    target_agent_id: UUID
    action_type: str  # AgentAction value
    probability: float
    step: int
    message_id: UUID
    contextual_packet: "ContextualPacket | None" = None
    generated_content: str | None = None  # CG-03: Tier 3 agent-generated post text


@dataclass
class CascadeConfig:
    """Thresholds for emergent behavior detection.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector

    Invariant: all thresholds > 0.
    Violation: raise ValueError.

    Round 8-8 calibration (2026-04-12):
    - ``polarization_variance_threshold``: lowered 0.4 → 0.05. The old
      threshold assumed belief variance on [-1, 1] would routinely
      reach 0.4 (which implies half the community at +1 and half at
      -1). Realistic pilot data shows community belief variance sits
      in the 0.03-0.07 range — the belief update dynamics don't push
      communities to full bimodality. With the old threshold, the
      polarization detector never fired in any pilot. 0.05 is
      ~1 standard deviation above the neutral baseline (0.03) and
      fires cleanly on hostile-framing pilots where real splits form.
    - ``echo_chamber_ratio``: left at 10.0 but documented as not
      currently firing on Prophet's default network topology. The
      default NetworkGenerator (Watts-Strogatz + Barabasi-Albert
      with ``cross_community_prob=0.02``) produces communities with
      internal/external edge ratios of ~0.4-0.6 — the preferential
      attachment creates MORE cross-community bridges than
      intra-community ties. A true echo-chamber detector needs a
      belief-isolation metric (low internal variance + large deviation
      from global mean), not an edge-ratio metric. Tracked as a
      follow-up in docs/USE_CASE_PILOTS.md.
    """
    viral_cascade_threshold: float = 0.15
    slow_adoption_threshold: float = 0.02  # per-step delta below which adoption is "slow"
    slow_adoption_steps: int = 5
    polarization_variance_threshold: float = 0.05
    collapse_drop_rate: float = 0.20
    echo_chamber_ratio: float = 10.0

    def __post_init__(self) -> None:
        if self.viral_cascade_threshold <= 0:
            raise ValueError(
                f"viral_cascade_threshold must be > 0, got {self.viral_cascade_threshold}"
            )
        if self.slow_adoption_threshold <= 0:
            raise ValueError(
                f"slow_adoption_threshold must be > 0, got {self.slow_adoption_threshold}"
            )
        if self.slow_adoption_steps <= 0:
            raise ValueError(
                f"slow_adoption_steps must be > 0, got {self.slow_adoption_steps}"
            )
        if self.polarization_variance_threshold <= 0:
            raise ValueError(
                f"polarization_variance_threshold must be > 0, "
                f"got {self.polarization_variance_threshold}"
            )
        if self.collapse_drop_rate <= 0:
            raise ValueError(
                f"collapse_drop_rate must be > 0, got {self.collapse_drop_rate}"
            )
        if self.echo_chamber_ratio <= 0:
            raise ValueError(
                f"echo_chamber_ratio must be > 0, got {self.echo_chamber_ratio}"
            )


@dataclass
class EmergentEvent:
    """An emergent behavior detected during simulation.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#cascadedetector
    """
    event_type: Literal[
        "viral_cascade", "slow_adoption", "polarization", "collapse", "echo_chamber"
    ]
    step: int
    community_id: UUID | None
    severity: float
    description: str
    affected_agent_ids: list[UUID]


@dataclass
class CommunitySentiment:
    """Sentiment state of a community at a given step.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#sentimentmodel
    """
    community_id: UUID
    mean_belief: float
    sentiment_variance: float
    adoption_rate: float
    step: int


@dataclass
class NegativeEvent:
    """A negative event that can trigger negative cascades.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#negative-cascade-model
    """
    event_type: Literal["bad_review", "controversy", "fake_news", "competitor_attack"]
    content: str
    controversy: float
    source_agent_id: UUID | None
    step: int


@dataclass
class ExpertOpinion:
    """An expert agent's opinion on a campaign.

    SPEC: docs/spec/03_DIFFUSION_SPEC.md#expert-intervention-model
    """
    expert_agent_id: UUID
    score: float
    reasoning: str
    step: int
    affects_communities: list[UUID]
    confidence: float


# --------------------------------------------------------------------------- #
# Monte Carlo aggregates                                                       #
# SPEC: docs/spec/29_MONTE_CARLO_SPEC.md#11-result-dataclasses-mc-eng-01       #
# --------------------------------------------------------------------------- #


@dataclass
class RunSummary:
    """Terminal stats for a single Monte Carlo run.

    SPEC: docs/spec/29_MONTE_CARLO_SPEC.md#11-result-dataclasses-mc-eng-01
    """
    run_id: int
    final_adoption: int
    viral_detected: bool
    steps_completed: int


@dataclass
class MonteCarloResult:
    """Aggregate over N runs of the same SimulationConfig with different seeds.

    SPEC: docs/spec/29_MONTE_CARLO_SPEC.md#11-result-dataclasses-mc-eng-01
    """
    n_runs: int
    viral_probability: float
    expected_reach: float
    p5_reach: float
    p50_reach: float
    p95_reach: float
    community_adoption: dict[str, float] = field(default_factory=dict)
    run_summaries: list[RunSummary] = field(default_factory=list)


__all__ = [
    "RecSysConfig",
    "FeedItem",
    "CampaignEvent",
    "ExposureResult",
    "ContextualPacket",
    "PropagationEvent",
    "CascadeConfig",
    "EmergentEvent",
    "CommunitySentiment",
    "NegativeEvent",
    "ExpertOpinion",
    "RunSummary",
    "MonteCarloResult",
]
