# 18 — Frontend Performance Optimization SPEC
Version: 0.4.0 | Status: CURRENT | Updated: 2026-04-08

---

## 0. Related Documents

| Document | Role |
|----------|------|
| **17_PERFORMANCE_SPEC.md** | Backend performance optimization |
| **CLAUDE.md** | Project-wide conventions + current tech stack |

---

## 1. Context

The Prophet frontend renders a real-time simulation dashboard with a **3D WebGL
graph** (`react-force-graph-3d` / three.js, 1,000-5,000 agents), Recharts
metrics, TanStack Query for server state, and WebSocket-driven updates.

> **History:** Prior to v0.3.0 the graph used Cytoscape.js (2D canvas). Findings
> that reference Cytoscape APIs (`cy.batch()`, `cy.add/remove`, `textureOnViewport`,
> etc.) are marked **[SUPERSEDED]** but retained for reference. The 3D-specific
> performance contract lives in §5 (Graph 3D Rendering).

> **TanStack Query migration:** Completed across 3 phases (v0.2.0). Finding
> FE-PERF-09 ("TanStack Query installed but unused") is **[RESOLVED]** — all
> pages now use `useQuery` hooks from `src/api/queries.ts`.

> **ControlPanel refactoring (v0.4.0):** The monolithic `ControlPanel.tsx`
> (was ~785 lines) has been split into 8 files (4 hooks + 4 components). The
> orchestrator shell is now 360 lines. Details in §8.

This SPEC catalogs findings organized by severity and subsystem.

---

## 2. Findings

### CRITICAL — Fix Immediately

#### FE-PERF-01: `steps` array subscription causes cascade re-renders [CRITICAL]

**Files:**
- `SimulationPage.tsx:39` — subscribes to `steps`
- `GraphPanel.tsx:377` — subscribes to `steps`
- `ConversationPanel.tsx:77` — subscribes to `steps`
- `TimelinePanel.tsx:28` — subscribes to `steps`
- `LLMDashboard.tsx:74` — subscribes to `steps`
- `AgentInspector.tsx:105` — subscribes to `steps`

**Problem:** `appendStep` creates a new array reference (`[...state.steps, step]`)
every step. ALL 6 components re-render on every simulation step. At 10x speed =
10 full re-render cascades/second, including the heavyweight GraphPanel.

**Fix:** Use granular selectors:
- Components needing only the latest step → `useSimulationStore((s) => s.latestStep)`
- Components needing count → `useSimulationStore((s) => s.steps.length)`
- Components needing recent N → add `recentSteps` derived slice to store

---

#### FE-PERF-02: `steps` array grows unbounded [CRITICAL]

**File:** `simulationStore.ts:143`

**Problem:** Over 365 steps with `propagation_pairs` (50 entries each), memory
can reach hundreds of MB, causing browser tab crashes.

**Fix:** Sliding window — keep last N steps (e.g., 100):
```typescript
steps: [...state.steps.slice(-(MAX_STEPS_IN_MEMORY - 1)), step]
```
Components needing full history fetch from API via `getSteps()`.

---

#### FE-PERF-03: Loading previous simulation is O(n^2) [CRITICAL → RESOLVED]

**File:** `usePrevSimulations.ts` (was `ControlPanel.tsx:240-249`)

**Problem:** `for (const step of stepsData) { setSteps(step); }` — 365 steps
means 365 state updates, each copying an increasingly large array.

**Fix (implemented):** `setStepsBulk(stepsData)` — single store update via
`useSimulationStore.getState().setStepsBulk(stepsData)` in
`usePrevSimulations.ts:handleLoadPrevSimulation`. Comment `FE-PERF-03` is
present in the file confirming the fix.

---

### HIGH — Fix Before Production

#### FE-PERF-04: SimulationPage subscribes to 12 store slices [HIGH]

**File:** `SimulationPage.tsx:33-44`

**Problem:** Any store change triggers full page reconciliation including
all child components.

**Fix:** Move conditional panels (`LLMDashboard`, `AgentInspector`) into
separate wrapper components subscribing to only their visibility state.
Use `getState()` for action functions.

---

#### FE-PERF-05: LOD zoom handler iterates all nodes without debounce [HIGH]

**File:** `GraphPanel.tsx:476-498`

**Problem:** `applyLOD()` runs on every `zoom` event (continuous during scroll).
At mid-zoom, iterates every node individually to check influence scores.

**Fix:** Debounce `applyLOD` (100ms). Pre-partition nodes into high/low
influence collections at graph init time.

---

#### FE-PERF-06: Adoption update sorts ALL nodes every step [HIGH]

**File:** `GraphPanel.tsx:610-624`

**Problem:** O(n log n) sort of all nodes per step. At 10K nodes, this is
significant CPU work on every step.

**Fix:** Pre-sort nodes once at graph initialization, store in a ref.
On each step, take a different slice length from the pre-sorted array.

---

#### FE-PERF-07: Propagation particles use cy.add/remove [HIGH]

**File:** `GraphPanel.tsx:937-968`

