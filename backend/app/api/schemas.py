"""Pydantic request/response models for Prophet API.
SPEC: docs/spec/06_API_SPEC.md
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


# --- Enums ---

class SimulationStatus(str, Enum):
    """SPEC: docs/spec/06_API_SPEC.md#2-simulation-endpoints"""
    CONFIGURED = "configured"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class NetworkFormat(str, Enum):
    """SPEC: docs/spec/06_API_SPEC.md#4-network-endpoints"""
    CYTOSCAPE = "cytoscape"
    D3 = "d3"
    RAW = "raw"


# --- Campaign ---

class CampaignInput(BaseModel):
    """Campaign configuration.
    SPEC: docs/spec/06_API_SPEC.md#post-simulations
    """
    name: str
    budget: float = 0.0
    channels: list[str]
    message: str
    target_communities: list[str] = Field(default_factory=lambda: ["all"])
    controversy: float = Field(ge=0.0, le=1.0, default=0.1)
    novelty: float = Field(ge=0.0, le=1.0, default=0.5)
    utility: float = Field(ge=0.0, le=1.0, default=0.5)


# --- Simulation Requests ---

class CreateSimulationRequest(BaseModel):
    """Create simulation request body.
    SPEC: docs/spec/06_API_SPEC.md#post-simulations
    """
    name: str
    description: str = ""
    campaign: CampaignInput
    communities: list[dict[str, Any]] | None = None
    max_steps: int = Field(default=50, ge=1, le=1000)
    default_llm_provider: str = "ollama"
    random_seed: int | None = None
    slm_llm_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    slm_model: str = "phi4"
    budget_usd: float = Field(default=10.0, ge=0.0)
    platform: str = "default"


class InjectEventRequest(BaseModel):
    """Inject external event mid-simulation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idinject-event
    """
    event_type: str
    content: str
    controversy: float = Field(ge=0.0, le=1.0, default=0.5)
    target_communities: list[str] = Field(default_factory=list)


class EngineControlRequest(BaseModel):
    """Adjust SLM/LLM ratio at runtime.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idengine-control
    """
    slm_llm_ratio: float = Field(ge=0.0, le=1.0)
    slm_model: str = "phi4"
    budget_usd: float = Field(ge=0.0, default=50.0)


class RecommendEngineRequest(BaseModel):
    """Budget-based auto engine recommendation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationsrecommend-engine
    """
    agent_count: int = Field(ge=1)
    budget_usd: float = Field(ge=0.0)
    max_steps: int = Field(ge=1, default=50)


class MonteCarloRequest(BaseModel):
    """Monte Carlo analysis request.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idmonte-carlo
    """
    n_runs: int = Field(ge=1, default=100)
    llm_enabled: bool = False


class AgentPatchRequest(BaseModel):
    """Patch agent state (simulation must be PAUSED).
    SPEC: docs/spec/06_API_SPEC.md#patch-simulationssimulation_idagentsagent_id
    """
    personality: dict[str, float] | None = None
    emotion: dict[str, float] | None = None
    belief: float | None = Field(default=None, ge=-1.0, le=1.0)


# --- Simulation Responses ---

class NetworkMetricsData(BaseModel):
    """Network metrics summary."""
    clustering_coefficient: float = 0.0
    avg_path_length: float = 0.0


class SimulationResponse(BaseModel):
    """Response after creating a simulation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulations
    """
    simulation_id: str
    status: SimulationStatus
    total_agents: int = 0
    network_metrics: NetworkMetricsData = Field(default_factory=NetworkMetricsData)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SimulationDetailResponse(BaseModel):
    """Full simulation details.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_id
    """
    simulation_id: str
    name: str
    description: str = ""
    status: SimulationStatus
    current_step: int = 0
    max_steps: int = 50
    total_agents: int = 0
    network_metrics: NetworkMetricsData = Field(default_factory=NetworkMetricsData)
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StatusResponse(BaseModel):
    """Generic status change response."""
    status: SimulationStatus
    current_step: int | None = None
    started_at: datetime | None = None


class StepResultResponse(BaseModel):
    """Result of a single simulation step.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idstep
    """
    step: int = 0
    adoption_rate: float = 0.0
    mean_sentiment: float = 0.0
    sentiment_variance: float = 0.0
    diffusion_rate: int = 0
    total_adoption: int = 0
    community_metrics: dict[str, Any] = Field(default_factory=dict)
    action_distribution: dict[str, int] = Field(default_factory=dict)
    propagation_pairs: list[dict[str, Any]] = Field(default_factory=list)
    llm_calls_this_step: int = 0
    step_duration_ms: float = 0.0
    emergent_events: list[dict[str, Any]] = Field(default_factory=list)


