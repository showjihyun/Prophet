# 19_SIMULATION_INTEGRITY_SPEC.md — Simulation Fidelity & Integrity Improvement Plan

> Version: 0.1.0
> Created: 2026-04-09
> Status: DRAFT — implementation begins after user approval
> Audit basis: pessimistic Agent simulation expert audit (2026-04-09)

---

## 0. Grade Target Summary

| Area | Current Grade | Target Grade | Key Improvement |
|------|----------|----------|----------|
| Opinion Dynamics | **D** | **B+** | Introduce Bounded Confidence model |
| Diffusion Engine | **C** | **B+** | SIR-inspired state machine + IC model |
| Agent Cognition Model | **C** | **B** | Emotion dimension interactions + memory materialization |
| Data Integrity | **D** | **B** | run_all/replay/persistence safety |
| Concurrency Safety | **D** | **B** | Lock consistency + state protection |
| Network Model | **B-** | **B+** | Metric reinforcement + bridge improvements + O(N²) removal |
| Scalability | **C+** | **B** | O(N²) bottleneck resolution |
| Reproducibility | **B+** | **A-** | None seed safety net + determinism verification |

---

## Phase 1: Data Integrity & Concurrency (D → B)

> **Principle**: If simulation results cannot be trusted, no model improvement is meaningful.
> **Priority**: CRITICAL — must precede all other Phases

### 1.1 Orchestrator Concurrency Safety (D → B)

**Problem**: `inject_event()`, `replay_step()`, `start()` modify state without simulation lock

**Change Target**:
- `backend/app/engine/simulation/orchestrator.py`

**Changes**:

```python
# AS-IS: inject_event() — no lock
def inject_event(self, simulation_id: UUID, event=None, ...):
    state = self._get_state(simulation_id)
    state.injected_events.append(env_event)  # ← mutation without lock

# TO-BE: inject_event() — lock protected
async def inject_event(self, simulation_id: UUID, event=None, ...):
    lock = self._get_lock(simulation_id)
    async with lock:
        state = self._get_state(simulation_id)
        state.injected_events.append(env_event)
```

Methods to apply same pattern:
| Method | Current | Change |
|--------|------|------|
| `start()` | sync, no lock | `async start()`, `async with lock` |
| `inject_event()` | sync, no lock | `async inject_event()`, `async with lock` |
| `replay_step()` | sync, no lock | `async replay_step()`, `async with lock` |
| `modify_agent()` | sync, no lock | `async modify_agent()`, `async with lock` |

**`_get_lock()` TOCTOU fix**:
```python
# AS-IS
def _get_lock(self, simulation_id: UUID) -> asyncio.Lock:
    if simulation_id not in self._locks:
        self._locks[simulation_id] = asyncio.Lock()
    return self._locks[simulation_id]

# TO-BE: guarantee atomicity via defaultdict
def __init__(self):
    self._locks: dict[UUID, asyncio.Lock] = defaultdict(asyncio.Lock)

def _get_lock(self, simulation_id: UUID) -> asyncio.Lock:
    return self._locks[simulation_id]
```

**Test Contract**:
- `test_orchestrator_inject_event_acquires_lock`
- `test_orchestrator_replay_acquires_lock`
- `test_orchestrator_start_acquires_lock`
- `test_get_lock_returns_same_instance_for_same_id`
- `test_concurrent_inject_and_step_no_lost_events`

---

### 1.2 `run_all` Intermediate Step Persistence (CRITICAL)

**Problem**: `/run-all` only persists the final state → entire data loss on intermediate crash

**Change Target**:
- `backend/app/api/simulations.py` — `run_all_simulation()`
- `backend/app/engine/simulation/orchestrator.py` — `run_all()`

**Changes**:

```python
# AS-IS: orchestrator.run_all() returns only final state after step loop
async def run_all(self, simulation_id: UUID) -> dict:
    while state.current_step < config.max_steps:
        await self.run_step(simulation_id)
    return {"status": state.status, ...}

# TO-BE: persist each step via step_callback
async def run_all(
    self,
    simulation_id: UUID,
    step_callback: Callable[[StepResult, list[Agent]], Awaitable[None]] | None = None,
) -> dict:
    while state.current_step < config.max_steps:
        result = await self.run_step(simulation_id)
        if step_callback:
            await step_callback(result, state.agents)
    return {"status": state.status, ...}
```

