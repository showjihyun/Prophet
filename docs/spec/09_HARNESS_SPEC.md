# 09 — Test Harness SPEC (F18–F30)
Version: 0.1.0 | Status: DRAFT

---

## 1. Overview

The harness is a first-class engineering system — not just a test helper. It provides mock environments, replay, hot-swap, performance monitoring, and failure recovery so every module can be developed, debugged, and extended independently.

**Harness is required to pass before any Phase is considered complete.**

---

## 2. Harness Feature Map

| ID | Feature | Phase | Description |
|----|---------|-------|-------------|
| F18 | Unit Test Hooks | 1 | Per-layer test entry points for Agent, Network, Diffusion |
| F19 | Mock Environment | 1 | Full simulation without LLM or DB (in-memory stubs) |
| F20 | Event/Agent Replay | 1 | Step-level replay from stored state |
| F21 | Metric Logging API | 2 | Structured logging of all step metrics to file + DB |
| F22 | Module Hot-Swap | 2 | Replace agent/LLM/network module at runtime |
| F23 | Scenario Comparison | 4 | Diff two simulation runs |
| F24 | Simulation Sandbox | 1 | Isolated test run with ephemeral DB |
| F25 | Debug Visualization | 3 | Agent decision tree + LLM prompt/response inspector |
| F26 | API/Integration Hooks | 2 | External data injection, LLM stream connection |
| F27 | Performance Monitor | 2 | CPU/memory/step-time instrumentation |
| F28 | Failure Recovery | 2 | Retry/fallback on agent or LLM failure |
| F29 | Configurable Agent Behavior | 1 | Dynamic agent modification via config |
| F30 | Hybrid Execution Mode | 3 | Per-step LLM provider selection |

---

## 3. F18 — Unit Test Hooks

Each engine layer exposes a `harness_hook()` entry point for direct unit testing:

```python
# backend/harness/runners/agent_harness.py

class AgentHarness:
    def run_perception(
        self,
        agent: AgentState,
        events: list[EnvironmentEvent],
        neighbors: list[NeighborAction],
    ) -> PerceptionResult:
        """Direct PerceptionLayer call — no other layers involved."""

    def run_emotion_update(
        self,
        current_emotion: AgentEmotion,
        signals: EmotionSignals,
    ) -> AgentEmotion:
        """Direct EmotionLayer call."""

    def run_cognition(
        self,
        agent: AgentState,
        perception: PerceptionResult,
        memories: list[MemoryRecord],
        tier: int,
    ) -> CognitionResult:
        """Direct CognitionLayer call with mocked LLM if tier=3."""

    def run_full_tick(
        self,
        agent: AgentState,
        context: AgentTickContext,
        mock_llm: bool = True,
    ) -> AgentTickResult:
        """Full agent tick with optional mock LLM."""


class NetworkHarness:
    def generate_minimal(self, n_agents: int = 10) -> SocialNetwork:
        """Fast small network for unit tests."""

    def assert_scale_free(self, network: SocialNetwork) -> None:
        """Assert degree distribution follows power law."""


class DiffusionHarness:
    def run_single_step(
        self,
        agents: list[AgentState],
        network: SocialNetwork,
        campaign: CampaignConfig,
    ) -> StepResult:
        """Run one diffusion step in isolation."""
```

---

## 4. F19 — Mock Environment

```python
# backend/harness/mocks/mock_environment.py

class MockLLMAdapter(LLMAdapter):
    """
    Returns deterministic responses for testing.
    Configurable response templates.
    Never makes network calls.
    """
    provider_name = "mock"

    def __init__(self, response_template: dict[str, Any] | None = None):
        self.response_template = response_template or {
            "evaluation_score": 0.5,
            "recommended_action": "like",
            "reasoning": "Mock reasoning for test",
            "confidence": 0.8
        }
        self.call_count = 0
        self.call_log: list[LLMPrompt] = []

    async def complete(self, prompt: LLMPrompt, options=None) -> LLMResponse:
        self.call_count += 1
        self.call_log.append(prompt)
        return LLMResponse(
            provider="mock",
            model="mock-1.0",
            content=json.dumps(self.response_template),
            parsed=self.response_template,
            prompt_tokens=100,
            completion_tokens=50,
            latency_ms=1.0,
        )

    async def embed(self, text: str) -> list[float]:
        """Returns deterministic 768-dim vector (hash-based)."""
        seed = int(hashlib.md5(text.encode()).hexdigest(), 16) % (2**32)
        rng = np.random.default_rng(seed)
        return rng.uniform(-1, 1, 768).tolist()


class MockSLMAdapter(SLMBatchInferencer):
    """
    Mock SLM for Tier 1 testing.
    Returns deterministic responses without GPU/Ollama dependency.
    Simulates batch inference latency.
    """
    def __init__(self, response_template: dict | None = None):
        self.response_template = response_template or {
            "evaluation_score": 0.3,
            "action": "like",
            "reasoning": "Mock SLM reasoning",
            "confidence": 0.6
        }
        self.call_count = 0
        self.batch_log: list[int] = []  # batch sizes

    async def batch_complete(self, prompts: list, options=None) -> list:
        self.call_count += len(prompts)
        self.batch_log.append(len(prompts))
        return [LLMResponse(
            provider="mock-slm", model="mock-phi4",
            content=json.dumps(self.response_template),
            parsed=self.response_template,
            prompt_tokens=50, completion_tokens=30,
            latency_ms=5.0,
        ) for _ in prompts]


class MockDatabase:
    """
    In-memory SQLite database for harness tests.
    Eliminates PostgreSQL dependency in unit tests.
    """
    def __init__(self):
        self.engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def setup(self) -> None:
        """Creates all tables from SQLAlchemy models."""
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def teardown(self) -> None:
        await self.engine.dispose()
```