**Problem:** Up to 50 `cy.add()` + `cy.remove()` per step at close-up zoom.
Each add/remove triggers Cytoscape internal element re-indexing.

**Fix:** Use DOM overlay divs for particle animations (absolutely positioned
over canvas) or a pre-allocated pool of hidden particle nodes.

---

#### FE-PERF-08: SimulationPage + heavy graph lib eagerly loaded [HIGH → RESOLVED]

**File:** `App.tsx:17-31`

**Problem:** `SimulationPage` was NOT lazy-loaded. It eagerly imported GraphPanel
→ three.js (~600KB gzipped). All users paid this cost even if they started on
`/projects`.

**Fix (implemented):** ALL 14 page-level routes in `App.tsx` are now wrapped
with `React.lazy()` + a shared `<Suspense>` boundary using a `PAGE_FALLBACK`
skeleton. The three.js + react-force-graph-3d stack is additionally isolated in
the `vendor-three` Rollup chunk (see §9 — Vite Build Config) so it is only
fetched when `GraphPanel` actually mounts.

---

#### FE-PERF-09: TanStack Query installed but unused [HIGH → RESOLVED]

**File:** `src/api/queries.ts`

**Problem:** ~15KB gzipped library loaded for nothing. All fetching was raw
`apiClient` calls in `useEffect` — no caching, no deduplication, no SWR.

**Fix (implemented):** Full TanStack Query migration across all pages and
components (3 phases, v0.2.0). `src/api/queries.ts` exports `useProjects`,
`useSimulations`, `useLLMStats`, `useLLMImpact`, `useEngineControl`, and
10+ additional query/mutation hooks using `useQuery` / `useMutation` from
`@tanstack/react-query`. `useProjectScenarioSync` syncs the TanStack cache
into Zustand so imperative logic throughout ControlPanel continues to work.

---

#### FE-PERF-10: Auto-step interval has no in-flight guard [HIGH → RESOLVED]

**File:** `hooks/useAutoStepLoop.ts`

**Problem:** At 10x speed = 100ms intervals. If `/step` API takes >100ms,
requests pile up with no guard.

**Fix (implemented):** `stepInFlightRef` (`useRef(false)`) in `useAutoStepLoop`
guards each `runStep` invocation. Additionally, `runAllLoadingRef` (a ref
mirroring the `runAllLoading` state) is checked synchronously so the auto-step
loop stops immediately when RunAll starts — closing the one-render gap where
React state propagation could allow a race. Pattern:
```typescript
if (runAllLoadingRef.current) return;   // sync check
if (stepInFlightRef.current) return;    // in-flight guard
stepInFlightRef.current = true;
try { ... } finally { stepInFlightRef.current = false; }
```

---

#### FE-PERF-11: WebSocket reconnect() does not actually reconnect [HIGH]

**File:** `useSimulationSocket.ts:88-95`

**Problem:** `reconnect()` closes socket and resets `retryExhausted`, but
`simulationId` doesn't change → useEffect does NOT re-trigger.

**Fix:** Add `reconnectCounter` state to force effect re-run.

---

### MEDIUM — Should Fix

#### FE-PERF-12: No React.memo on presentational components [MEDIUM]

**Problem:** `CommunityRow`, `ControlButton`, `StatTile`, `SentimentBar`,
`MetricCard` all re-render when parent re-renders even with unchanged props.

**Fix:** Wrap pure presentational components with `React.memo`.

---

#### FE-PERF-13: Edge coloring loop outside cy.batch() [MEDIUM]

**File:** `GraphPanel.tsx:502-510`

**Fix:** Wrap in `cy.batch()`.

---

#### FE-PERF-14: Community highlight not batched [MEDIUM]

**File:** `GraphPanel.tsx:628-641`

**Fix:** Wrap individual `node.style("opacity", ...)` calls in `cy.batch()`.

---

#### FE-PERF-15: Recharts data not memoized [MEDIUM]

**File:** `AnalyticsPage.tsx:38-49`

**Fix:** Wrap `buildAdoptionData(steps)` in `useMemo`.

---

#### FE-PERF-16: Chart components not isolated with memo [MEDIUM]

**Fix:** Wrap Recharts chart sections in `React.memo` components.

---

#### FE-PERF-17: emergentEvents array grows unbounded [MEDIUM]

**File:** `simulationStore.ts:150-152`

**Fix:** Cap at 50 most recent events.

---

#### FE-PERF-18: Propagation arc DOM elements not cleaned on unmount [MEDIUM]

**File:** `GraphPanel.tsx:851-864`

**Fix:** Track created DOM elements in a ref, remove in cleanup.

---

#### FE-PERF-19: Render-blocking font imports [MEDIUM]

**File:** `index.css:1-3`

**Fix:** Move to `<link rel="preload">` in index.html or self-host fonts.

---

#### FE-PERF-20: Monolithic store shape [MEDIUM]

**File:** `simulationStore.ts`

**Fix:** Split into `useSimulationDataStore`, `useUIStore`, `useProjectStore`.

---

