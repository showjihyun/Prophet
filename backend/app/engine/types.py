"""Shared data types across engine modules.
SPEC: docs/spec/01_AGENT_SPEC.md, 02_NETWORK_SPEC.md, 03_DIFFUSION_SPEC.md
"""
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID


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


class SimulationStatus(str, Enum):
    """SPEC: docs/spec/04_SIMULATION_SPEC.md#simulation-lifecycle"""
    CREATED = "created"
    CONFIGURED = "configured"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentPersonality:
    """SPEC: docs/spec/01_AGENT_SPEC.md#data-schema"""
    openness: float = 0.5
    skepticism: float = 0.5
    trend_following: float = 0.5
    brand_loyalty: float = 0.5
    social_influence: float = 0.5


@dataclass
class AgentEmotion:
    """SPEC: docs/spec/01_AGENT_SPEC.md#data-schema"""
    interest: float = 0.5
    trust: float = 0.5
    skepticism: float = 0.5
    excitement: float = 0.3


@dataclass
class MessageStrength:
    """SPEC: docs/spec/01_AGENT_SPEC.md#layer-6-influence"""
    novelty: float = 0.5
    controversy: float = 0.0
    utility: float = 0.5

    @property
    def score(self) -> float:
        return (self.novelty + self.controversy + self.utility) / 3.0


@dataclass
class ContextualPacket:
    """SPEC: docs/spec/01_AGENT_SPEC.md#contextual-packet"""
    source_agent_id: UUID
    source_emotion: AgentEmotion
    source_summary: str
    message_strength: MessageStrength
    sentiment_polarity: float
    action_taken: AgentAction
    step: int