class StepHistoryResponse(BaseModel):
    """Step history list.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idsteps
    """
    steps: list[StepResultResponse] = Field(default_factory=list)


class InjectEventResponse(BaseModel):
    """Response after injecting event.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idinject-event
    """
    event_id: str
    effective_step: int


class ReplayResponse(BaseModel):
    """Response after replaying from a step.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idreplaystep
    """
    replay_id: str
    from_step: int


class ScenarioComparisonResponse(BaseModel):
    """Compare two simulation runs.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idcompareother_simulation_id
    """
    simulation_a: str
    simulation_b: str
    comparison: dict[str, Any] = Field(default_factory=dict)


# --- Monte Carlo ---

class MonteCarloStatusResponse(BaseModel):
    """Monte Carlo job status/results.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idmonte-carlojob_id
    """
    job_id: str
    status: str
    n_runs: int = 0
    completed_runs: int | None = None
    viral_probability: float | None = None
    expected_reach: int | None = None
    p5_reach: int | None = None
    p50_reach: int | None = None
    p95_reach: int | None = None
    community_adoption: dict[str, float] | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


# --- Engine Control ---

class TierDistribution(BaseModel):
    """Tier distribution info."""
    tier1_count: int = 0
    tier2_count: int = 0
    tier3_count: int = 0
    estimated_cost_per_step: float | None = None
    estimated_latency_ms: float | None = None


class ImpactAssessment(BaseModel):
    """Impact assessment for engine config."""
    cost_efficiency: str = ""
    reasoning_depth: str = ""
    simulation_velocity: str = ""
    prediction_type: str = ""


class EngineControlResponse(BaseModel):
    """Response after adjusting engine control.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idengine-control
    """
    tier_distribution: TierDistribution = Field(default_factory=TierDistribution)
    impact_assessment: ImpactAssessment = Field(default_factory=ImpactAssessment)


class RecommendEngineResponse(BaseModel):
    """Budget-based engine recommendation.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationsrecommend-engine
    """
    recommended_ratio: float = 0.0
    recommended_slm_model: str = ""
    tier_distribution: TierDistribution = Field(default_factory=TierDistribution)
    estimated_total_cost: float = 0.0
    estimated_total_time: str = ""
    mode: str = ""


class RunAllResponse(BaseModel):
    """Response after running all remaining steps to completion.
    SPEC: docs/spec/06_API_SPEC.md#post-simulationssimulation_idrun-all
    """
    simulation_id: str
    status: str
    total_steps: int
    final_adoption_rate: float
    final_mean_sentiment: float
    community_summary: list[dict]
    emergent_events_count: int
    duration_ms: float


# --- Agent Responses ---

class AgentSummaryResponse(BaseModel):
    """Agent summary in listing.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagents
    """
    agent_id: str
    community_id: str = ""
    agent_type: str = ""
    action: str = "idle"
    adopted: bool = False
    influence_score: float = 0.0
    belief: float = 0.0


class AgentDetailResponse(BaseModel):
    """Full agent detail.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagentsagent_id
    """
    agent_id: str
    community_id: str = ""
    agent_type: str = ""
    action: str = "idle"
    adopted: bool = False
    influence_score: float = 0.0
    belief: float = 0.0
    personality: dict[str, float] = Field(default_factory=dict)
    emotion: dict[str, float] = Field(default_factory=dict)
    memories: list[dict[str, Any]] = Field(default_factory=list)


class MemoryRecordResponse(BaseModel):
    """Agent memory records.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idagentsagent_idmemory
    """
    memories: list[dict[str, Any]] = Field(default_factory=list)


# --- Network ---

class CytoscapeNode(BaseModel):
    """Cytoscape node format."""
    data: dict[str, Any]


class CytoscapeEdge(BaseModel):
    """Cytoscape edge format."""
    data: dict[str, Any]


class NetworkGraphResponse(BaseModel):
    """Network graph in Cytoscape format.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idnetwork
    """
    nodes: list[CytoscapeNode] = Field(default_factory=list)
    edges: list[CytoscapeEdge] = Field(default_factory=list)


class NetworkMetricsResponse(BaseModel):
    """Network metrics.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idnetworkmetrics
    """
    clustering_coefficient: float = 0.0
    avg_path_length: float = 0.0
    modularity: float = 0.0
    density: float = 0.0
    total_nodes: int = 0
    total_edges: int = 0