#### FE-PERF-21: ConversationPanel re-derives latestStep [MEDIUM]

**File:** `ConversationPanel.tsx:77-78`

**Fix:** Use `useSimulationStore((s) => s.latestStep)` directly.

---

### LOW — Nice to Have

#### FE-PERF-22: Inline style objects block memoization [LOW]
#### FE-PERF-23: Verify Recharts chunk splitting in production [LOW]
#### FE-PERF-24: Verify lucide-react tree-shaking [LOW]
#### FE-PERF-25: Inline computation in useEffect dependency [LOW]
#### FE-PERF-26: FPS counter runs continuously when idle [LOW]
#### FE-PERF-27: Hover handler potential forced reflow [LOW]
#### FE-PERF-28: Array spread copy in appendStep [LOW]
#### FE-PERF-29: Cascade animation re-sorts all nodes [LOW]

---

## 3. Priority Tiers

### Tier A — Critical Path (implement first)

| ID | Fix | Estimated Gain | Effort | Status |
|----|-----|---------------|--------|--------|
| FE-PERF-01 | Granular store selectors for `steps` | **Eliminates 6 cascade re-renders/step** | Medium | Open |
| FE-PERF-02 | Sliding window on `steps` array | **Prevents 100MB+ memory leak** | Low | Open |
| FE-PERF-03 | Bulk `setStepsBulk()` action | **O(n^2) → O(n) for load** | Low | **RESOLVED** |
| FE-PERF-10 | In-flight guard on auto-step + runAllLoadingRef | **Prevents request pileup** | Low | **RESOLVED** |

### Tier B — High Value (implement second)

| ID | Fix | Estimated Gain | Effort | Status |
|----|-----|---------------|--------|--------|
| FE-PERF-08 | Lazy-load all page routes + vendor-three chunk | **600KB+ off initial bundle** | Low | **RESOLVED** |
| FE-PERF-09 | Full TanStack Query migration | **+caching, deduplication, SWR** | High | **RESOLVED** |
| FE-PERF-05 | Debounce LOD + pre-partition nodes | **Smooth zoom at 10K nodes** | Medium | Open (2D-only; 3D uses G3D rules) |
| FE-PERF-11 | Fix WebSocket reconnect | **Reliability fix** | Low | Open |

### Tier C — Should Fix

| ID | Fix | Estimated Gain | Effort | Status |
|----|-----|---------------|--------|--------|
| FE-PERF-04 | Split SimulationPage subscriptions | **Fewer parent re-renders** | Medium | Open |
| FE-PERF-12 | React.memo on presentational components | **Fewer child re-renders** | Low | Open |
| FE-PERF-17 | Cap emergentEvents | **Prevent minor memory growth** | Low | Open |
| FE-PERF-21 | Use latestStep selector | **1 fewer full-array subscription** | Low | Open |

> **Note on FE-PERF-05/06/07/13/14:** These findings target the Cytoscape.js
> (2D) graph path which is **[SUPERSEDED]** by the react-force-graph-3d
> renderer. The 3D performance contract is now §5. Cytoscape remains in use
> only for `FactionMapView` and `EgoGraph` sub-views, not the main graph panel.

---

## 4. Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| FE-PERF-AC-01 | 365-step simulation memory usage | < 50MB total JS heap |
| FE-PERF-AC-02 | Step update re-render count | <= 3 components re-render per step |
| FE-PERF-AC-03 | Load 365-step history | < 500ms, single store update |
| FE-PERF-AC-04 | 10x speed auto-step | No request pileup, max 1 in-flight |
| FE-PERF-AC-05 | Zoom interaction at 10K nodes | >= 30fps during continuous zoom |
| FE-PERF-AC-06 | Initial bundle (excl. SimulationPage) | < 200KB gzipped |
| FE-PERF-AC-07 | WebSocket reconnect button | Establishes new connection |
| FE-PERF-AC-08 | Node adoption update per step | No sorting, O(1) slice from pre-sorted |

---

## 5. Graph 3D Rendering (three.js / react-force-graph-3d)

> **Scope:** the AI Social World panel (Zone 2 Center) in `/simulation`.
> Renderer: `GraphPanel.tsx` — backed by `react-force-graph-3d` (three.js WebGL).

The 2D Cytoscape renderer was replaced by a 3D WebGL force-directed graph
in 2026-04. This section documents the visual + performance contract so
regressions are caught at review time.

### 5.1 Visual Contract

1. **Nodes are spheres in 3D space.** Radius is derived from
   `influence_score` (via `nodeVal`). Community determines color.
2. **Node color = community color** from `@/config/constants#COMMUNITIES`.
   The Communities legend (left panel) and the graph MUST share the same
   palette — no separate hardcoded colors. Single source of truth.
3. **Edge color = source node's community color** at reduced alpha (~0.35)
   for intra-community edges. Inter-community and bridge edges use neutral
   muted gray (`rgba(148,163,184, α)`) so they read as connective tissue
   without competing with community hues.