Callback injection at the API layer:
```python
# simulations.py — run_all_simulation()
async def _persist_each_step(result: StepResult, agents: list):
    await persist.persist_step(session, sim_uuid, result, agents=agents)

report = await orchestrator.run_all(sim_uuid, step_callback=_persist_each_step)
```

**Test Contract**:
- `test_run_all_persists_every_step`
- `test_run_all_crash_at_step_N_preserves_prior_steps` (mock crash)
- `test_run_all_callback_receives_result_and_agents`

---

### 1.3 Replay State Restoration (HIGH)

**Problem**: `replay_step()` only rewinds `current_step` and does not restore agent state

**Change Target**:
- `backend/app/engine/simulation/orchestrator.py` — `replay_step()`
- `backend/app/engine/simulation/schema.py` — `SimulationState`

**Changes**:

```python
# Store agent snapshot in SimulationState
@dataclass
class SimulationState:
    ...
    # step → agent snapshot (deep copy at each step boundary)
    agent_snapshots: dict[int, list[Agent]] = field(default_factory=dict)

# Save snapshot before each step starts in run_step()
async def run_step(self, simulation_id):
    ...
    state.agent_snapshots[state.current_step] = deepcopy(state.agents)
    result = await self._step_runner.execute_step(state, ...)
    ...

# Restore snapshot in replay_step()
async def replay_step(self, simulation_id, target_step):
    async with self._get_lock(simulation_id):
        ...
        if target_step in state.agent_snapshots:
            state.agents = deepcopy(state.agent_snapshots[target_step])
        state.current_step = target_step
        state.step_history = state.step_history[:target_step]
```

**Memory management**: snapshots retain only the most recent N steps (sliding window, default 20)

**Test Contract**:
- `test_replay_restores_agent_state_to_target_step`
- `test_replay_then_step_produces_consistent_results`
- `test_replay_snapshot_sliding_window_cap`
- `test_replay_acquires_lock`

---

### 1.4 Persistence Failure Safety Net (HIGH)

**Problem**: All `persist_*` swallow exceptions and silently ignore data loss

**Change Target**:
- `backend/app/engine/simulation/persistence.py`

**Changes**:

```python
# AS-IS: ignores all exceptions
async def persist_step(self, session, sim_id, result, agents):
    try:
        ...
    except Exception:
        logger.warning("persist_step failed")  # data loss

# TO-BE: retry + failure queue
import asyncio
from collections import deque

class SimulationPersistence:
    def __init__(self):
        self._failed_queue: deque[tuple[str, dict]] = deque(maxlen=1000)
        self._retry_count: int = 3

    async def persist_step(self, session, sim_id, result, agents):
        for attempt in range(self._retry_count):
            try:
                ...  # existing logic
                return
            except Exception as exc:
                logger.warning(f"persist_step attempt {attempt+1} failed: {exc}")
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(0.5 * (attempt + 1))
        # Final failure: stored in queue (can be drained later)
        self._failed_queue.append(("step", {"sim_id": str(sim_id), "step": result.step}))
        logger.error(f"persist_step PERMANENTLY FAILED for sim={sim_id} step={result.step}")
```

**Added API endpoint**: `GET /admin/persistence-failures` — view failure queue

**Test Contract**:
- `test_persist_step_retries_on_transient_failure`
- `test_persist_step_queues_on_permanent_failure`
- `test_failed_queue_bounded_at_1000`
- `test_admin_persistence_failures_endpoint`

---

### 1.5 SimulationConfig Validation (HIGH)

**Change Target**:
- `backend/app/engine/simulation/schema.py` — `SimulationConfig`

```python
@dataclass
class SimulationConfig:
    ...
    def __post_init__(self):
        if self.max_steps < 1:
            raise ValueError(f"max_steps must be >= 1, got {self.max_steps}")
        if not (0.0 <= self.llm_tier3_ratio <= 1.0):
            raise ValueError(f"llm_tier3_ratio must be in [0, 1], got {self.llm_tier3_ratio}")
        if not (0.0 <= self.slm_llm_ratio <= 1.0):
            raise ValueError(f"slm_llm_ratio must be in [0, 1], got {self.slm_llm_ratio}")
        if self.random_seed is None:
            self.random_seed = int.from_bytes(os.urandom(4), 'big')
        for c in self.communities:
            if c.size < 1:
                raise ValueError(f"Community size must be >= 1, got {c.size}")
```

