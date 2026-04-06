# 17 — Performance Optimization SPEC
Version: 0.1.0 | Status: DRAFT

---

## 0. Related Documents

| Document | Role |
|----------|------|
| **04_SIMULATION_SPEC.md** | Simulation orchestrator, step runner |
| **01_AGENT_SPEC.md** | 6-Layer agent engine |
| **03_DIFFUSION_SPEC.md** | Propagation / exposure / cascade |
| **05_LLM_SPEC.md** | LLM gateway, tier routing |
| **00_ARCHITECTURE.md** | System architecture |

---

## 1. Context

At 1,000 agents the step loop runs in ~287ms. The target is to support **10,000 agents
within 2,000ms per step** (NF01 extrapolation). Profiling reveals that the hot path —
`StepRunner.execute_step()` → community ticks → agent ticks — contains O(N^2) graph
lookups, false concurrency, redundant allocations, and batching that never activates.

This SPEC catalogs **19 findings** from a performance audit and defines a prioritized
remediation plan. Each finding is annotated with file, root cause, fix, and estimated
impact.

---

## 2. Performance Budget (10,000 agents, 10 communities)

| Phase | Budget | Current Estimate |
|-------|--------|-----------------|
| Agent-node map build | 5ms | 50ms (5x rebuild) |
| Community subgraph prep | 10ms | 200ms (deep copy) |
| Agent tick loop (Tier 1/2) | 500ms | 1,200ms (serial + O(N^2) exposure) |
| Agent tick loop (Tier 3 LLM) | 500ms | 5,000ms (serial + batch timeout) |
| Diffusion / propagation | 200ms | 400ms (linear node scan) |
| Cascade detection | 50ms | 50ms (OK) |
| Metrics aggregation | 50ms | 100ms (O(N*C) filter) |
| Network evolution | 100ms | 300ms (deepcopy) |
| Persistence (async) | N/A | N/A (fire-and-forget) |
| **Total** | **< 2,000ms** | **~7,300ms** |

---

## 3. Findings

### PERF-01: ExposureModel._find_agent_node() — O(N) linear scan [HIGH]

**File:** `backend/app/engine/diffusion/exposure_model.py:261-265`

**Problem:** `_find_agent_node()` iterates all graph nodes to find a node by `agent_id`.
Called O(N*M) times per step (once per agent, then per-neighbor in `_rank_feed()`).
At 1,000 agents with 6 neighbors each: ~6M node comparisons per community.

**Fix:** Accept a pre-built `agent_id → node_id` dict (already exists in
`CommunityOrchestrator.agent_node_map`). Thread it through to ExposureModel.

**Impact:** Eliminates the dominant O(N^2) hotspot. Estimated **30-50% of step time**.

---

### PERF-02: PropagationModel._find_agent_node() — same O(N) scan [MEDIUM]

**File:** `backend/app/engine/diffusion/propagation_model.py:198-203`

**Problem:** Same linear scan pattern as PERF-01, called once per propagation event.

**Fix:** Accept `agent_to_node` map parameter.

---

### PERF-03: Agent-to-node mapping rebuilt 4-5 times per step [MEDIUM]

**Files:**
- `step_runner.py:128-133` (`_build_graph_context`)
- `step_runner.py:218-222` (`_build_community_orchestrators`)
- `step_runner.py:456-459` (network evolution)
- `community_orchestrator.py:96-98` (per community)

**Problem:** Each location independently iterates `G.nodes(data=True)`.
At 10,000 nodes: ~40,000-50,000 redundant iterations per step.

**Fix:** Build once at step start, pass to all consumers.

---

### PERF-04: CommunityOrchestrator sequential agent tick loop [HIGH]

**File:** `backend/app/engine/simulation/community_orchestrator.py:244-274`

**Problem:** Agents are processed one-by-one with `await _run_agent_tick(agent, tier)`
despite being in an async context. Even the BATCH_SIZE=32 batches are sequential.
For Tier 3 agents with ~500ms LLM latency: 10 agents = 5 seconds serial.

**Fix:** Use `asyncio.gather()` for Tier 3 agents within each batch.
```python
tasks = [_run_agent_tick(agent, tier) for agent in batch]
results = await asyncio.gather(*tasks)
```

**Impact:** **5-10x faster** Tier 3 processing.

---

### PERF-05: Deep-copy community subgraph per step [MEDIUM]

**File:** `backend/app/engine/simulation/step_runner.py:243`

**Problem:** `G.subgraph(node_ids).copy()` creates a full copy of each community graph.
10 communities = 10 graph copies per step.

