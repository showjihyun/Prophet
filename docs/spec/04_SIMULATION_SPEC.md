# 04 — Simulation Orchestrator SPEC
Version: 0.2.0 | Status: REVIEW

---

## 1. Overview

The SimulationOrchestrator is the top-level coordinator that manages simulation lifecycle, step execution, real-time intervention, and metric collection.

### Execution Model

- **Step loop:** `asyncio.Task` (NOT Celery). Steps run as async coroutines within the FastAPI event loop.
- **Monte Carlo:** `asyncio.create_task` (in-process). Celery + Valkey integration planned for Scale Phase.
- **Run-All:** `run_all()` runs all remaining steps in a loop and returns a summary report (synchronous completion).
- **Rationale:** Step execution requires real-time WebSocket feedback (asyncio-native). Monte Carlo currently in-process for simplicity.
- **Concurrency:** Max 3 simultaneous simulation step-loops per API server (`_MAX_CONCURRENT = 3`). Max 50 total in-memory simulations (`MAX_SIMULATIONS = 50`, TTL 86400s).
- **Failure:** If step loop crashes, status → FAILED. Client can resume from last persisted step.

---

## 2. Simulation Lifecycle

```
CREATE → CONFIGURED → RUNNING → PAUSED ↔ RUNNING → COMPLETED
                                    ↓
                                 MODIFIED → RUNNING
                                    ↓
                                  FAILED
```

```python
class SimulationStatus(str, Enum):
    CREATED    = "created"
    CONFIGURED = "configured"
    RUNNING    = "running"
    PAUSED     = "paused"
    COMPLETED  = "completed"
    FAILED     = "failed"
```

---

## 3. SimulationConfig

```python
@dataclass
class SimulationConfig:
    simulation_id: UUID
    name: str
    description: str

    # Population
    communities: list[CommunityConfig]        # default: 5 communities, 1000 agents

    # Campaign
    campaign: CampaignConfig

    # Network
    network_config: NetworkConfig

    # Execution
    max_steps: int = 50
    step_delay_ms: int = 0               # 0 = as fast as possible
    enable_personality_drift: bool = True
    enable_dynamic_edges: bool = True

    # Temporal Model (OASIS-inspired)
    temporal_mode: Literal["fixed", "variable"] = "fixed"
    fixed_step_hours: float = 1.0        # "fixed" mode: 1 step = N hours of simulated time
    # "variable" mode: step duration depends on event density (see TemporalConfig)
    temporal_config: TemporalConfig | None = None

    # RecSys
    recsys_config: RecSysConfig | None = None  # None = default RecSys weights

    # LLM
    default_llm_provider: str = "ollama"  # "ollama" | "claude" | "openai"
    llm_tier3_ratio: float = 0.10        # max % agents using LLM per step
    slm_llm_ratio: float = 0.5          # 0.0=all SLM, 1.0=max LLM (user slider)
    slm_model: str = "phi4"             # "phi4" | "llama3.2:8b-q4" | "gemma2:2b"
    budget_usd: float | None = None     # if set, auto-adjusts slm_llm_ratio to fit budget

    # Platform
    platform: str | None = None          # Optional platform plugin identifier

    # Monte Carlo
    monte_carlo_runs: int = 0            # 0 = disabled
    monte_carlo_llm_enabled: bool = False

    # Seeding
    random_seed: int | None = None

@dataclass
class CampaignConfig:
    name: str
    budget: float
    channels: list[Literal["sns", "influencer", "online_ads", "tv", "email"]]
    message: str
    target_communities: list[str]        # community IDs or ["all"]
    start_step: int = 0
    end_step: int | None = None          # None = runs entire simulation
    controversy: float = 0.0            # 0–1, affects negative cascade risk
    novelty: float = 0.5
    utility: float = 0.5

@dataclass
class TemporalConfig:
    """
    Variable-duration time model (OASIS-inspired).

    Instead of fixed-tick steps, each step's simulated duration adapts
    based on event density. High-activity periods (viral cascade) use
    shorter time slices for finer resolution; quiet periods use longer
    slices for efficiency.

    This enables realistic timeline analysis:
        t=0h  campaign launch (1h steps)
        t=3h  influencer share detected → switch to 15min steps
        t=6h  viral peak → 5min steps
        t=12h activity declines → back to 1h steps
    """
    # 24-hour Activity Vector (OASIS-inspired)
    enable_activity_vector: bool = True  # agents have per-hour activity probability
    # When enabled, agents are only active during their probable hours
    # Inactive agents skip their tick (no SLM call) → further cost savings

    min_step_hours: float = 0.08     # ~5 minutes (finest resolution)
    max_step_hours: float = 4.0      # 4 hours (coarsest resolution)
    base_step_hours: float = 1.0     # default step duration
    event_density_threshold: float = 0.3  # above this → shorten steps
    cascade_zoom_factor: float = 0.25     # multiply step duration during cascade
```