4. **Adopted nodes** glow green (`#22c55e`) on the "adopted" highlight set
   regardless of community color. The set is recomputed each simulation
   step but the graph topology is NOT rebuilt.
5. **Community highlight dim:** when `highlightedCommunity` is set, nodes
   and edges that don't match are dimmed to `rgba(30,41,59,0.08)` — they
   must remain visible (not hidden) so the overall structure stays legible.

### 5.2 Interaction Contract

| Input | Action |
|-------|--------|
| **Left-drag** | Orbit camera around graph center |
| **Scroll wheel** | Zoom in / out |
| **Right-drag** | Pan camera |
| **Click node** | Navigate to `/agents/{agent_id}` |
| **Hover node** | Show tooltip (label + community + influence) |
| **Click background** | Clear community highlight |

Left-drag rotation is REQUIRED — `controlType="orbit"` (three.js
OrbitControls). Trackball-style controls are NOT acceptable because they
allow free-roll which disorients the user.

### 5.3 Performance Contract

| ID | Rule | Rationale |
|----|------|-----------|
| G3D-01 | **No `nodeThreeObject` callback.** Use the built-in instanced sphere path via `nodeColor` + `nodeVal` callbacks. | Per-node `THREE.Mesh` creates thousands of draw calls; instanced path = 1 draw call for all nodes. |
| G3D-02 | `nodeResolution` MUST scale with node count: `10` (< 500), `6` (500-2000), `4` (> 2000). | Triangles per sphere dominates fragment cost on zoom. |
| G3D-03 | `linkDirectionalParticles` MUST be `0` when `linkCount >= 200`. | Particle animation is the single biggest frame-time contributor. |
| G3D-04 | `rendererConfig.antialias` MUST be `false` when `nodeCount > 500`. | Biggest single win on integrated GPUs; MSAA ~2x fragment cost. |
| G3D-05 | `cooldownTicks` MUST be bounded (`150 / 80 / 40` for small/large/huge) and `d3AlphaDecay >= 0.04`. | Force simulation must stop; otherwise every frame runs physics. |
| G3D-06 | Per-step adoption highlight MUST NOT mutate `graphData`. Use a `useRef<Set<string>>` + `fgRef.current.refresh()`. | Rebuilding `graphData` restarts the force simulation on every step. |
| G3D-07 | Link colors MUST be O(1) — source community is cached at load time on `link._srcCommunity` to avoid branching on `link.source` type (string vs node object) per frame. | `linkColor` is called for every link every frame. |
| G3D-08 | `enableNodeDrag` MUST be `false`. | Drag interferes with orbit controls and restarts the force simulation. |
| G3D-09 | Container element MUST use inline `position: absolute; inset: 0; width: 100%; height: 100%`. Tailwind `absolute inset-0` alone is forbidden — it can collapse to `height: 0` inside certain flex parents, which causes the WebGL canvas to render nothing (historical "agents stuck in bottom-left" bug). | Inline sizing is immune to the parent/style interaction. |

### 5.4 Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| G3D-AC-01 | 1000-node graph, continuous mouse wheel zoom | >= 45 fps (no perceptible stutter) |
| G3D-AC-02 | 1000-node graph, left-drag orbit | >= 45 fps |
| G3D-AC-03 | Community legend color for "Alpha" | **Identical** to `#COMMUNITIES[0].color` AND to the on-graph node color for any alpha node |
| G3D-AC-04 | Per-step adoption highlight | Does not rebuild `graphData`; physics stays at rest |
| G3D-AC-05 | Bottom-left controls hint | Visible and reads "Left-drag: rotate · Scroll: zoom · Right-drag: pan" |
| G3D-AC-06 | Click node on canvas | Navigates to `/agents/{id}` |
| G3D-AC-07 | `data-testid="graph-cytoscape-container"` | Present on the WebGL mount point (regression-tested) |

---

## 6. AgentDetailPage — Real-Data-Only Contract

> **Scope:** `frontend/src/pages/AgentDetailPage.tsx` — the `/agents/:agentId` route
> opened when a user clicks an agent in the 3D graph.

The page used to initialise its `agent` state to a hard-coded `MOCK_AGENT`
constant and overwrite it when the API fetch resolved. Whenever the fetch
was slow, failed, or never fired (no active simulation in store), the user
saw mock content (e.g. "Daniel Hayes / Alpha Community / 78% openness")
labelled with the URL's real agent UUID — confusing and untrustworthy.

### 6.1 Contract — what MUST hold