**Test Contract**:
- `test_config_rejects_zero_max_steps`
- `test_config_rejects_negative_community_size`
- `test_config_rejects_tier3_ratio_above_one`
- `test_config_assigns_random_seed_when_none`

---

## Phase 2: Opinion Dynamics (D → B+)

> **Principle**: Properly implementing one established model is better than multiple ad-hoc heuristics.

### 2.1 Bounded Confidence Model (Deffuant-Weisbuch)

**Change Target**:
- **New**: `backend/app/engine/agent/opinion_dynamics.py`
- **Modify**: `backend/app/engine/agent/tick.py` — belief update logic

**Core Algorithm**:

Deffuant-Weisbuch model: when two agents i, j interact:
```
if |belief_i - belief_j| < ε (confidence bound):
    belief_i += μ * (belief_j - belief_i)
    belief_j += μ * (belief_i - belief_j)
```

- `ε` (epsilon): confidence bound — opinions outside this range are ignored
- `μ` (mu): convergence rate — opinion convergence speed (0 < μ ≤ 0.5)

**Prophet Application**:

```python
@dataclass
class OpinionDynamicsConfig:
    """SPEC: 19_SIMULATION_INTEGRITY_SPEC.md#2.1"""
    model: Literal["deffuant", "classic"] = "deffuant"
    epsilon: float = 0.3        # confidence bound
    mu: float = 0.1             # convergence rate
    stubbornness: float = 0.0   # 0=fully open, 1=immovable (Friedkin extension)

class DeffuantModel:
    """Bounded Confidence opinion update.
    SPEC: 19_SIMULATION_INTEGRITY_SPEC.md#2.1
    """
    def update_belief(
        self,
        agent: Agent,
        neighbor_beliefs: list[tuple[float, float]],  # (belief, trust_weight)
        config: OpinionDynamicsConfig,
    ) -> float:
        """Update agent belief via pairwise Deffuant interactions."""
        new_belief = agent.belief
        stubbornness = config.stubbornness * agent.personality.skepticism

        for neighbor_belief, trust in neighbor_beliefs:
            distance = abs(new_belief - neighbor_belief)
            if distance < config.epsilon:
                adjustment = config.mu * trust * (neighbor_belief - new_belief)
                new_belief += adjustment * (1.0 - stubbornness)

        return max(-1.0, min(1.0, new_belief))
```

**tick.py changes**:
```python
# AS-IS (tick.py:224)
new_belief = max(-1.0, min(1.0, agent.belief + cognition.evaluation_score * 0.1))

# TO-BE
neighbor_beliefs = [
    (n.belief, graph_context.get_trust(agent.agent_id, n.agent_id))
    for n in neighbors
]
# Cognition score still influences belief as external stimulus
external_shift = cognition.evaluation_score * 0.05
agent.belief = max(-1.0, min(1.0, agent.belief + external_shift))
# Then apply Deffuant pairwise dynamics
agent.belief = opinion_model.update_belief(agent, neighbor_beliefs, config.opinion_dynamics)
```

**Test Contract (Red-Green)**:
- `test_deffuant_converges_within_epsilon`
- `test_deffuant_no_update_beyond_epsilon`
- `test_deffuant_mu_controls_convergence_speed`
- `test_deffuant_stubbornness_resists_change`
- `test_deffuant_symmetric_update`
- `test_opinion_dynamics_classic_mode_backward_compatible`

---

## Phase 3: Diffusion Model Improvement (C → B+)

> **Principle**: Borrow the state transition concept from SIR while reflecting the characteristics of information diffusion.

### 3.1 Agent Diffusion State Machine (SEIAR)

Extending the existing boolean `adopted` to a 5-state machine:

```
SUSCEPTIBLE → EXPOSED → INTERESTED → ADOPTED → RECOVERED
     ↑            ↓                       ↓
     └──── RESISTANT ←────────────────────┘
```

**Change Target**:
- **Modify**: `backend/app/engine/agent/schema.py` — `AgentState`
- **New**: `backend/app/engine/diffusion/state_machine.py`