---

## 5. F20 — Event/Agent Replay

```python
# backend/harness/runners/replay_runner.py

class ReplayRunner:
    async def replay_from_step(
        self,
        simulation_id: UUID,
        target_step: int,
        db: AsyncSession,
        modifications: list[AgentModification] | None = None,
    ) -> AsyncIterator[StepResult]:
        """
        1. Load agent_states at target_step from DB
        2. Load network snapshot (edge weights at that step)
        3. Apply optional modifications (for what-if analysis)
        4. Re-run simulation from target_step using same config + new random seed
        5. Yields StepResult for each replayed step

        Original run data is not modified.
        Replay steps stored with replay_id tag in sim_steps.
        """

    async def compare_with_original(
        self,
        simulation_id: UUID,
        replay_id: UUID,
        metrics: list[str],
        db: AsyncSession,
    ) -> ReplayComparison:
        """Side-by-side metric comparison of original vs replay."""
```

---

## 6. F21 — Metric Logging API

```python
# backend/harness/metric_logger.py

class MetricLogger:
    """
    Structured logging of all simulation events.
    Writes to: PostgreSQL (sim_steps) + optional JSONL file.
    """

    def __init__(self, simulation_id: UUID, output_path: Path | None = None):
        self.simulation_id = simulation_id
        self.output_path = output_path  # if set, writes JSONL for offline analysis

    def log_step(self, step_result: StepResult) -> None: ...
    def log_agent_action(self, agent_id: UUID, step: int, action: AgentAction) -> None: ...
    def log_llm_call(self, call_log: LLMCallLog) -> None: ...
    def log_emergent_event(self, event: EmergentEvent) -> None: ...
    def log_performance(self, step: int, duration_ms: float, agent_count: int) -> None: ...

    def export_jsonl(self, output_path: Path) -> None:
        """Export all logged events as JSONL for external analysis."""

    def get_summary(self) -> SimulationSummary:
        """Returns aggregated statistics across all logged steps."""
```

---

## 7. F22 — Module Hot-Swap

```python
# backend/harness/hotswap.py

class ModuleRegistry:
    """
    Runtime module replacement without restarting simulation.
    Used in harness to test alternative implementations.
    """
    _registry: dict[str, Any] = {}

    def register(self, name: str, module: Any) -> None:
        self._registry[name] = module

    def swap(self, name: str, new_module: Any) -> Any:
        """Replace module, returns old module for restoration."""
        old = self._registry.get(name)
        self._registry[name] = new_module
        return old

    def get(self, name: str) -> Any:
        return self._registry[name]

# Usage:
# registry.swap("llm_adapter", MockLLMAdapter())
# registry.swap("cognition_engine", AlternativeCognitionEngine())
```

---

## 8. F24 — Simulation Sandbox

```python
# backend/harness/sandbox.py

class SimulationSandbox:
    """
    Isolated simulation environment for testing.
    Uses ephemeral in-memory DB + mock LLM.
    Auto-tears down after context exit.
    """

    @classmethod
    @asynccontextmanager
    async def create(
        cls,
        config: SimulationConfig | None = None,
        mock_llm: bool = True,
        seed: int = 42,
    ) -> AsyncIterator["SimulationSandbox"]:
        """
        async with SimulationSandbox.create(seed=42) as sandbox:
            result = await sandbox.run_steps(5)
            assert result.adoption_rate > 0
        """

    async def run_steps(self, n: int) -> StepResult: ...
    async def run_to_completion(self) -> SimulationRun: ...
    async def get_agent(self, agent_id: UUID) -> AgentState: ...
    async def modify_agent(self, agent_id: UUID, mod: AgentModification) -> None: ...
    async def inject_event(self, event: EnvironmentEvent) -> None: ...
```

---

## 9. F25 — Debug Visualization