| ID | Rule |
|----|------|
| AD-01 | The component MUST NOT contain `MOCK_AGENT`, `MOCK_INTERACTIONS`, `MOCK_CONNECTIONS`, or `MOCK_MESSAGES` constants. The body field for an agent (avatar, community, personality, interactions, messages, connections) MUST come from API responses or computed real state. |
| AD-02 | The `agent` state MUST be `AgentView \| null` and initialised to `null`. Never `{...MOCK_AGENT, id: agentId}`. |
| AD-03 | The render function MUST short-circuit on three gates BEFORE rendering the body: (a) **no active simulation** (`simulationId` from store is null), (b) **loading** (`agentLoading === true \|\| agent === null`), (c) **not found** (`agentNotFound === true`). Each gate has its own dedicated screen — none of them render the body with a stale `agent`. |
| AD-04 | The agent fetch MUST run `apiClient.agents.get` and `apiClient.network.get` in parallel via `Promise.all`. The network response provides the human-friendly `community_name` (e.g. `early_adopters`, `bridge_node`) which is passed to `apiToAgent` as a second-argument override. The agent endpoint alone returns the community as a UUID, which is unfit for display. |
| AD-05 | `apiToAgent` MUST NOT fall back to mock fields. `memorySummary` for an agent with no memories MUST read "No recorded memories yet — agent has not produced any episodic events in this run." (or equivalent explicit empty-state copy) — never `MOCK_AGENT.memorySummary`. |
| AD-06 | `agentNumber` MUST be derived deterministically from the agent UUID (e.g. first 4 hex chars after stripping dashes). It MUST never be empty. |
| AD-07 | On fetch failure, the page MUST set `agentNotFound = true` and render an explicit "Agent not found" screen showing the URL's agent id and a button back to `/simulation`. It MUST NOT silently render a body. |

### 6.2 Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| AD-AC-01 | Click any agent node in the 3D graph | Page renders with the clicked agent's real `agent_id`, real personality, real influence_score, real community name |
| AD-AC-02 | Open `/agents/<uuid>` directly with no simulation in store | Page renders the "No active simulation" gate, NOT the body |
| AD-AC-03 | Open `/agents/<uuid>` for an id that does not exist in the active sim | Page renders the "Agent not found" gate showing the input UUID |
| AD-AC-04 | `grep -rn "MOCK_AGENT\|MOCK_INTERACTIONS\|MOCK_CONNECTIONS\|MOCK_MESSAGES" frontend/src/pages/AgentDetailPage.tsx` | Returns nothing (constants and references both removed) |
| AD-AC-05 | Vitest `AgentDetail.test.tsx` | All 17 tests pass; tests provide a successful agent fetch mock and seed `simulationStore` so the loading gate resolves |

---

## 7. SimulationPage — Lazy GraphPanel + Auto-Provision Scenario

### 7.1 GraphPanel Lazy Loading

`SimulationPage` MUST `React.lazy` the `GraphPanel` import. Rationale:

- `react-force-graph-3d` pulls in `three.js` (~600KB gzipped). Eagerly
  loading it on every page hit (including the placeholder shown when
  no simulation is active) wastes the budget and slows TTI.
- Lazy loading defers the chunk until a simulation is actually loaded.
- Tests that touch the rendered GraphPanel MUST use `await screen.findByTestId(...)`
  (not `getByTestId`) so React Suspense has a chance to resolve before the
  assertion runs. See the `Zone 2: AI Social World Graph Engine (3D)` block
  in `SimulationMain.test.tsx` for the canonical pattern.

### 7.2 Scenario Auto-Provisioning

When a user picks a scenario in the ControlPanel dropdown that has no
linked simulation yet, `handleScenarioChange` MUST:

1. Call `apiClient.projects.runScenario(projectId, scenarioId)` — backend
   builds a `SimulationConfig` from `scenario.config`, creates the in-memory
   state, persists, starts the run, and links `scenario.simulation_id`.
2. Fetch the resulting simulation via `apiClient.simulations.get(newSimId)`.
3. `setSimulation(sim)` + `setStatus(SIM_STATUS.RUNNING)`.
4. Locally update the `scenarios` array entry with the new `simulation_id`
   so a subsequent dropdown selection takes the simple-load path.

The user MUST NOT need to click a separate "Create Simulation" button
to start a scenario from the dropdown. "Create Simulation" remains as an
explicit action for creating new empty simulations outside any scenario.

### 7.3 persist_creation FK Safety

`SimulationPersistence.persist_creation` mixes ORM `session.add` with bulk
Core `session.execute(insert(...))`. The bulk Core path triggers an
autoflush that does NOT honour FK dependency ordering, so a Campaign row
can flush before the Simulation row it points to and produce a
`campaigns_simulation_id_fkey` violation. To prevent this:

| ID | Rule |
|----|------|
| PC-01 | The `Simulation` row MUST be added with `session.add(sim_row)` followed by an **explicit `await session.flush()`** before any other `add` or bulk insert. |
| PC-02 | The `Campaign` row (if any) MUST also be flushed explicitly so subsequent campaign-referencing inserts see it. |
| PC-03 | The outer `try/except` MUST `raise` after rollback. Swallowing the error lets callers (e.g. `run_scenario`) blindly write a `scenarios.simulation_id` FK to a row that does not exist, producing a confusing second FK error several layers up the stack. |