```python
class DiffusionState(str, Enum):
    """SPEC: 19_SIMULATION_INTEGRITY_SPEC.md#3.1"""
    SUSCEPTIBLE = "susceptible"   # not yet exposed
    EXPOSED = "exposed"           # exposed, not yet interested (incubation)
    INTERESTED = "interested"     # showing interest, not yet adopted
    ADOPTED = "adopted"           # adoption complete
    RECOVERED = "recovered"       # interest waned, no longer spreading
    RESISTANT = "resistant"       # actively rejecting, immune

class DiffusionStateMachine:
    """SIR-inspired state transitions for information diffusion.
    SPEC: 19_SIMULATION_INTEGRITY_SPEC.md#3.1
    """
    # transition probabilities (per step)
    exposure_to_interest: float = 0.3   # E → I
    interest_to_adoption: float = 0.15  # I → A
    adoption_to_recovery: float = 0.02  # A → R (interest decay)
    exposure_to_resistant: float = 0.1  # E → RESISTANT (rejection)

    def transition(self, agent: Agent, exposure_score: float, rng: Random) -> DiffusionState:
        current = agent.diffusion_state
        if current == DiffusionState.SUSCEPTIBLE and exposure_score > 0:
            return DiffusionState.EXPOSED
        if current == DiffusionState.EXPOSED:
            if rng.random() < self.exposure_to_resistant * agent.personality.skepticism:
                return DiffusionState.RESISTANT
            if rng.random() < self.exposure_to_interest * exposure_score:
                return DiffusionState.INTERESTED
        if current == DiffusionState.INTERESTED:
            if rng.random() < self.interest_to_adoption * (1 - agent.personality.skepticism):
                return DiffusionState.ADOPTED
        if current == DiffusionState.ADOPTED:
            if rng.random() < self.adoption_to_recovery:
                return DiffusionState.RECOVERED
        return current
```

**Backward compatibility**: Map `agent.adopted` property to `diffusion_state == ADOPTED`

**Test Contract**:
- `test_susceptible_to_exposed_on_exposure`
- `test_exposed_to_interested_probability`
- `test_interested_to_adopted_probability`
- `test_adopted_to_recovered_decay`
- `test_exposed_to_resistant_skeptic`
- `test_backward_compat_adopted_property`
- `test_recovered_agents_do_not_propagate`
- `test_resistant_agents_are_immune`

### 3.2 Propagation Emotion Factor Continualization

**Problem**: When `emotion_factor ≤ 0`, propagation probability is exactly 0 (hard cutoff)

**Change Target**:
- `backend/app/engine/diffusion/propagation_model.py`

```python
# AS-IS (line 143-148)
emotion_factor = max(0.0, emotion_factor)  # hard cutoff

# TO-BE: sigmoid smoothing
def _smooth_emotion_factor(raw: float) -> float:
    """Sigmoid-smoothed emotion factor: never exactly 0, graceful degradation."""
    # Maps (-inf, +inf) → (0.01, 1.0)
    # At raw=0: returns ~0.05 (not zero)
    # At raw=1: returns ~0.73
    return 0.01 + 0.99 / (1.0 + math.exp(-4.0 * raw))
```

**Test Contract**:
- `test_emotion_factor_never_exactly_zero`
- `test_emotion_factor_positive_returns_high`
- `test_emotion_factor_negative_returns_low_but_nonzero`

---

## Phase 4: Agent Cognition Enhancement (C → B)

### 4.1 Emotion Dimension Interactions

**Problem**: 4 emotion dimensions are updated independently

**Change Target**:
- `backend/app/engine/agent/emotion.py`

```python
# TO-BE: inter-dimension interaction matrix
EMOTION_INTERACTION = {
    # trust increase → skepticism decrease (inverse relationship)
    ("trust", "skepticism"): -0.3,
    ("skepticism", "trust"): -0.3,
    # excitement increase → interest increase (positive relationship)
    ("excitement", "interest"): 0.2,
    # skepticism increase → excitement decrease (suppression)
    ("skepticism", "excitement"): -0.2,
}

def update(self, agent: Agent, signals: EmotionSignals) -> AgentEmotion:
    # 1) existing independent update
    deltas = self._compute_independent_deltas(agent, signals)
    # 2) interaction correction
    for (src, tgt), weight in EMOTION_INTERACTION.items():
        deltas[tgt] += deltas[src] * weight
    # 3) apply + clamp
    return self._apply_deltas(agent.emotion, deltas)
```

