# 04 — Simulation Orchestrator SPEC
Version: 0.1.1 | Status: DRAFT

---

## 1. Overview

The SimulationOrchestrator is the top-level coordinator that manages simulation lifecycle, step execution, real-time intervention, and metric collection.

### Execution Model

- **Step loop:** `asyncio.Task` (NOT Celery). Steps run as async coroutines within the FastAPI event loop.
- **Monte Carlo:** Celery worker task. Each run is a Celery task dispatched to Valkey-backed queue, allowing parallel execution across worker processes.
- **Rationale:** Step execution requires real-time WebSocket feedback (asyncio-native). Monte Carlo is fire-and-forget batch work (Celery-appropriate).
- **Concurrency:** Max 3 simultaneous simulation step-loops per API server. Monte Carlo worker pool configurable via `CELERY_CONCURRENCY` env.
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
        Execute one simulation step:
            1. Get active campaign events for current step
            2. ExposureModel.compute_exposure(agents, graph, events)
            3. asyncio.gather(*[AgentEngine.tick(agent) for agent in agents])
            4. PropagationModel → generate new events for next step
            5. SentimentModel.update_community_sentiment()
            6. CascadeDetector.detect()
            7. MetricCollector.record(step, results)
            8. NetworkEvolver.evolve_step() if enabled

        Note: All engine calls receive an `agent_node_map: dict[UUID, int]`
        mapping agent UUIDs to NetworkX integer node IDs. This map is built
        once per step from `SocialNetwork.graph.nodes(data='agent_id')` and
        passed to ExposureModel, PropagationModel, and NetworkEvolver to
        avoid O(N) graph scans per agent.

            9. WebSocket.broadcast(step_summary)
           10. Persist agent_states to PostgreSQL

        Returns StepResult.
        Increments simulation.current_step.
        """

    async def pause(self, simulation_id: UUID) -> None:
        """Status → PAUSED. Current step completes before pausing."""

    async def resume(self, simulation_id: UUID) -> None:
        """Status → RUNNING. Continues from current_step."""

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