### 7.4 Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| SP-AC-01 | Pick project + new scenario in dropdown | Play button is clickable within ~1s of scenario selection (no extra "Create Simulation" click required) |
| SP-AC-02 | `POST /projects/{pid}/scenarios/{sid}/run` against a fresh scenario | Returns 200 with `{simulation_id, status: "running"}`; the linked row exists in the `simulations` table |
| SP-AC-03 | `frontend/src/__tests__/SimulationMain.test.tsx` | All Zone 2 (3D) tests use `findByTestId` / `findByText` to wait for the lazy `GraphPanel` chunk |
| SP-AC-04 | `npx vitest run` from `frontend/` | 27 test files, 521+ tests, all green |

---

## 8. ControlPanel Refactoring

> **Context:** Prior to this refactoring `ControlPanel.tsx` was a ~785-line
> monolith that combined auto-step loop logic, playback handlers, keyboard
> shortcuts, project/scenario API calls, and Load Previous/Compare state into
> a single component. It was split in April 2026.

### 8.1 File Layout

| File | Lines | Responsibility |
|------|-------|----------------|
| `control/ControlPanel.tsx` | 360 | Layout orchestrator — renders bar, wires hooks |
| `control/hooks/useAutoStepLoop.ts` | 73 | Auto-step `setInterval`, in-flight guard, runAllLoadingRef check |
| `control/hooks/usePlaybackControls.ts` | 141 | Play/Pause/Step/Reset/RunAll handlers + keyboard shortcuts |
| `control/hooks/useProjectScenarioSync.ts` | 193 | Project/scenario loading, auto-provision scenario, TanStack→Zustand sync |
| `control/hooks/usePrevSimulations.ts` | 64 | Load Previous list state + `handleLoadPrevSimulation` (bulk load) |
| `control/ControlButton.tsx` | 38 | Pure presentational button wrapper |
| `control/LoadPrevDropdown.tsx` | 71 | Load Previous dropdown UI |
| `control/CompareDropdown.tsx` | 72 | Compare dropdown UI |

### 8.2 Hook Contracts

#### `useAutoStepLoop(runAllLoading, runAllLoadingRef)`

Manages the `setInterval` that fires `apiClient.simulations.step()` while
`status === SIM_STATUS.RUNNING`. Two guards prevent pileup:

1. `stepInFlightRef` — skips the tick if a previous step request is
   still in flight (FE-PERF-10 fix).
2. `runAllLoadingRef` — ref (not state) mirror of `runAllLoading`. Checked
   synchronously inside the interval callback to stop auto-step the moment
   RunAll begins, before React state propagation has completed.

The interval is cleared and restarted whenever `status`, `speed`, or
`runAllLoading` changes.

#### `usePlaybackControls()`

Returns `{ isRunning, runAllLoading, runAllLoadingRef, handlePlay, handlePause, handleStep, handleReset, handleRunAll }`.

Key patterns:
- All handlers call `useSimulationStore.getState()` (not captured state) so
  keyboard shortcut closures always see the current simulation ID.
- `handlePlay` implements a 409-recovery path: if `resume` returns a
  409/state-mismatch error, it falls back to `stop` → `start`.
- **Keyboard shortcut modal guard**: the `keydown` handler checks
  `document.querySelector("[role='dialog']")` before acting. When any
  modal/dialog is open, `Escape` closes the dialog (browser default) rather
  than resetting the simulation.

#### `useProjectScenarioSync()`

Returns `{ creating, activeScenarioId, handleProjectChange, handleScenarioChange, handleNewScenario, handleNewSimulation, handleClone }`.

- Uses `useProjects()` (TanStack Query) and syncs the result into Zustand via
  `setProjects()` so the rest of the codebase keeps reading from the store.
- `activeScenarioId` is derived (not state) by matching
  `simulation.simulation_id` against the `scenarios` list — keeps the dropdown
  controlled on direct `/simulation/:id` navigation.
- `handleScenarioChange` auto-provisions a simulation via
  `POST /projects/{pid}/scenarios/{sid}/run` when the chosen scenario has no
  `simulation_id` yet (SP-AC-01 contract).

#### `usePrevSimulations()`

Returns list + open/search state for the Load Previous dropdown.
`handleLoadPrevSimulation` calls `setStepsBulk` for O(n) bulk load (FE-PERF-03
fix). `filteredPrevSimulations` is `useMemo`-derived from search query.

### 8.3 runAllLoadingRef Race Prevention

`runAllLoading` is React state; `runAllLoadingRef` is a `useRef` that mirrors
it. The sequence is:

```typescript
// handleRunAll (usePlaybackControls)
runAllLoadingRef.current = true;   // ← sync, visible immediately
setRunAllLoading(true);            // ← async React state update

// inside auto-step interval (useAutoStepLoop)
if (runAllLoadingRef.current) return; // ← ref check catches the gap
```

This prevents a single extra `/step` call during the one-render gap between
`setRunAllLoading(true)` and the re-render that propagates the new value to
`useAutoStepLoop`.

### 8.4 LLM Stats Polling Debounce

**File:** `pages/GlobalMetricsPage.tsx:97-111`

LLM stats (`GET /simulations/{id}/llm/stats`) are polled at most once every
5 simulation steps to avoid flooding the backend during fast simulations
(speed 10 = 100ms/step would otherwise generate 10 req/s):