---

## 4. SimulationOrchestrator Interface

```python
class SimulationOrchestrator:
    async def create_simulation(
        self,
        config: SimulationConfig,
    ) -> SimulationRun:
        """
        1. Persist SimulationRun to PostgreSQL
        2. Generate agent population
        3. Generate SocialNetwork
        4. Assign agents to communities
        5. Initialize agent states (personality, emotion from distribution)
        6. Status → CONFIGURED
        """

    async def start(self, simulation_id: UUID) -> None:
        """
        Status → RUNNING
        Begins step loop in background (asyncio task).
        """

    # Concurrency Control:
    #     Each simulation has a dedicated `asyncio.Lock`. The lock is acquired
    #     for the entire duration of `run_step()`, `pause()`, `resume()`, and
    #     `modify_agent()`. This prevents race conditions from concurrent
    #     API requests or WebSocket commands targeting the same simulation.
    #
    #     ```python
    #     self._locks: dict[UUID, asyncio.Lock] = {}
    #     ```

    async def run_step(
        self,
        simulation_id: UUID,
    ) -> StepResult:
        """
        Execute one simulation step using **Community-level Orchestration**.

        현실 SNS에서 정보는 커뮤니티 내부에서 먼저 순환한 후 외부로 전파된다.
        이를 반영하여 step 실행을 3-Phase로 분리한다.

        Phase 1 — Intra-Community (병렬):
            각 CommunityOrchestrator가 자기 커뮤니티의 agent들만 처리.
            asyncio.gather로 5개 커뮤니티 동시 실행.

            ```python
            community_results = await asyncio.gather(*[
                community_orch.tick(step, campaign_events)
                for community_orch in self._community_orchestrators.values()
            ])
            ```

            각 CommunityOrchestrator.tick():
                1a. ExposureModel — 커뮤니티 내부 agent만 대상
                1b. AgentTick — 커뮤니티 소속 agent만 tick
                1c. Intra-community propagation — 커뮤니티 내부 엣지만 사용
                1d. Community sentiment — 커뮤니티별 mean_belief, variance 계산
                1e. Community-level tier allocation — 커뮤니티별 SLM/LLM 비율 적용

        Phase 2 — Cross-Community (순차):
            커뮤니티 간 bridge 엣지를 통한 전파.
            Phase 1에서 SHARE/REPOST/COMMENT 한 agent의 콘텐츠가
            bridge edge를 통해 다른 커뮤니티로 전달됨.

            ```python
            cross_events = self._bridge_propagator.propagate(
                community_results, bridge_edges
            )
            ```

        Phase 3 — Global Aggregation (순차):
            1. 전체 agent 결과 merge
            2. CascadeDetector.detect() — 글로벌 emergent behavior
            3. NetworkEvolver.evolve_step() — edge weight 업데이트
            4. MetricCollector.record() — 전체 + 커뮤니티별 메트릭
            5. WebSocket.broadcast(step_summary)

        Note: All engine calls receive an `agent_node_map: dict[UUID, int]`
        mapping agent UUIDs to NetworkX integer node IDs. This map is built
        once per step from `SocialNetwork.graph.nodes(data='agent_id')` and
        passed to ExposureModel, PropagationModel, and NetworkEvolver to
        avoid O(N) graph scans per agent.

        Returns StepResult.
        Increments simulation.current_step.
        """

```

### CommunityOrchestrator (NEW)

```python
class CommunityOrchestrator:
    """Manages agent execution within a single community.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#communityorchestrator

    Each community has its own orchestrator that:
    - Holds references to only its community's agents
    - Uses only intra-community network edges for propagation
    - Computes community-local sentiment independently
    - Applies community-specific tier allocation
    """

    def __init__(
        self,
        community_id: UUID,
        community_config: CommunityConfig,
        agents: list[AgentState],
        subgraph: nx.Graph,            # intra-community edges only
        agent_node_map: dict[UUID, int],
        bridge_node_ids: set[int] | None = None,  # inter-community bridge nodes
        gateway: "LLMGateway | None" = None,       # LLM gateway for tier-based calls
    ): ...

    async def tick(
        self,
        step: int,
        campaign_events: list[CampaignEvent],
        recsys_config: RecSysConfig | None = None,
        env_events: list[EnvironmentEvent] | None = None,  # injected events
    ) -> CommunityTickResult:
        """
        Execute one step for this community's agents.

        Steps:
            1. ExposureModel.compute_exposure(self.agents, self.subgraph, events)
            2. TierSelector.assign_tiers(self.agents, max_ratio)
            3. for agent in self.agents: AgentTick.tick(agent, ...)
            4. Intra-community PropagationModel (self.subgraph edges only)
            5. SentimentModel.update_community_sentiment(self.community_id, ...)

        Returns CommunityTickResult with:
            - updated_agents: list[AgentState]
            - propagation_events: list[PropagationEvent]
            - community_sentiment: CommunitySentiment
            - outbound_events: list[PropagationEvent]  # events targeting bridge edges
        """