**Test Contract**:
- `test_trust_increase_dampens_skepticism`
- `test_skepticism_increase_dampens_excitement`
- `test_excitement_increase_boosts_interest`
- `test_emotion_interaction_does_not_exceed_bounds`

### 4.2 Enable Cosine Similarity by Default in Memory Retrieval

**Problem**: `memory_fallback_beta=0.0` makes relevance weight 0

**Change Target**:
- `backend/app/config.py` — change default value

```python
# AS-IS
memory_fallback_beta: float = 0.0   # ignore relevance (cosine sim)

# TO-BE
memory_fallback_beta: float = 0.25  # weight relevance at 25%
```

**Test Contract**:
- `test_memory_retrieval_uses_cosine_similarity`
- `test_memory_relevant_items_ranked_higher`

### 4.3 Perception Network Weight Incorporation

**Problem**: `edge_weight` is hardcoded to `1.0`

**Change Target**:
- `backend/app/engine/agent/perception.py`

```python
# AS-IS (line 159)
edge_weight = 1.0

# TO-BE
edge_weight = graph_context.get_edge_weight(agent.agent_id, neighbor.agent_id, default=0.5)
```

**Test Contract**:
- `test_perception_uses_real_edge_weights`
- `test_perception_high_weight_neighbor_stronger_signal`

---

## Phase 5: Network & Scalability (B- → B+, C+ → B)

### 5.1 Network Metric Reinforcement

**Change Target**:
- `backend/app/engine/network/generator.py`

**Added metrics**:
```python
def compute_metrics(self, G: nx.Graph) -> dict:
    return {
        "clustering_coefficient": nx.average_clustering(G),
        "average_path_length": self._safe_avg_path_length(G),
        "modularity": self._compute_modularity(G),           # new
        "assortativity": nx.degree_assortativity_coefficient(G),  # new
        "degree_distribution": self._degree_distribution(G),
    }

def _compute_modularity(self, G: nx.Graph) -> float:
    """Compute Newman modularity using community partition."""
    communities = [
        {n for n, d in G.nodes(data=True) if d.get("community") == c}
        for c in set(nx.get_node_attributes(G, "community").values())
    ]
    return nx.community.modularity(G, communities)
```

**Test Contract**:
- `test_metrics_include_modularity`
- `test_metrics_include_assortativity`
- `test_modularity_positive_for_community_structure`

### 5.2 Bridge Edge Improvement — Preferential Attachment

**Change Target**:
- `backend/app/engine/network/generator.py` — `_add_bridge_edges()`

```python
# AS-IS: uniform random selection
target_node = rng.choice(list(other_community_nodes))

# TO-BE: degree-weighted preferential attachment
degrees = [G.degree(n) for n in other_nodes]
total_deg = sum(degrees) or 1
probs = [d / total_deg for d in degrees]
target_node = rng.choices(other_nodes, weights=probs, k=1)[0]
```

**Test Contract**:
- `test_bridge_edges_prefer_high_degree_nodes`
- `test_bridge_edge_weight_varies`

### 5.3 O(N²) Bottleneck Resolution

#### 5.3a Exposure Model — Reverse Map Caching

**Change Target**:
- `backend/app/engine/diffusion/exposure_model.py`

```python
# AS-IS (line 170): rebuilt per agent
node_to_agent = {v: k for k, v in agent_node_map.items()}

# TO-BE: built once at ExposureModel initialization
class ExposureModel:
    def __init__(self, ...):
        self._reverse_map: dict | None = None

    def _get_reverse_map(self, agent_node_map):
        if self._reverse_map is None:
            self._reverse_map = {v: k for k, v in agent_node_map.items()}
        return self._reverse_map
```

#### 5.3b Network Metrics — average_path_length Sampling

```python
# AS-IS: O(N*(N+E)) — all node pairs
nx.average_shortest_path_length(G)

# TO-BE: 1000-sample estimation (O(1000*(N+E)))
def _safe_avg_path_length(self, G: nx.Graph, sample_size: int = 1000) -> float:
    if len(G) <= sample_size:
        return nx.average_shortest_path_length(G)
    nodes = self._rng.sample(list(G.nodes()), sample_size)
    total = sum(
        nx.single_source_shortest_path_length(G, n).values()
        for n in nodes[:100]
    )
    return total / (100 * len(G))
```

#### 5.3c Remove Edge Storage Cap