```typescript
// Poll LLM stats at most every 5 steps
if (latestStep > 0 && latestStep % 5 !== 0) return;
```

The constant `LLM_STATS_POLL_INTERVAL_MS = 5_000` in `src/config/constants.ts`
documents the intent; the step-modulus guard is the actual implementation.

### 8.5 Zustand Selector Stability

ControlPanel and its hooks read Zustand state exclusively via per-field
selector functions (e.g. `useSimulationStore((s) => s.status)`) rather than
inline object destructure (`useSimulationStore((s) => ({ a: s.a, b: s.b })`).
Each selector returns a stable primitive or reference, so unrelated store
mutations do NOT trigger re-renders in that hook/component.

Action functions (setters) are also read via selectors
(`useSimulationStore((s) => s.setSpeed)`) rather than calling `getState()`
inline, which would create a new function reference on every render. For
one-off imperative calls inside event handlers, `useSimulationStore.getState()`
is used directly to avoid subscribing to the whole store.

### 8.6 EngineControlPanel Modal Conversion

`EngineControlPanel` was previously rendered as an inline dropdown panel.
It is now a **centered modal popup** (`fixed inset-0 z-50 flex items-center
justify-center` overlay with `role="dialog"`). The `isOpen` prop controls
visibility via an early `if (!isOpen) return null` guard.

The modal-guard in `usePlaybackControls` (§8.2) ensures that pressing
`Escape` while the Engine Control modal is open closes the modal instead of
resetting the simulation.

### 8.7 Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| CP-AC-01 | `ControlPanel.tsx` line count | ≤ 400 lines |
| CP-AC-02 | Auto-step at 10x speed while RunAll is active | No extra `/step` calls fired after RunAll begins |
| CP-AC-03 | Press `Escape` while EngineControlPanel is open | Modal closes; simulation is NOT reset |
| CP-AC-04 | Press `Space` while an `<input>` is focused | No play/pause action triggered |
| CP-AC-05 | Load Previous simulation (365 steps) | Single `setStepsBulk` call, no per-step loop |
| CP-AC-06 | LLM stats requests at 10x speed (100ms/step) | At most 1 request per 5 steps (≤ 2 req/s) |
| CP-AC-07 | Pick scenario with no simulation_id | Simulation auto-provisioned via `runScenario`, Play button enabled ≤1s |

---

## 9. Vite Build Configuration

**File:** `frontend/vite.config.ts`

### 9.1 Named Chunk Strategy

Rollup `manualChunks` splits heavy third-party libraries into stable named
chunks. Stable filenames survive route changes in the browser cache, and the
chunks are only fetched when the code path that imports them is actually
executed (lazy routes, lazy components).

| Chunk | Libraries included | Trigger |
|-------|--------------------|---------|
| `vendor-three` | `three`, `react-force-graph-3d`, `3d-force-graph`, `three-render-objects`, `three-forcegraph` | `GraphPanel` mounts (~1 MB raw) |
| `vendor-cytoscape` | `cytoscape` (and plugins) | `FactionMapView` or `EgoGraph` mounts |
| `vendor-recharts` | `recharts`, `victory-vendor` | Any chart component mounts |
| `vendor-d3` | `d3-*` (not already in another vendor chunk) | Various |

### 9.2 Bundle Budget

| Setting | Value | Rationale |
|---------|-------|-----------|
| `chunkSizeWarningLimit` | **600 KB** | Raised from Vite default 500 KB so simulation chunk warning only fires for regressions, not normal three.js growth |

### 9.3 Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| BC-AC-01 | `npx vite build` output — initial bundle (no simulation pages) | `index` chunk < 200 KB gzipped |
| BC-AC-02 | `vendor-three` chunk present in dist | Yes — confirms three.js is NOT in the initial bundle |
| BC-AC-03 | Navigating to `/metrics` before `/simulation` | No `vendor-three` request in Network tab |
| BC-AC-04 | FE-PERF-23: Recharts chunk in build output | `vendor-recharts` chunk present |

---

## 10. SimulationListPage — Project Scoping & Filtering

> **Version: 0.1.0 (2026-04-11)** — added to close a UX gap where
> `/simulation` showed a flat list with no project context and the
> "New Simulation" button dropped users into `/setup` with no project
> pre-selected, forcing them to discover the requirement mid-form.

### 10.1 Problem

Before this section, `SimulationListPage` at `/simulation` had three UX
holes:

1. **Flat list, no project context.** Rows displayed `sim.name` and
   `sim.simulation_id` but not `sim.project_id` or project name, so
   users couldn't tell which project owned which simulation.
2. **Context-free "New Simulation" button.** Clicking it navigated to
   `/setup` with no project context. Users then discovered that
   "Project" was the first required field buried inside the
   `CampaignSetupPage` form, with a `disabled` submit button until it
   was filled.
3. **Unused `/setup/:projectId` route variant.** `CampaignSetupPage`
   already supported URL-scoped project pre-selection via
   `useParams<{ projectId: string }>` but no caller used it from the
   `/simulation` entry point.