**Fix:** Use `G.subgraph(node_ids)` as a read-only view (no `.copy()`).

---

### PERF-06: NetworkEvolver `copy.deepcopy(graph)` [MEDIUM-HIGH]

**File:** `backend/app/engine/network/evolution.py:37`

**Problem:** `copy.deepcopy()` on a 10K-node graph recursively copies every dict, UUID,
and string. Estimated 50-200ms per step.

**Fix:** Use `network.graph.copy()` (shallow structure copy) or mutate in-place.

---

### PERF-07: CommunityOrchestrator instantiated fresh every step [LOW-MEDIUM]

**File:** `backend/app/engine/simulation/step_runner.py:207-275`

**Problem:** Creates new CommunityOrchestrator + AgentTick + 6 layer objects per
community per step = 70+ object instantiations per step.

**Fix:** Cache orchestrators across steps, update agent lists and subgraphs only.

---

### PERF-08: MemoryLayer linear scan + sort on retrieve [MEDIUM]

**File:** `backend/app/engine/agent/memory.py:146-185`

**Problem:** Retrieval iterates all stored memories (up to 1,000 per agent), scores each,
and sorts. With 100 active agents: 100 * sort(1,000) per step per community.

**Fix:** Maintain a heap or sorted structure. Use `heapq.nlargest(k, ...)` instead
of full sort + slice.

---

### PERF-09: Pure Python cosine similarity [MEDIUM]

**File:** `backend/app/engine/agent/memory.py:51-61` and `backend/app/llm/gateway.py:198-206`

**Problem:** Hand-written cosine similarity using Python loops over 768-dim embeddings.
~100x slower than numpy.

**Fix:** `np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))`. Deduplicate.

---

### PERF-10: SentimentModel full-agent-list filter [LOW]

**File:** `backend/app/engine/diffusion/sentiment_model.py:44-47`

**Problem:** `[a for a in agent_states if a.community_id == community_id]` filters
all agents when called from `step_runner.py:407` for missing communities.

**Fix:** Pre-group agents by community_id, pass only relevant agents.

---

### PERF-11: No CPU parallelism across communities [HIGH]

**File:** `backend/app/engine/simulation/step_runner.py:349-359`

**Problem:** `asyncio.gather()` for community ticks provides coroutine concurrency
only, not CPU parallelism. Tier 1/2 ticks are CPU-bound pure Python — all run on
one thread.

**Fix:** Wire up existing Ray infrastructure (`config.ray_enabled`, `distributed.py`)
for cross-community parallelism. On 8-core: potential **4-8x throughput**.

---

### PERF-12: uuid4() per neighbor action [LOW-MEDIUM]

**File:** `backend/app/engine/simulation/community_orchestrator.py:202`

**Problem:** `content_id=uuid4()` generates ~60,000 CSPRNG calls per step at 10K agents.

**Fix:** Use deterministic ID from `(agent_id, neighbor_id, step)` hash.

---

### PERF-13: Dead `run_until_complete` code in tick [LOW]

**File:** `backend/app/engine/agent/tick.py:197-208`

**Problem:** `loop.run_until_complete()` inside an already-running loop silently skips.
Embeddings are never computed in the sync path during simulation.

**Fix:** Remove dead code. Embeddings for sync-path agents should be pre-batched.

---

### PERF-14: LLM batch queue never fills, always waits 100ms [HIGH]

**File:** `backend/app/llm/gateway.py:379-409`

**Problem:** Serial agent processing (PERF-04) means prompts arrive one-by-one.
Batch never reaches BATCH_SIZE=32 — always waits MAX_WAIT_MS=100ms timeout.
With 10 Tier 3 agents: 10 * 100ms = 1 second of pure waiting.

**Fix:** Collect all Tier 3 prompts for a community before submitting as a single
batch, or fix PERF-04 so concurrent submission fills the batch naturally.

---

### PERF-15: SLMBatchInferencer creates new AsyncClient per call [MEDIUM]

**File:** `backend/app/llm/slm_batch.py:56-57`

**Problem:** `AsyncClient(host=self._base_url)` creates a new HTTP client per prompt.
No connection pooling. 100 calls = 100 TCP handshakes.

**Fix:** Create client once in `__init__()`, reuse across calls.

---

### PERF-16: ExposureModel SocialNetwork wrapper allocation [HIGH]

**File:** `backend/app/engine/simulation/community_orchestrator.py:154-177`

**Problem:** Creates a temporary `_SocialNetwork` wrapper with dummy metrics per agent,
then ExposureModel re-scans the graph (PERF-01) on this wrapper.

