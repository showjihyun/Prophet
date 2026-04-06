# 18 — Frontend Performance Optimization SPEC
Version: 0.1.0 | Status: DRAFT

---

## 0. Related Documents

| Document | Role |
|----------|------|
| **07_FRONTEND_SPEC.md** | Component specs, GraphPanel, ControlPanel |
| **17_PERFORMANCE_SPEC.md** | Backend performance optimization |

---

## 1. Context

The Prophet frontend renders a real-time simulation dashboard with a Cytoscape.js
graph (1,000-10,000 nodes), Recharts metrics, and WebSocket-driven updates.
Profiling reveals that the `steps` array subscription pattern causes cascading
re-renders across 6+ components on every simulation step, and the steps array
grows unbounded during long simulations.

This SPEC catalogs **29 findings** organized by severity and subsystem.

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

#### FE-PERF-03: Loading previous simulation is O(n^2) [CRITICAL]

**File:** `ControlPanel.tsx:240-249`

**Problem:** `for (const step of stepsData) { setSteps(step); }` — 365 steps
means 365 state updates, each copying an increasingly large array.

**Fix:** Add `setStepsBulk(steps: StepResult[])` action to store that sets
the entire array at once.

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

#### FE-PERF-08: SimulationPage + Cytoscape eagerly loaded [HIGH]

**File:** `App.tsx:12`

**Problem:** `SimulationPage` is NOT lazy-loaded. It eagerly imports GraphPanel
→ Cytoscape.js (~400KB). All users pay this cost even if they start on
`/projects`.

**Fix:** `const SimulationPage = lazy(() => import("./pages/SimulationPage"))`.
Additionally, lazy-load `LLMDashboard` and `AgentInspector` within SimulationPage.

---

#### FE-PERF-09: TanStack Query installed but unused [HIGH]

**File:** `main.tsx` (QueryClientProvider), `useSimulationData.ts` (unused hooks)

**Problem:** ~15KB gzipped library loaded for nothing. All fetching is raw
`apiClient` calls in `useEffect` — no caching, no deduplication, no SWR.

**Fix:** Either migrate data fetching to TanStack Query hooks, or remove
the dependency.

---

#### FE-PERF-10: Auto-step interval has no in-flight guard [HIGH]

**File:** `ControlPanel.tsx:110-127`

**Problem:** At 10x speed = 100ms intervals. If `/step` API takes >100ms,
requests pile up with no guard.

**Fix:** Add `inFlightRef` to skip interval tick if previous call is pending:
```typescript
const inFlightRef = useRef(false);
const runStep = async () => {
  if (inFlightRef.current) return;
  inFlightRef.current = true;
  try { ... } finally { inFlightRef.current = false; }
};
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

| ID | Fix | Estimated Gain | Effort |
|----|-----|---------------|--------|
| FE-PERF-01 | Granular store selectors for `steps` | **Eliminates 6 cascade re-renders/step** | Medium |
| FE-PERF-02 | Sliding window on `steps` array | **Prevents 100MB+ memory leak** | Low |
| FE-PERF-03 | Bulk `setStepsBulk()` action | **O(n^2) → O(n) for load** | Low |
| FE-PERF-10 | In-flight guard on auto-step | **Prevents request pileup** | Low |

### Tier B — High Value (implement second)

| ID | Fix | Estimated Gain | Effort |
|----|-----|---------------|--------|
| FE-PERF-06 | Pre-sort nodes once, reuse across steps | **O(n log n) → O(1) per step** | Low |
| FE-PERF-08 | Lazy-load SimulationPage | **400KB off initial bundle** | Low |
| FE-PERF-05 | Debounce LOD + pre-partition nodes | **Smooth zoom at 10K nodes** | Medium |
| FE-PERF-07 | DOM overlay particles instead of cy.add | **50 fewer cy mutations/step** | Medium |
| FE-PERF-11 | Fix WebSocket reconnect | **Reliability fix** | Low |

### Tier C — Should Fix

| ID | Fix | Estimated Gain | Effort |
|----|-----|---------------|--------|
| FE-PERF-04 | Split SimulationPage subscriptions | **Fewer parent re-renders** | Medium |
| FE-PERF-09 | Remove unused TanStack Query or migrate | **-15KB or +caching** | High |
| FE-PERF-12 | React.memo on presentational components | **Fewer child re-renders** | Low |
| FE-PERF-13+14 | cy.batch() wrappers | **Fewer Cytoscape repaints** | Low |
| FE-PERF-17 | Cap emergentEvents | **Prevent minor memory growth** | Low |
| FE-PERF-21 | Use latestStep selector | **1 fewer full-array subscription** | Low |

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