```python
# AS-IS (persistence.py:143)
edge_batch = network_edges[:5000]

# TO-BE: batch insert (1000 at a time)
for i in range(0, len(network_edges), 1000):
    batch = network_edges[i:i+1000]
    await session.execute(insert_stmt, batch)
```

**Test Contract**:
- `test_exposure_model_reverse_map_built_once`
- `test_avg_path_length_sampling_for_large_graphs`
- `test_persistence_stores_all_edges`

---

## Phase 6: WebSocket Reliability & Statistics Correction

### 6.1 WebSocket Sequence Numbers

**Change Target**:
- `backend/app/api/ws.py`

```python
class ConnectionManager:
    def __init__(self):
        self._seq: dict[str, int] = defaultdict(int)  # sim_id → sequence

    async def broadcast(self, simulation_id: str, message: dict):
        self._seq[simulation_id] += 1
        message["seq"] = self._seq[simulation_id]
        ...
```

**Frontend**:
- Track `seq` in `useSimulationSocket.ts`, correct via REST when gap detected (missing steps fetch)

### 6.2 Ping/Pong Normal Handling

**Change Target**:
- `backend/app/api/ws.py` — WebSocket message handler

```python
# AS-IS: treats "ping" as unknown type
# TO-BE:
if msg_type == "ping":
    await websocket.send_json({"type": "pong", "ts": time.time()})
```

### 6.3 Statistical Correction

**Variance calculation**: `population variance (/n)` → `sample variance (/n-1)` (Bessel's correction)

**Change Target**:
- `backend/app/engine/simulation/step_runner.py`
- `backend/app/engine/diffusion/sentiment_model.py`

```python
# AS-IS
variance = sum((b - mean) ** 2 for b in beliefs) / n

# TO-BE
variance = sum((b - mean) ** 2 for b in beliefs) / max(n - 1, 1)
```

**diffusion_rate type**: `int` → `float` (schemas.py)

**Cascade multi-community detection**:
```python
# AS-IS: return on first match
# TO-BE: collect all matches
polarized_communities = []
for cid, var in community_variances.items():
    if var > threshold:
        polarized_communities.append(cid)
if polarized_communities:
    return EmergentEvent(..., description=f"Polarization in {len(polarized_communities)} communities")
```

---

## Phase Implementation Order & Dependencies

```
Phase 1 (Data Integrity)       ← highest priority, prerequisite for all other Phases
    ↓
Phase 2 (Opinion Dynamics)     ← after Phase 1 complete
    ↓
Phase 3 (Diffusion Model)      ← can run in parallel with Phase 2
    ↓
Phase 4 (Agent Cognition)      ← after Phase 2, 3 complete (depends on belief update changes)
    ↓
Phase 5 (Network & Scalability) ← can proceed independently after Phase 1 complete
    ↓
Phase 6 (WS & Statistics)      ← can proceed independently
```

## Expected Test Increment

| Phase | New Test Count | Area |
|-------|-------------|------|
| Phase 1 | ~20 | orchestrator concurrency, run_all persistence, replay restoration, config validation |
| Phase 2 | ~10 | Deffuant model, backward compat |
| Phase 3 | ~12 | SEIAR state machine, emotion sigmoid, backward compat |
| Phase 4 | ~8 | emotion interactions, memory cosine, perception weights |
| Phase 5 | ~8 | metric reinforcement, bridge improvements, O(N²) resolution |
| Phase 6 | ~6 | WS sequence, ping/pong, statistics correction |
| **Total** | **~64** | |

---

## Completion Criteria

Re-audit grade targets upon completion of all Phases:

| Area | D/C → Target | Verification Method |
|------|-----------|----------|
| Opinion Dynamics | D → **B+** | Deffuant convergence tests, epsilon threshold tests |
| Diffusion Engine | C → **B+** | SEIAR transition probability tests, recovery/immunity behavior verification |
| Agent Cognition | C → **B** | emotion interactions, memory cosine, real edge weights |
| Data Integrity | D → **B** | run_all intermediate persistence, replay state restoration, retry |
| Concurrency Safety | D → **B** | all mutation methods lock-protected, concurrency tests |
| Network | B- → **B+** | modularity/assortativity calculation, preferential bridge |
| Scalability | C+ → **B** | O(N²) removal confirmed, 10K agent benchmark |
| Reproducibility | B+ → **A-** | None seed auto-assignment, determinism regression test |