@dataclass
class CommunityTickResult:
    community_id: UUID
    updated_agents: list[AgentState]
    propagation_events: list[PropagationEvent]  # intra-community only
    outbound_events: list[PropagationEvent]     # targeting other communities via bridges
    community_sentiment: CommunitySentiment
    action_distribution: dict[str, int]
    llm_calls: int
    tick_duration_ms: float
```

### BridgePropagator (NEW)

```python
class BridgePropagator:
    """Handles cross-community propagation via bridge edges.
    SPEC: docs/spec/04_SIMULATION_SPEC.md#bridgepropagator

    Phase 2 of the 3-Phase step execution.
    Takes outbound events from each community and delivers them
    to target agents in other communities.
    """

    def propagate(
        self,
        community_results: list[CommunityTickResult],
        bridge_edges: list[tuple[int, int]],
        full_graph: nx.Graph,
    ) -> list[PropagationEvent]:
        """
        For each outbound_event from CommunityTickResult:
            If target_agent is in a different community:
                Apply cross-community propagation probability
                (reduced by bridge_trust_factor = 0.6)

        Returns cross-community PropagationEvents to be applied in Phase 3.
        """
```

```python
    async def pause(self, simulation_id: UUID) -> None:
        """Status → PAUSED. Current step completes before pausing."""

    async def resume(self, simulation_id: UUID) -> None:
        """Status → RUNNING. Continues from current_step."""

    async def run_all(self, simulation_id: UUID) -> RunAllReport:
        """
        Run all remaining steps to completion synchronously.
        Returns summary report with final metrics.
        """

    async def modify_agent(
        self,
        simulation_id: UUID,
        agent_id: UUID,
        modifications: AgentModification,
    ) -> AgentState:
        """
        Real-time intervention: modify agent while simulation is PAUSED.
        Allowed fields: personality, emotion, community_id, llm_provider.
        Change is persisted and takes effect on next step.
        Triggers MODIFIED event in audit log.
        """

    async def inject_event(
        self,
        simulation_id: UUID,
        event: EnvironmentEvent,
    ) -> None:
        """
        Inject an external event mid-simulation (e.g., negative PR, competitor attack).
        Takes effect on next step.
        """

    async def replay_step(
        self,
        simulation_id: UUID,
        target_step: int,
    ) -> StepResult:
        """
        Re-runs from target_step using stored agent_states at that step.
        Does NOT overwrite original run history.
        Creates a branch (replay_id) in the database.
        """

@dataclass
class AgentModification:
    personality: AgentPersonality | None = None
    emotion: AgentEmotion | None = None
    community_id: UUID | None = None
    llm_provider: str | None = None
    belief: float | None = None
```

---

## 5. StepResult

```python
@dataclass
class StepResult:
    simulation_id: UUID
    step: int
    timestamp: datetime

    # Aggregate metrics
    total_adoption: int
    adoption_rate: float
    diffusion_rate: float             # R(t) = dN/dt
    mean_sentiment: float
    sentiment_variance: float

    # Per-community
    community_metrics: dict[str, CommunityStepMetrics]

    # Emergent behaviors
    emergent_events: list[EmergentEvent]

    # Agent summary (full states in DB)
    action_distribution: dict[str, int]  # action → count

    # Propagation pairs for real-time graph animation (GAP-7)
    # Top N propagation events sorted by probability desc.
    # Frontend renders edge flash / floating particle animations.
    propagation_pairs: list[PropagationPair]  # max 50 per step

    # LLM usage
    llm_calls_this_step: int
    llm_tier_distribution: dict[int, int]  # tier → count

    # Performance
    step_duration_ms: float

@dataclass
class CommunityStepMetrics:
    community_id: UUID
    adoption_count: int
    adoption_rate: float
    mean_belief: float
    dominant_action: AgentAction
    new_propagation_count: int
