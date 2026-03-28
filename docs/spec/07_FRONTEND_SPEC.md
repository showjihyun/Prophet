# 07 — Frontend SPEC (React 18)
Version: 0.1.1 | Status: DRAFT

---

## 1. Tech Stack

| Library | Version | Purpose |
|---------|---------|---------|
| React | 18.x | UI framework |
| TypeScript | 5.x | Type safety |
| Vite | 5.x | Build tool |
| Cytoscape.js | 3.x | Social graph visualization |
| Recharts | 2.x | Timeline + metric charts |
| Zustand | 4.x | Global state management |
| TanStack Query | 5.x | Server state + API fetching |
| Tailwind CSS | 3.x | Styling |
| shadcn/ui | latest | UI component library |
| React Router | 6.x | Page routing |

---

## 2. Pages

### `/` — Home / Simulation List
- List of simulation runs (status badges, creation date, campaign name)
- Button: "New Simulation"
- Quick stats: total runs, active simulations

### `/simulations/new` — Campaign Setup Page
- Form: simulation name, campaign config (message, budget, channels)
- Community config (use defaults or customize agent counts)
- LLM provider selection (Ollama / Claude / OpenAI)
- Advanced settings: max_steps, personality_drift, random_seed
- Button: "Create & Configure"

### `/simulations/:id` — Main Simulation Page
- **Full-screen layout** with 4 panels (see §3)
- WebSocket connection to real-time step updates

### `/simulations/:id/analytics` — Post-run Analytics
- Full metric history charts
- Emergent event timeline
- Community adoption comparison
- Monte Carlo results (if run)

### `/simulations/:id/compare/:other_id` — Scenario Comparison
- Side-by-side metric charts
- Winner highlight
- Emergent event diff

---

## 3. Main Simulation Page — Panel Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  Header: Simulation Name | Status Badge | Step Counter | LLM Status │
├────────────────────────────────┬────────────────────────────────────┤
│                                │                                    │
│     GRAPH PANEL                │    TIMELINE / METRIC PANEL         │
│     (Cytoscape.js)             │    (Recharts)                      │
│                                │                                    │
│     - Agent nodes              │    - Adoption rate line chart      │
│     - Community clusters       │    - Sentiment chart               │
│     - Influence edges          │    - Diffusion rate chart          │
│     - Emergent cluster         │    - Emergent event markers        │
│       highlights               │    - Per-community bars            │
│                                │                                    │
│     Hover → Agent Detail       │                                    │
│     Click → Agent Inspector    │                                    │
│                                │                                    │
├────────────────────────────────┴────────────────────────────────────┤
│                                                                      │
│   CONTROL PANEL                                                      │
│   [▶ Play] [⏸ Pause] [⏭ Step] [⏹ Stop]  Step: 14/50               │
│   Speed: [●────────] | Campaign: Model X Launch | Budget: $5M        │
│                                                                      │
├──────────────────────────────────────────────────────────────────────┤
│   LLM DASHBOARD (collapsible)                                        │
│   Provider: Ollama llama3.2 | Calls: 234 | Cached: 45% | Avg: 212ms │
│   [View Prompt Log]                                                  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Specs

### GraphPanel

```typescript
interface GraphPanelProps {
  simulationId: string;
  currentStep: number;
  highlightedCommunity: string | null;
  onAgentHover: (agentId: string | null) => void;
  onAgentClick: (agentId: string) => void;
}
```

**Behavior:**
- Renders Cytoscape.js graph with nodes = agents, edges = influence links
- Node color encodes community (each community gets distinct color)
- Node size encodes influence_score (range: 10px–40px)
- Node border color encodes emotion state (excitement = gold, skepticism = grey, trust = blue)
- Edge opacity: weight (0.1–0.9)
- Edge color: sentiment polarity of last propagation (green=positive, red=negative, grey=neutral)
- Edge thickness: message_strength (novelty+controversy+utility) — thicker = stronger message
- Edge animation: pulsing animation on active propagation events this step
- Viral cascade cluster highlighted with pulsing orange ring
- Community cluster convex hull shapes drawn (optional, toggle)
- Hover tooltip shows: agent_type, community, action, adoption status, top emotion

**Layout:** Compound layout (communities as parent nodes) via `cytoscape-compound-drag-and-drop`

**Update strategy:** On step_result WebSocket event, only mutate changed node data (do NOT re-render full graph — diffuse updates for performance)

### TimelinePanel