**Fix:** Restructure ExposureModel to accept node-resolved data directly via
the pre-built `agent_node_map`.

---

### PERF-17: Persistence one-by-one `session.add()` [MEDIUM]

**File:** `backend/app/engine/simulation/persistence.py:98-129, 211-257`

**Problem:** 10,000 individual `session.add()` calls per step for agent states.
Each call performs ORM identity map checks.

**Fix:** Use `session.add_all(batch)` or bulk `session.execute(insert(...).values(rows))`.

---

### PERF-18: TierSelector rebuilds set in loop [LOW]

**File:** `backend/app/engine/agent/tier_selector.py:72-73`

**Problem:** `{c.agent_id for c in tier3_candidates}` rebuilt per agent in priority checks.

**Fix:** Build the set once before the loop.

---

### PERF-19: Step metrics O(N*C) aggregation [LOW-MEDIUM]

**File:** `backend/app/engine/simulation/step_runner.py:491-514`

**Problem:** For each community, filters all updated agents and scans all propagation
events. 10 communities * 10,000 agents = 100,000 comparisons.

**Fix:** Group agents by `community_id` once. Index propagation events by `source_agent_id`.

---

## 4. Priority Tiers

### Tier A — Critical Path (implement first)

| ID | Fix | Estimated Gain | Effort |
|----|-----|---------------|--------|
| PERF-01 + 02 + 16 | Thread `agent_to_node` map through Exposure/Propagation | **30-50% of step time** | Low |
| PERF-04 + 14 | `asyncio.gather()` for Tier 3 agents + batch fill | **5-10x Tier 3 speed** | Medium |
| PERF-03 | Build node map once per step | **~40ms saved** | Low |

### Tier B — High Value (implement second)

| ID | Fix | Estimated Gain | Effort |
|----|-----|---------------|--------|
| PERF-06 | Replace `deepcopy` with shallow copy or in-place mutation | **50-200ms/step** | Low |
| PERF-05 | Subgraph view instead of copy | **~30ms/step** | Low |
| PERF-15 | Reuse SLM AsyncClient | **100-500ms/step** | Low |
| PERF-09 | Numpy cosine similarity | **~100x for Tier 3 memory** | Low |

### Tier C — Nice to Have (implement as needed)

| ID | Fix | Estimated Gain | Effort |
|----|-----|---------------|--------|
| PERF-11 | Ray CPU parallelism | **4-8x throughput** | High |
| PERF-08 | Heap-based memory retrieval | **Variable** | Medium |
| PERF-17 | Bulk DB inserts | **~50ms/step** | Low |
| PERF-07 | Cache orchestrators | **~20ms/step** | Medium |
| PERF-19 | Pre-group metrics | **~10ms/step** | Low |
| PERF-18 | Pre-build tier set | **~5ms/step** | Low |
| PERF-12 | Deterministic content IDs | **~60ms/step** | Low |
| PERF-10 | Pre-group sentiment agents | **~5ms/step** | Low |
| PERF-13 | Remove dead embedding code | **Code cleanup** | Low |

---

## 5. Target Metrics After Optimization

| Scenario | Current | After Tier A | After Tier A+B |
|----------|---------|-------------|----------------|
| 1,000 agents × 1 step | 287ms | ~150ms | ~120ms |
| 10,000 agents × 1 step | ~7,300ms (est.) | ~2,500ms | ~1,500ms |
| 10,000 agents × 1 step (w/ Tier 3 LLM) | ~12,000ms (est.) | ~3,500ms | ~2,000ms |

---

## 6. Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| PERF-AC-01 | 1,000 agents × 1 step | < 500ms |
| PERF-AC-02 | 10,000 agents × 1 step (Tier 1/2 only) | < 2,000ms |
| PERF-AC-03 | 10,000 agents × 1 step (with Tier 3 LLM) | < 3,000ms |
| PERF-AC-04 | ExposureModel node lookup | O(1) dict lookup, not O(N) scan |
| PERF-AC-05 | Agent-to-node map built once per step | Single `G.nodes(data=True)` iteration |
| PERF-AC-06 | Tier 3 agents processed concurrently | `asyncio.gather()` within batches |
| PERF-AC-07 | LLM batch fills before timeout | Batch size reached before MAX_WAIT_MS |
| PERF-AC-08 | No `copy.deepcopy` on graph | Shallow copy or in-place mutation |
| PERF-AC-09 | SLM client reused across calls | Single AsyncClient instance per model |
| PERF-AC-10 | Cosine similarity uses numpy | Vector ops, not Python loops |
