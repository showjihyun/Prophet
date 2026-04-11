"""Agent data types.
SPEC: docs/spec/01_AGENT_SPEC.md#data-schema
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal
from uuid import UUID


@dataclass(frozen=True)
class AgentPersonality:
    """5-dimensional personality vector. All fields in [0.0, 1.0].

    SPEC: docs/spec/01_AGENT_SPEC.md#data-schema

    Invariant: 0.0 <= field <= 1.0 for all fields.
    Violation: raise ValueError at construction time.
    """
    openness: float
    skepticism: float
    trend_following: float
    brand_loyalty: float
    social_influence: float

    def __post_init__(self):
        for f in ['openness', 'skepticism', 'trend_following', 'brand_loyalty', 'social_influence']:
            v = getattr(self, f)
            if not (0.0 <= v <= 1.0):
                raise ValueError(f"AgentPersonality.{f} must be in [0.0, 1.0], got {v}")

    def as_vector(self) -> list[float]:
        """Returns [openness, skepticism, trend_following, brand_loyalty, social_influence].

        SPEC: docs/spec/01_AGENT_SPEC.md#data-schema
        """
        return [self.openness, self.skepticism, self.trend_following,
                self.brand_loyalty, self.social_influence]


@dataclass
class AgentEmotion:
    """4-dimensional emotion state. All fields in [0.0, 1.0].

    SPEC: docs/spec/01_AGENT_SPEC.md#data-schema

    Invariant: 0.0 <= field <= 1.0 for all fields.
    Violation: clamp to [0.0, 1.0] with WARNING log (not exception).
    """
    interest: float
    trust: float
    skepticism: float
    excitement: float

    def clamped(self) -> 'AgentEmotion':
        """Returns a new AgentEmotion with all fields clamped to [0.0, 1.0].

        SPEC: docs/spec/01_AGENT_SPEC.md#data-schema
        """
        return AgentEmotion(
            interest=max(0.0, min(1.0, self.interest)),
            trust=max(0.0, min(1.0, self.trust)),
            skepticism=max(0.0, min(1.0, self.skepticism)),
            excitement=max(0.0, min(1.0, self.excitement)),
        )


class AgentType(str, Enum):
    """SPEC: docs/spec/01_AGENT_SPEC.md#data-schema"""
    CONSUMER = "consumer"
    EARLY_ADOPTER = "early_adopter"
    SKEPTIC = "skeptic"
    INFLUENCER = "influencer"
    EXPERT = "expert"


class DiffusionState(str, Enum):
    """SIR-inspired diffusion state for information spread.
    SPEC: docs/spec/19_SIMULATION_INTEGRITY_SPEC.md#3.1
    """
    SUSCEPTIBLE = "susceptible"
    EXPOSED = "exposed"
    INTERESTED = "interested"
    ADOPTED = "adopted"
    RECOVERED = "recovered"
    RESISTANT = "resistant"


class AgentAction(str, Enum):
    """SPEC: docs/spec/01_AGENT_SPEC.md#agent-action-enum"""
    # Passive
    IGNORE = "ignore"
    VIEW = "view"
    SEARCH = "search"
    # Positive Engagement
    LIKE = "like"
    SAVE = "save"
    COMMENT = "comment"
    SHARE = "share"
    REPOST = "repost"
    # Relationship
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    # Conversion
    ADOPT = "adopt"
    # Negative
    MUTE = "mute"


# SPEC: docs/spec/01_AGENT_SPEC.md#action-weight-table
ACTION_WEIGHT: dict[AgentAction, float] = {
    AgentAction.IGNORE:   0.0,
    AgentAction.VIEW:     0.1,
    AgentAction.SEARCH:   0.2,
    AgentAction.LIKE:     0.3,
    AgentAction.SAVE:     0.4,
    AgentAction.COMMENT:  0.6,
    AgentAction.SHARE:    0.8,
    AgentAction.REPOST:   0.7,
    AgentAction.FOLLOW:   0.5,
    AgentAction.UNFOLLOW: -0.3,
    AgentAction.ADOPT:    1.0,
    AgentAction.MUTE:     -0.5,
}


@dataclass
class AgentState:
    """Full mutable state of an agent at a given simulation step.

    SPEC: docs/spec/01_AGENT_SPEC.md#data-schema

    Invariants:
      - belief in [-1.0, 1.0]
      - exposure_count >= 0
      - step >= 0
      - llm_tier_used in {None, 1, 2, 3}
      - len(activity_vector) == 24
      - each activity_vector[i] in [0.0, 1.0]
    """
    agent_id: UUID
    simulation_id: UUID
    agent_type: AgentType
    step: int
    personality: AgentPersonality
    emotion: AgentEmotion
    belief: float
    action: AgentAction
    exposure_count: int
    adopted: bool
    community_id: UUID
    influence_score: float
    llm_tier_used: int | None
    activity_vector: list[float] = field(default_factory=lambda: [0.5] * 24)
    cumulative_drift: dict[str, float] = field(default_factory=dict)
    diffusion_state: DiffusionState = DiffusionState.SUSCEPTIBLE
    last_reflection_step: int = -1  # RF-01: step when agent last reflected


__all__ = [
    "AgentPersonality",
    "AgentEmotion",
    "AgentType",
    "AgentAction",
    "ACTION_WEIGHT",
    "AgentState",
    "DiffusionState",
]