```

---

## 6. MetricCollector

```python
class MetricCollector:
    async def record(
        self,
        simulation_id: UUID,
        step: int,
        agent_results: list[AgentTickResult],
        emergent_events: list[EmergentEvent],
        step_duration_ms: float,
    ) -> StepResult:
        """
        1. Computes aggregate metrics from agent_results
        2. INSERTs into sim_steps table
        3. Batch INSERTs agent_states (only changed fields for efficiency)
        4. INSERTs emergent_events
        5. INSERTs llm_call_logs from tick results
        Returns computed StepResult.
        """

    async def get_metric_history(
        self,
        simulation_id: UUID,
        metric: str,
        from_step: int = 0,
        to_step: int | None = None,
    ) -> list[tuple[int, float]]:
        """Returns [(step, value)] for the requested metric."""
```

---

## 7. Real-time WebSocket Protocol

```
Client → Server: {"type": "subscribe", "simulation_id": "uuid"}
Server → Client: {"type": "step_result", "data": StepResult}
Server → Client: {"type": "emergent_event", "data": EmergentEvent}
Server → Client: {"type": "simulation_status", "data": {"status": "paused"}}
Client → Server: {"type": "pause", "simulation_id": "uuid"}
Client → Server: {"type": "resume", "simulation_id": "uuid"}
Client → Server: {"type": "inject_event", "data": EnvironmentEvent}
```

---

## 8. Scenario Comparison (F23)

```python
class ScenarioComparator:
    async def compare(
        self,
        simulation_id_a: UUID,
        simulation_id_b: UUID,
        metrics: list[str],
    ) -> ScenarioComparison:
        """
        Compares two completed simulation runs step-by-step.
        Returns diff metrics, adoption curves, and emergent event timeline.
        """

@dataclass
class ScenarioComparison:
    sim_a: UUID
    sim_b: UUID
    metric_diffs: dict[str, list[float]]   # metric → [diff per step]
    final_adoption_diff: float
    emergent_event_diff: list[str]
    winner: UUID | None                     # which scenario performed better
    summary: str
```

---

## 9. Error Specification

| Situation | Exception Type | Recovery | Logging |
|-----------|---------------|----------|---------|
| Step loop async task crashes | `SimulationStepError` | Status → FAILED, persist last valid step, notify client via WebSocket `error` event | ERROR |
| Max concurrent simulations (3) exceeded | `SimulationCapacityError` | Reject `start()` with 429, queue or return retry-after hint | WARN |
| Invalid state transition (e.g., COMPLETED → RUNNING) | `InvalidStateTransitionError` | Reject operation, return current state | ERROR |
| `modify_agent` called while RUNNING | `InvalidStateError` | Reject — only allowed when PAUSED | ERROR |
| `inject_event` with unknown event type | `ValueError` | Reject injection | ERROR |
| `replay_step` target step > current step | `ValueError` | Reject replay | ERROR |
| `replay_step` target step not persisted | `StepNotFoundError` | Reject replay, suggest nearest valid step | ERROR |
| WebSocket disconnect during step | — (resilient) | Continue step execution, buffer events, deliver on reconnect | WARN |
| Celery worker dies during Monte Carlo run | — (Celery retry) | Auto-retry once with same seed; if 2nd fail → mark FAILED | ERROR |
| `create_simulation` with empty community list | `ValueError` | Reject creation | ERROR |
| Step timeout (>2000ms for 1000 agents) | — (soft limit) | Log slow step, continue execution (not fatal) | WARN |
| DB persistence failure during step | `DBPersistenceError` | Retry once; if fail → status FAILED, notify client | ERROR |

---

## 10. Acceptance Criteria (Harness Tests)

| ID | Test | Expected |
|----|------|----------|
| SIM-01 | Create simulation with default config | Status == CONFIGURED |
| SIM-02 | Run 10 steps, check adoption increases | `adoption_rate` monotonically non-decreasing |
| SIM-03 | Pause mid-step | Status == PAUSED after current step completes |
| SIM-04 | Modify agent belief while paused | Next step reflects new belief |
| SIM-05 | Inject negative event | `mean_sentiment` decreases in following step |
| SIM-06 | Replay step produces deterministic result | Same output with same seed |
| SIM-07 | Step executes within 2000ms for 1000 agents | Benchmark |
| SIM-08 | WebSocket receives step_result within 500ms | Real-time requirement |
| SIM-09 | Monte Carlo 100 runs produces viral_probability in [0,1] | Valid range |
| SIM-10 | Scenario comparison returns winner | Non-null winner for different configs |