# --- Community ---

class CommunityResponse(BaseModel):
    """Community info.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idcommunities
    """
    community_id: str
    name: str = ""
    size: int = 0
    adoption_rate: float = 0.0
    mean_belief: float = 0.0
    sentiment_variance: float = 0.0
    dominant_action: str = "idle"


class CommunitiesListResponse(BaseModel):
    """Community list response."""
    communities: list[CommunityResponse] = Field(default_factory=list)


# --- LLM Dashboard ---

class LLMStatsResponse(BaseModel):
    """LLM usage statistics.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idllmstats
    """
    total_calls: int = 0
    cached_calls: int = 0
    provider_breakdown: dict[str, int] = Field(default_factory=dict)
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    tier_breakdown: dict[str, int] = Field(default_factory=dict)


class LLMCallLogEntry(BaseModel):
    """Single LLM call log entry."""
    call_id: str = ""
    step: int = 0
    agent_id: str = ""
    provider: str = ""
    latency_ms: float = 0.0
    tokens: int = 0
    cached: bool = False


class LLMCallsResponse(BaseModel):
    """LLM call log response.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idllmcalls
    """
    calls: list[LLMCallLogEntry] = Field(default_factory=list)


class LLMImpactResponse(BaseModel):
    """LLM impact assessment.
    SPEC: docs/spec/06_API_SPEC.md#get-simulationssimulation_idllmimpact
    """
    slm_llm_ratio: float = 0.0
    tier_distribution: dict[str, int] = Field(default_factory=dict)
    impact: ImpactAssessment = Field(default_factory=ImpactAssessment)
    slm_model: str = ""
    slm_batch_throughput: str = ""


# --- Paginated ---

class PaginatedResponse(BaseModel):
    """Generic paginated response.
    SPEC: docs/spec/06_API_SPEC.md#2-simulation-endpoints
    """
    items: list[Any] = Field(default_factory=list)
    total: int = 0


# --- Project / Scenario ---

class CreateProjectRequest(BaseModel):
    """Create project request.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    name: str
    description: str = ""


class ProjectResponse(BaseModel):
    """Project summary response.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    project_id: str
    name: str
    description: str = ""
    status: str = "active"
    scenario_count: int = 0
    created_at: datetime | None = None


class ScenarioResponse(BaseModel):
    """Scenario response.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    scenario_id: str
    name: str
    description: str = ""
    status: str = "draft"
    simulation_id: str | None = None
    config: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class ProjectDetailResponse(BaseModel):
    """Project detail with scenarios.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    project_id: str
    name: str
    description: str = ""
    status: str = "active"
    scenarios: list[ScenarioResponse] = Field(default_factory=list)
    created_at: datetime | None = None


class UpdateProjectRequest(BaseModel):
    """Update project request (PATCH).
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    name: str | None = None
    description: str | None = None


class CreateScenarioRequest(BaseModel):
    """Create scenario request.
    SPEC: docs/spec/06_API_SPEC.md#9-project-scenario-endpoints
    """
    name: str
    description: str = ""
    config: dict[str, Any] = Field(default_factory=dict)


# --- Conversation Threads ---

class ThreadSummary(BaseModel):
    """Thread summary in listing.
    SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
    """
    thread_id: str
    topic: str
    participant_count: int
    message_count: int
    avg_sentiment: float


class ThreadMessage(BaseModel):
    """Single message in a conversation thread.
    SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
    """
    message_id: str
    agent_id: str
    community_id: str
    stance: str  # "Progressive", "Conservative", "Neutral"
    content: str
    reactions: dict[str, int]  # agree, disagree, nuanced
    is_reply: bool
    reply_to_id: str | None = None


class ThreadsListResponse(BaseModel):
    """Response for listing threads.
    SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
    """
    threads: list[ThreadSummary] = Field(default_factory=list)


class ThreadDetailResponse(BaseModel):
    """Full thread detail with messages.
    SPEC: docs/spec/06_API_SPEC.md#5-community-endpoints
    """
    thread_id: str
    topic: str
    participant_count: int
    message_count: int
    avg_sentiment: float
    messages: list[ThreadMessage] = Field(default_factory=list)


# --- Error ---

class ErrorResponse(BaseModel):
    """RFC 7807 Problem Details error response.
    SPEC: docs/spec/06_API_SPEC.md#8-error-response-format
    """
    type: str = "https://prophet.io/errors/unknown"
    title: str = "Error"
    status: int = 500
    detail: str = ""
    instance: str = ""
