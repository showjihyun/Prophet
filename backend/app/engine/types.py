"""Shared data types across engine modules.
SPEC: docs/spec/01_AGENT_SPEC.md, 02_NETWORK_SPEC.md, 03_DIFFUSION_SPEC.md

Agent-specific types (AgentAction, AgentPersonality, AgentEmotion) are canonical
in app.engine.agent.schema and re-exported here for convenience.
"""
from dataclasses import dataclass
from enum import Enum
from uuid import UUID

# Re-export canonical agent types from schema
from app.engine.agent.schema import AgentAction, AgentPersonality, AgentEmotion  # noqa: F401


class SimulationStatus(str, Enum):
    """SPEC: docs/spec/04_SIMULATION_SPEC.md#simulation-lifecycle"""
    CREATED = "created"
    CONFIGURED = "configured"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


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