```typescript
interface TimelinePanelProps {
  simulationId: string;
  steps: StepResult[];
  emergentEvents: EmergentEvent[];
}
```

**Charts (stacked, scrollable):**
1. **Adoption Rate** — line chart, one line per community + total
2. **Sentiment** — area chart, mean_belief per community
3. **Diffusion Rate R(t)** — bar chart
4. **Action Distribution** — stacked bar (ignore/like/share/adopt per step)

**Emergent event markers:** Vertical dotted lines on all charts at step where event detected, with label (e.g., "⚡ Viral", "⚠ Collapse")

### ControlPanel

```typescript
interface ControlPanelProps {
  simulationId: string;
  status: SimulationStatus;
  currentStep: number;
  maxSteps: number;
  onPlay: () => void;
  onPause: () => void;
  onStep: () => void;
  onStop: () => void;
  onSpeedChange: (stepsPerSecond: number) => void;
  onInjectEvent: (event: EnvironmentEvent) => void;
}
```

**Buttons:**
- Play: POST /start (disabled if RUNNING)
- Pause: POST /pause (disabled if not RUNNING)
- Step: POST /step (enabled when PAUSED or CONFIGURED)
- Stop: POST /stop (confirmation dialog)

**Inject Event button:** Opens modal to configure a NegativeEvent or custom EnvironmentEvent

**SLM/LLM Ratio Slider** (Prophet-unique UX):
- Slider range: 0.0 (all SLM) to 1.0 (max LLM)
- Real-time 4-indicator display:
  1. Cost Efficiency: estimated $ per step
  2. Reasoning Depth: 양적/균형/질적
  3. Simulation Velocity: estimated seconds per step
  4. Prediction Type: Quantitative / Hybrid / Qualitative
- Optional: Budget input field → auto-adjusts slider to fit budget
- Calls `POST /engine-control` when changed (requires PAUSED state)

### AgentInspector (right drawer)

Opened by clicking an agent node in GraphPanel.

```typescript
interface AgentInspectorProps {
  agentId: string;
  simulationId: string;
  isPaused: boolean;
}
```

**Shows:**
- Agent ID, type, community
- Personality radar chart (5 axes)
- Emotion bar chart
- Belief gauge (-1 to +1)
- Influence score
- Action history (last 5 steps)
- Memory list (last 10 entries, expandable)
- **Edit panel** (only when simulation PAUSED): sliders for personality/emotion/belief

### LLMDashboard (collapsible bottom bar)

- Provider status indicators (green/red dot)
- Real-time call counter + cache hit rate
- Average latency sparkline
- Toggle: show/hide prompt log table
- Prompt log: agent_id, step, provider, prompt preview (truncated), latency, cached

---

## 5. State Management (Zustand)

```typescript
// store/simulationStore.ts
interface SimulationStore {
  simulation: SimulationRun | null;
  status: SimulationStatus;
  currentStep: number;
  steps: StepResult[];
  emergentEvents: EmergentEvent[];

  // WebSocket
  wsConnected: boolean;
  lastStepReceived: number;

  // UI state
  selectedAgentId: string | null;
  highlightedCommunity: string | null;
  isAgentInspectorOpen: boolean;
  isLLMDashboardOpen: boolean;

  // Engine control
  slmLlmRatio: number;
  tierDistribution: TierDistribution | null;
  impactAssessment: EngineImpactReport | null;
  setSlmLlmRatio: (ratio: number) => void;

  // Actions
  setSimulation: (sim: SimulationRun) => void;
  appendStep: (step: StepResult) => void;
  appendEmergentEvent: (event: EmergentEvent) => void;
  setStatus: (status: SimulationStatus) => void;
  selectAgent: (agentId: string | null) => void;
}
```

---

## 6. WebSocket Hook

```typescript
// hooks/useSimulationSocket.ts
function useSimulationSocket(simulationId: string): {
  connected: boolean;
  lastMessage: WSMessage | null;
  send: (message: WSClientMessage) => void;
}
```

- Auto-reconnect on disconnect (max 5 retries, exponential backoff)
- Dispatches to Zustand store on every received message
- Heartbeat ping every 30s

---

## 7. TypeScript Types

All backend response types are mirrored in `src/types/`:

