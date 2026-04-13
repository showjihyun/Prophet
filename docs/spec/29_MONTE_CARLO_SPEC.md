# 29_MONTE_CARLO_SPEC

> **Status**: CURRENT
> **Version**: 0.1.0
> **Created**: 2026-04-13
> **Scope**: Real Monte Carlo sweep — engine schema completion, API endpoint, frontend wiring.

This SPEC closes the half-finished Monte Carlo (MC) work surfaced in 2026-04:
the `MonteCarloRunner` engine class existed in
`backend/app/engine/simulation/monte_carlo.py` but **could not be imported**
because its result dataclasses (`RunSummary`, `MonteCarloResult`) were never
defined. The frontend `DecidePanel → Monte Carlo` tab existed but silently
fell back to single-seed `run-all`, which is not a Monte Carlo sweep at all.

---

## 1. Engine Contract (MC-ENG-*)

### 1.1 Result dataclasses (MC-ENG-01)

**File**: `backend/app/engine/diffusion/schema.py`

```python
@dataclass
class RunSummary:
    """One run's terminal stats."""
    run_id: int
    final_adoption: int       # # of adopted agents at last step
    viral_detected: bool      # any viral_cascade event during the run
    steps_completed: int      # may be < max_steps if a step failed

@dataclass
class MonteCarloResult:
    """Aggregate over N runs of the same config with different seeds."""
    n_runs: int
    viral_probability: float            # P(any viral cascade)
    expected_reach: float               # mean(final_adoption)
    p5_reach: float
    p50_reach: float
    p95_reach: float
    community_adoption: dict[str, float]   # community_id → mean adoption rate
    run_summaries: list[RunSummary]
```

### 1.2 Runner behavior (MC-ENG-02)

**File**: `backend/app/engine/simulation/monte_carlo.py`

- Each run gets `random_seed = base_seed + run_id * 1000` for reproducibility.
- Concurrency is bounded by an `asyncio.Semaphore` (default 3) to prevent
  memory exhaustion when a 5K-agent network is replicated N times in RAM.
- A failed run logs WARNING and is excluded from aggregates — does not abort
  the sweep.
- `viral_probability = (# runs with any viral_cascade) / n_runs`.
- Percentiles use sorted-index lookup (no interpolation) for stability with
  small N.

---

## 2. API Contract (MC-API-*)

### 2.1 Endpoint (MC-API-01)

```
POST /api/v1/simulations/{simulation_id}/monte-carlo
```

**Request body** (`MonteCarloRequest`):

```json
{
  "n_runs": 10,
  "max_concurrency": 3
}
```

| Field | Type | Constraint | Default |
|-------|------|-----------|---------|
| `n_runs` | int | `[2, 50]` | 10 |
| `max_concurrency` | int | `[1, 10]` | 3 |

`n_runs < 2` is rejected (a single run is not Monte Carlo).
`n_runs > 50` is rejected (would dominate the host; users running larger
sweeps should script the engine directly).

**Response body** (`MonteCarloResponse`):

```json
{
  "simulation_id": "uuid",
  "n_runs": 10,
  "viral_probability": 0.7,
  "expected_reach": 412.3,
  "p5_reach": 280.0,
  "p50_reach": 415.0,
  "p95_reach": 612.0,
  "community_adoption": { "uuid-1": 0.42, "uuid-2": 0.31 },
  "run_summaries": [
    { "run_id": 0, "final_adoption": 380, "viral_detected": true, "steps_completed": 50 }
  ]
}
```

### 2.2 Synchronous execution + timeout (MC-API-02)

The endpoint is **synchronous** in this cycle (await + return). For
production-scale sweeps (>50 runs or 10K-agent networks) a background-job
queue is the future direction, but is out of scope here.

Realistic latency ceilings (RTX 4070-class host, 1K agents, 50 steps,
n_runs=10, concurrency=3):
- ~30–90 seconds wall time depending on tier-3 ratio + LLM cache hits.

The frontend MUST show a "Running..." indicator with a hint that the call
is long-running, and disable the button while in flight.

### 2.3 Source config (MC-API-03)

The endpoint reads `state.config` from the existing simulation (the one in
the URL path) and replays it N times with new seeds. **The original
simulation's history is not modified.** Each MC run instantiates its own
`SimulationOrchestrator` with a fresh state.

### 2.4 Error responses (MC-API-04)

| Status | Cause |
|--------|-------|
| 404 | `simulation_id` not found in orchestrator (in-memory or DB) |
| 422 | `n_runs` or `max_concurrency` outside accepted range |
| 500 | Engine raised non-recoverable error (e.g. all runs failed) |

---

## 3. Frontend Contract (MC-FE-*)

### 3.1 API client method (MC-FE-01)

**File**: `frontend/src/api/client.ts`

```ts
runMonteCarlo: (id: string, body: { n_runs: number; max_concurrency?: number }) =>
  request<MonteCarloResponse>(
    `/simulations/${id}/monte-carlo`,
    { method: "POST", body: JSON.stringify(body) }
  )
```

### 3.2 Hook (MC-FE-02)

**File**: `frontend/src/api/queries.ts`

`useRunMonteCarlo()` is a `useMutation` (not a query) — explicit user
trigger only, no auto-refetch. On success it invalidates nothing (results
are surfaced inline in the panel).

### 3.3 DecidePanel MC tab UX (MC-FE-03)

**File**: `frontend/src/components/decide/DecidePanel.tsx`

- N-runs slider: range `[2, 50]`, step 1, default 10.
- "Run N Scenarios" button — disabled while `mutation.isPending`.
- During run: button label "Running…"; an indeterminate progress hint
  appears.
- On success: render a result block inline below the button:
  - Viral probability (percentage, large)
  - Expected reach (with P5 / P50 / P95 percentiles)
  - "Open full report →" button (deferred — out of scope; SPEC stub)
- On error: red text near the button (existing `decide-mc-error` testid).
- The legacy `useRunAllSimulation` fallback is **removed** — DecidePanel
  no longer pretends MC is a single-seed run.

### 3.4 Acceptance Criteria

| ID | Criterion | Test |
|----|-----------|------|
| MC-AC-01 | `MonteCarloResult` / `RunSummary` import successfully from `app.engine.diffusion.schema` | `test_29_monte_carlo.py::test_schema_imports` |
| MC-AC-02 | `POST /monte-carlo` rejects `n_runs=1` with 422 | `test_rejects_n_runs_lt_2` |
| MC-AC-03 | `POST /monte-carlo` rejects `n_runs=51` with 422 | `test_rejects_n_runs_gt_50` |
| MC-AC-04 | Response includes all aggregate fields (viral_prob, expected, p5/p50/p95) | `test_response_shape` |
| MC-AC-05 | Original simulation's `step_history` is not mutated by the sweep | `test_does_not_mutate_source` |
| MC-AC-06 | DecidePanel slider min=2 max=50 (was 5–50) | `test_mc_slider_range` |
| MC-AC-07 | DecidePanel calls `runMonteCarlo` mutation (not `runAll`) | `test_mc_calls_real_endpoint` |
| MC-AC-08 | DecidePanel renders viral_probability + expected_reach after success | `test_mc_renders_results` |

---

## 4. Out of Scope (this cycle)

- Background-job queue for >50-run sweeps
- "Open full report →" page (`/simulation/:id/monte-carlo/:runId`)
- Cross-sweep comparison ("MC of scenario A vs MC of scenario B")
- Per-step trajectory variance bands on the live timeline
- Persisting MC results to PostgreSQL (currently transient — re-run to re-view)

These are tracked in `ROADMAP.md` and may earn their own future SPEC.