### 10.2 Contract

**File:** `frontend/src/pages/SimulationListPage.tsx`

#### SL-01 — Project filter dropdown in header

The header row MUST render a project filter dropdown to the left of
the "New Simulation" button.

```
┌──────────────────────────────────────────────────────┐
│ Simulations           [Project: All ▾]  [+ New Sim]  │
├──────────────────────────────────────────────────────┤
│ ...                                                   │
└──────────────────────────────────────────────────────┘
```

- Dropdown options are built from `useProjects()` (TanStack Query).
- The first option is `"All projects"` with value `null` (the default
  on page mount).
- Subsequent options are the user's projects, sorted by `name`
  alphabetically.
- While the projects query is loading, the dropdown MUST render the
  "All projects" option only (no spinner inside the trigger — the
  list loading spinner is sufficient).

#### SL-02 — Filter applied to the simulation list

When a project is selected in the dropdown:

- The displayed simulation list MUST be filtered client-side to
  `sim.project_id === selectedProjectId`.
- The list header count (if present) reflects the filtered count, not
  the total.
- Filter state is local component state (`useState`). It is NOT
  persisted across navigation — arriving at `/simulation` always
  resets to "All projects".

> Client-side filter rationale: projects typically number in the
> single-to-low-double digits and simulations in the low-to-mid
> hundreds. A server-side `GET /simulations?project_id=` is not worth
> the round-trip latency at this scale.

#### SL-03 — "New Simulation" button routing

The "New Simulation" button's navigation target MUST depend on the
filter state:

| Filter state | Click target |
|---|---|
| "All projects" (null) | `/setup` (current behavior — form will require project) |
| Specific project selected | `/setup/:projectId` (project pre-selected) |

This applies to both copies of the CTA (the header button AND the
empty-state CTA inside the list body).

#### SL-04 — Per-row project name

Every simulation row MUST display the owning project's name **inline
below the simulation name**, alongside the `simulation_id`, separated
by a middle-dot. This placement is visible at all breakpoints — no
responsive hiding — so the "which project does this belong to?"
question is always answerable at a glance.

```
┌──────────────────────────────────────────────────┐
│ Beverage Launch                       Step 5/50  │
│ sim-abc123 · Q4 Campaigns                         │
└──────────────────────────────────────────────────┘
```

Lookup: build a `Map<string, string>` from `projects.map(p => [p.project_id, p.name])`
once per render (memo). Rows whose `project_id` has no matching
project (orphaned simulations, race conditions) MUST render only the
`simulation_id` — no middle-dot, no `"—"`, no crash. Rows whose sim
object has no `project_id` at all follow the same fallback.

#### SL-05 — Empty-state copy varies by filter

The empty state text MUST reflect the filter:

- **No filter + zero sims**: "No simulations yet" + "Create your first
  simulation to see it here." + CTA "Create Simulation"
- **Filter applied + zero matching sims**: "No simulations in this
  project" + "This project doesn't have any simulations yet." + CTA
  "Create in this project" (links to `/setup/:projectId`)

### 10.3 Non-goals

- **No cascading API changes.** `apiClient.simulations.list()` MUST
  NOT gain a `project_id` parameter in this revision. Filtering is
  client-side per SL-02.
- **No change to `/projects` or `/projects/:id/scenarios` pages.**
  Their role (project-first authoring) is preserved. This section only
  adds a project *lens* to the existing `/simulation` index.
- **No persistent filter state.** No localStorage, no URL query param.
  Keeping state ephemeral avoids stale filters confusing returning users.

### 10.4 Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| SL-AC-01 | Mount `SimulationListPage` with projects + sims | Filter dropdown renders with "All projects" selected by default |
| SL-AC-02 | Select a specific project from the dropdown | List updates to show only sims where `project_id === selectedProjectId` |
| SL-AC-03 | Click "New Simulation" while "All projects" selected | Navigate to `/setup` |
| SL-AC-04 | Click "New Simulation" while project `proj-q4` selected | Navigate to `/setup/proj-q4` |
| SL-AC-05 | Render a sim whose `project_id` matches a known project | Row shows `{simulation_id} · {project_name}` inline below the sim name |
| SL-AC-06 | Render a sim whose `project_id` has no matching project (orphan) | Row shows `simulation_id` only, no middle-dot (no crash) |
| SL-AC-07 | Filter by a project with zero sims | Empty state shows "No simulations in this project" + "Create in this project" CTA |
| SL-AC-08 | Project query loading | Dropdown renders "All projects" option only; does not crash |
| SL-AC-09 | Projects query error | Dropdown falls back to "All projects" only; list still renders from sims query |

### 10.5 Test Coverage

New test file: `frontend/src/__tests__/SimulationListPage.test.tsx`

Must cover:

- All nine acceptance criteria SL-AC-01 through SL-AC-09.
- Mock both `useSimulations` and `useProjects` via `vi.mock('@/api/queries', ...)`.
- Assert `useNavigate` mock receives the expected paths for SL-AC-03 and SL-AC-04.