```typescript
// src/types/simulation.ts
export interface SimulationRun { ... }
export interface StepResult { ... }
export interface AgentState { ... }
export interface AgentPersonality { ... }
export interface AgentEmotion { ... }
export interface EmergentEvent { ... }
export interface CommunityStepMetrics { ... }

// src/types/network.ts
export interface CytoscapeNode { data: AgentNodeData }
export interface CytoscapeEdge { data: EdgeData }
export interface NetworkGraphData { nodes: CytoscapeNode[]; edges: CytoscapeEdge[] }

// src/types/llm.ts
export interface LLMCallLog { ... }
export interface LLMStats { ... }
```

---

## 8. API Client

```typescript
// src/api/client.ts
const apiClient = {
  simulations: {
    create: (config: SimulationConfig) => Promise<SimulationRun>,
    get: (id: string) => Promise<SimulationRun>,
    list: (params?: ListParams) => Promise<PaginatedResponse<SimulationRun>>,
    start: (id: string) => Promise<void>,
    step: (id: string) => Promise<StepResult>,
    pause: (id: string) => Promise<void>,
    resume: (id: string) => Promise<void>,
    stop: (id: string) => Promise<void>,
    getSteps: (id: string, params?: StepParams) => Promise<StepResult[]>,
    injectEvent: (id: string, event: EnvironmentEvent) => Promise<void>,
    compare: (id: string, otherId: string) => Promise<ScenarioComparison>,
    runMonteCarlo: (id: string, options: MCOptions) => Promise<{ job_id: string }>,
  },
  agents: {
    list: (simId: string, params?: AgentListParams) => Promise<PaginatedResponse<AgentSummary>>,
    get: (simId: string, agentId: string) => Promise<AgentDetail>,
    modify: (simId: string, agentId: string, mod: AgentModification) => Promise<AgentState>,
    getMemory: (simId: string, agentId: string) => Promise<MemoryRecord[]>,
  },
  network: {
    get: (simId: string, format?: NetworkFormat) => Promise<NetworkGraphData>,
    getMetrics: (simId: string) => Promise<NetworkMetrics>,
  },
  llm: {
    getStats: (simId: string) => Promise<LLMStats>,
    getCalls: (simId: string, params?: LLMCallParams) => Promise<LLMCallLog[]>,
  },
}
```

---

## 9. Error Specification

| Situation | Exception Type | Recovery | User Feedback |
|-----------|---------------|----------|---------------|
| WebSocket disconnect | — (auto-reconnect) | Exponential backoff reconnect (1s, 2s, 4s, max 30s); buffer local state | Toast: "Connection lost. Reconnecting..." |
| WebSocket reconnect after N failures (N=5) | — (give up) | Stop retry, show manual reconnect button | Banner: "Connection failed. Click to retry." |
| API call HTTP 4xx (client error) | — (display) | Show error detail from RFC 7807 response body | Toast: error `detail` field |
| API call HTTP 5xx (server error) | — (display) | Show generic error, log full response to console | Toast: "Server error. Please try again." |
| API call network timeout | — (retry) | Auto-retry once; if fail → show error | Toast: "Request timed out." |
| Cytoscape render crash (>5000 nodes) | `ErrorBoundary` | Catch in React Error Boundary, show fallback UI | Panel: "Graph too large. Apply filters to reduce nodes." |
| Invalid simulation config form submit | — (validation) | Block submit, highlight invalid fields | Inline: field-level error messages |
| Agent inspector receives stale data | — (refetch) | Auto-refetch on panel open; show loading state | Spinner while loading |
| Zustand store hydration failure | — (reset) | Reset to default state, refetch from API | Toast: "State reset. Refreshing data..." |
| Browser localStorage quota exceeded | — (graceful) | Skip persistence, continue in-memory only | Console warning (no user toast) |

---

## 10. Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| FE-01 | Graph panel renders 1000 nodes without freeze | Frame rate ≥ 30fps |
| FE-02 | Step update refreshes graph within 500ms | WebSocket → Cytoscape update |
| FE-03 | Agent hover shows correct tooltip data | Matches backend AgentState |
| FE-04 | Play/Pause buttons change simulation status | Backend status matches UI |
| FE-05 | Agent inspector edit form disabled when RUNNING | Edit controls not interactable |
| FE-06 | Emergent event appears as vertical line on timeline | Correct step position |
| FE-07 | LLM dashboard updates call count in real-time | Zustand state updates |
| FE-08 | WebSocket reconnects after disconnect | `connected` returns to true |
| FE-09 | Community highlight filters graph nodes | Non-selected nodes dimmed |
| FE-10 | Simulation setup form validates required fields | Submit blocked on invalid input |