```python
# backend/harness/debug_viz.py

class AgentDecisionDebugger:
    """
    Produces structured debug output of a single agent tick.
    Used to inspect why an agent made a specific decision.
    """

    def explain_tick(self, tick_result: AgentTickResult) -> AgentDecisionTrace:
        """
        Returns full trace:
            - Which events were perceived
            - Which memories were retrieved (with scores)
            - Emotion update delta
            - Cognition evaluation breakdown (Tier used, score components)
            - Social pressure contributors
            - Action probability distribution
            - Final action + confidence
            - If LLM: full prompt + raw response
        """

@dataclass
class AgentDecisionTrace:
    agent_id: UUID
    step: int
    tier_used: int
    perception_summary: str
    memories_retrieved: list[dict]  # memory + retrieval score
    emotion_before: AgentEmotion
    emotion_after: AgentEmotion
    cognition_score_components: dict[str, float]
    social_pressure: float
    action_probabilities: dict[str, float]
    chosen_action: AgentAction
    llm_prompt: str | None
    llm_response: str | None
    reasoning: str | None
```

---

## 10. F27 — Performance Monitor

```python
# backend/harness/performance.py

class SimulationProfiler:
    """Instruments step execution for performance analysis."""

    @asynccontextmanager
    async def profile_step(self, step: int) -> AsyncIterator[StepProfile]:
        """
        async with profiler.profile_step(step) as profile:
            await run_step()
        # profile.to_dict() contains timing breakdown
        """

@dataclass
class StepProfile:
    step: int
    total_duration_ms: float
    exposure_ms: float
    agent_tick_ms: float
    propagation_ms: float
    cascade_detection_ms: float
    db_write_ms: float
    ws_broadcast_ms: float
    llm_calls_ms: float
    agent_count: int
    llm_call_count: int
    memory_mb: float
```

---

## 11. F28 — Failure Recovery

```python
# backend/harness/recovery.py

class FailureRecoveryManager:
    """
    Handles failures gracefully to keep simulation running.
    """

    async def with_llm_fallback(
        self,
        llm_call: Coroutine,
        fallback_tier: int = 2,
        agent: AgentState | None = None,
    ) -> CognitionResult:
        """
        Attempts LLM call.
        On LLMTimeoutError or LLMQuotaError: falls back to Tier fallback_tier.
        On 3 consecutive failures: disables LLM for this step.
        Logs all failures to simulation_events.
        """

    async def with_agent_retry(
        self,
        agent_tick: Coroutine,
        max_retries: int = 2,
    ) -> AgentTickResult:
        """
        Retries agent tick on transient errors.
        On final failure: returns a safe default AgentTickResult (action=IGNORE).
        """

    def checkpoint(
        self,
        simulation_id: UUID,
        step: int,
        agent_states: list[AgentState],
    ) -> None:
        """
        Periodic checkpoint to Valkey.
        On simulation crash: can resume from last checkpoint.
        """
```

---

## 12. Harness Test Runner

```python
# backend/harness/runners/harness_runner.py

class HarnessRunner:
    """
    Orchestrates running all harness acceptance tests for a phase.
    """

    def run_phase(self, phase: int) -> HarnessReport:
        """
        Runs all acceptance criteria tests for the given phase.
        Returns pass/fail per test with details.
        """

    def run_all(self) -> HarnessReport: ...

@dataclass
class HarnessReport:
    phase: int
    total: int
    passed: int
    failed: int
    skipped: int
    results: list[HarnessTestResult]
    duration_ms: float

    @property
    def is_passing(self) -> bool:
        return self.failed == 0
```

---

## 13. pytest Configuration

```python
# backend/tests/conftest.py

@pytest.fixture
async def sandbox():
    async with SimulationSandbox.create(seed=42) as s:
        yield s

@pytest.fixture
def mock_llm():
    return MockLLMAdapter()

@pytest.fixture
def mock_slm():
    return MockSLMAdapter()

@pytest.fixture
async def mock_db():
    db = MockDatabase()
    await db.setup()
    yield db.session
    await db.teardown()

@pytest.fixture
def agent_harness():
    return AgentHarness()

@pytest.fixture
def network_harness():
    return NetworkHarness()

@pytest.fixture
def diffusion_harness():
    return DiffusionHarness()
```

---

## 14. Running Harness

```bash
# Run all harness tests
uv run pytest backend/tests/ -v

# Run specific phase
uv run pytest backend/tests/ -v -m "phase1"

# Run acceptance criteria only
uv run pytest backend/tests/ -v -m "acceptance"

# Performance benchmarks
uv run pytest backend/tests/ -v -m "benchmark" --benchmark-only

# With coverage
uv run pytest backend/tests/ --cov=backend/app --cov-report=html
```

**pytest marks:**
- `@pytest.mark.phase1` through `@pytest.mark.phase7`
- `@pytest.mark.acceptance` — SPEC acceptance criteria
- `@pytest.mark.benchmark` — performance tests
- `@pytest.mark.integration` — requires live DB + Ollama
- `@pytest.mark.unit` — pure unit tests, no external deps
