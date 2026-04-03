"""Simulation data types.
SPEC: docs/spec/04_SIMULATION_SPEC.md#§3-5
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import UUID, uuid4

from app.engine.agent.schema import AgentAction, AgentEmotion, AgentPersonality, AgentState
from app.engine.diffusion.schema import EmergentEvent, RecSysConfig
from app.engine.network.schema import CommunityConfig, NetworkConfig


class SimulationStatus(str, Enum):
    """SPEC: docs/spec/04_SIMULATION_SPEC.md#simulation-lifecycle"""
    CREATED = "created"
    CONFIGURED = "configured"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class CampaignConfig:
    """Campaign configuration for a simulation.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationconfig
    """
    name: str = "default_campaign"
    budget: float = 1000.0
    channels: list[str] = field(
        default_factory=lambda: ["sns"]
    )
    message: str = "Default campaign message"
    target_communities: list[str] = field(
        default_factory=lambda: ["all"]
    )
    start_step: int = 0
    end_step: int | None = None
    controversy: float = 0.0
    novelty: float = 0.5
    utility: float = 0.5


@dataclass
class TemporalConfig:
    """Variable-duration time model (OASIS-inspired).
    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationconfig
    """
    enable_activity_vector: bool = True
    min_step_hours: float = 0.08
    max_step_hours: float = 4.0
    base_step_hours: float = 1.0
    event_density_threshold: float = 0.3
    cascade_zoom_factor: float = 0.25


@dataclass
class SimulationConfig:
    """Top-level simulation configuration.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationconfig
    """
    simulation_id: UUID = field(default_factory=uuid4)
    name: str = "Unnamed Simulation"
    description: str = ""

    # Population
    communities: list[CommunityConfig] = field(default_factory=list)

    # Campaign
    campaign: CampaignConfig = field(default_factory=CampaignConfig)

    # Network
    network_config: NetworkConfig = field(default_factory=NetworkConfig)

    # Execution
    max_steps: int = 50
    step_delay_ms: int = 0
    enable_personality_drift: bool = True
    enable_dynamic_edges: bool = True

    # Temporal
    temporal_mode: Literal["fixed", "variable"] = "fixed"
    fixed_step_hours: float = 1.0
    temporal_config: TemporalConfig | None = None

    # Platform & RecSys
    platform: str = "default"
    recsys_config: RecSysConfig | None = None

    # LLM
    default_llm_provider: str = "ollama"
    llm_tier3_ratio: float = 0.10
    slm_llm_ratio: float = 0.5
    slm_model: str = "phi4"
    budget_usd: float | None = None

    # Monte Carlo
    monte_carlo_runs: int = 0
    monte_carlo_llm_enabled: bool = False

    # Seeding
    random_seed: int | None = None


@dataclass
class AgentModification:
    """Real-time intervention to modify an agent.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
    """
    personality: AgentPersonality | None = None
    emotion: AgentEmotion | None = None
    community_id: UUID | None = None
    llm_provider: str | None = None
    belief: float | None = None


@dataclass
class CommunityStepMetrics:
    """Per-community metrics for a single step.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#stepresult
    """
    community_id: UUID
    adoption_count: int
    adoption_rate: float
    mean_belief: float
    dominant_action: AgentAction
    new_propagation_count: int


@dataclass
class StepResult:
    """Result of a single simulation step.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#stepresult
    """
    simulation_id: UUID
    step: int
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Aggregate metrics
    total_adoption: int = 0
    adoption_rate: float = 0.0
    diffusion_rate: float = 0.0
    mean_sentiment: float = 0.0
    sentiment_variance: float = 0.0

    # Per-community
    community_metrics: dict[str, CommunityStepMetrics] = field(default_factory=dict)

    # Emergent behaviors
    emergent_events: list[EmergentEvent] = field(default_factory=list)

    # Agent summary
    action_distribution: dict[str, int] = field(default_factory=dict)

    # LLM usage
    llm_calls_this_step: int = 0
    llm_tier_distribution: dict[int, int] = field(default_factory=dict)

    # Performance
    step_duration_ms: float = 0.0


@dataclass
class ScenarioComparison:
    """Comparison result of two simulation runs.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#scenario-comparison-f23
    """
    sim_a: UUID
    sim_b: UUID
    metric_diffs: dict[str, list[float]]
    final_adoption_diff: float
    emergent_event_diff: list[str]
    winner: UUID | None
    summary: str


@dataclass
class SimulationRun:
    """Handle returned by create_simulation().
    SPEC: docs/spec/04_SIMULATION_SPEC.md#simulationorchestrator-interface
    """
    simulation_id: UUID
    status: str
    current_step: int = 0
    config: SimulationConfig | None = None


__all__ = [
    "SimulationStatus",
    "SimulationConfig",
    "CampaignConfig",
    "TemporalConfig",
    "AgentModification",
    "CommunityStepMetrics",
    "StepResult",
    "ScenarioComparison",
    "SimulationRun",
]
