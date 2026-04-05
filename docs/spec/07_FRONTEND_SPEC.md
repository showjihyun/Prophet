# 07 — Frontend SPEC (React 18)
Version: 0.2.0 | Status: REVIEW

---

## 0. Related Documents

| 문서 | 역할 |
|------|------|
| **DESIGN.md** | UI 디자인 총괄 — 디자인 토큰, 컴포넌트 라이브러리, 그래프 엔진 시각 규칙 |
| **UI_01_SIMULATION_MAIN.md** | 메인 시뮬레이션 화면 (Pencil Frame: `FuHqi`) |
| **UI_02_COMMUNITIES_DETAIL.md** | 커뮤니티 상세 화면 (Pencil Frame: `LRkh8`) |
| **UI_03_TOP_INFLUENCERS.md** | 인플루언서 목록 화면 (Pencil Frame: `V99cE`) |
| **UI_04_AGENT_DETAIL.md** | 에이전트 상세 화면 (Pencil Frame: `pkFYA`) |
| **UI_05_GLOBAL_METRICS.md** | 글로벌 메트릭 화면 (Pencil Frame: `fjP3Z`) |
| **UI_06_PROJECTS_LIST.md** | 프로젝트 목록 화면 |
| **UI_07_PROJECT_SCENARIOS.md** | 프로젝트 시나리오 화면 |
| **UI_08_INFLUENCERS_PAGINATION.md** | 인플루언서 페이지네이션 |
| **UI_09_INFLUENCERS_FILTER.md** | 인플루언서 필터 |
| **UI_10_AGENT_INTERVENE.md** | 에이전트 개입 모달 |
| **UI_11_AGENT_CONNECTIONS.md** | 에이전트 연결 탭 |
| **UI_12_SETTINGS.md** | 설정 화면 |
| **UI_13_SCENARIO_OPINIONS.md** | 시나리오 의견 화면 |
| **UI_14_COMMUNITY_OPINION.md** | 커뮤니티 의견 화면 |
| **UI_15_CONVERSATION_THREAD.md** | 대화 스레드 화면 |
| **UI_16_CAMPAIGN_SETUP.md** | Campaign Setup 폼 화면 |

구현 시 **이 SPEC의 컴포넌트 인터페이스** + **UI_XX SPEC의 레이아웃/디자인**을 모두 참조한다.

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

## 2. App Layout & Routing

### Layout Structure

두 가지 레이아웃 패턴을 사용한다:

1. **SidebarLayout** — `AppSidebar` + `<main>` (대부분의 페이지)
2. **Full-screen** — 사이드바 없이 전체 화면 (`SimulationPage`, `LoginPage`)

### Route Table

| Route | Page | Layout | UI SPEC |
|-------|------|--------|---------|
| `/` | → Redirect to `/projects` | — | — |
| `/simulation` | `SimulationPage` | Full-screen | UI_01 |
| `/login` | `LoginPage` | Full-screen | — |
| `/projects` | `ProjectsListPage` | Sidebar | UI_06 |
| `/projects/:projectId` | `ProjectScenariosPage` | Sidebar | UI_07 |
| `/projects/:projectId/new-scenario` | `CampaignSetupPage` | Sidebar | UI_16 |
| `/setup` | `CampaignSetupPage` | Sidebar | UI_16 |
| `/communities` | `CommunitiesDetailPage` | Sidebar | UI_02 |
| `/communities/:communityId` | `CommunitiesDetailPage` | Sidebar | UI_02 |
| `/communities/manage` | `CommunityManagePage` | Sidebar | — |
| `/influencers` | `TopInfluencersPage` | Sidebar | UI_03, UI_08, UI_09 |
| `/agents/:agentId` | `AgentDetailPage` | Sidebar | UI_04, UI_10, UI_11 |
| `/metrics` | `GlobalMetricsPage` | Sidebar | UI_05 |
| `/settings` | `SettingsPage` | Sidebar | UI_12 |
| `/opinions` | `ScenarioOpinionsPage` | Sidebar | UI_13 |
| `/opinions/:communityId` | `CommunityOpinionPage` | Sidebar | UI_14 |
| `/opinions/:communityId/thread/:threadId` | `ConversationThreadPage` | Sidebar | UI_15 |
| `/compare/:otherId` | `ComparisonPage` | Sidebar | — |
| `/analytics` | `AnalyticsPage` | Sidebar | — |

> **참고:** 시뮬레이션 ID는 URL 파라미터가 아닌 Zustand store (`simulationStore`)에서 관리한다.
> `/simulation` 페이지는 store의 `simulation` 객체를 참조하여 렌더링한다.

### Error Boundary (Required)

모든 페이지 라우트는 `App.tsx`의 `ErrorBoundary`로 감싸져 있다.
특히 `GraphPanel` (Cytoscape.js)은 초기화 실패 시 전체 UI 크래시를 방지해야 한다.

---

## 3. Pages

### ProjectsListPage (`/projects`)
- 프로젝트 목록 (카드 형태, 상태 배지, 시나리오 수)
- "New Project" 버튼 — 이름/설명 입력 후 생성
- 프로젝트 삭제 기능
- @spec UI_06_PROJECTS_LIST.md

### ProjectScenariosPage (`/projects/:projectId`)
- 프로젝트 상세 + 시나리오 목록
- "Add Scenario" 버튼 → CampaignSetupPage로 이동
- 시나리오별: Run/Delete 버튼, 상태 표시 (draft/created/running/completed)
- @spec UI_07_PROJECT_SCENARIOS.md

### CampaignSetupPage (`/setup`, `/projects/:projectId/new-scenario`)
- **Project selector** (required — simulation must belong to a project)
- Form: simulation name, campaign config (message, budget, channels, target communities)
- **Community Configuration Section:**
  - "Load from Templates" 버튼 — fetches templates from `/communities/templates/`
  - 편집 가능한 community cards (이름, Agent Type, Agent Count, Personality Profile 5 sliders)
  - "Add Community" / "Remove" 버튼
- Campaign Attributes: controversy, novelty, utility 슬라이더
- LLM provider selection, Advanced settings (max_steps, random_seed, SLM/LLM ratio)
- Clone flow: `simulationStore.cloneConfig`가 존재하면 pre-fill
- @spec UI_16_CAMPAIGN_SETUP.md

### SimulationPage (`/simulation`) — Full-screen
- **4-Zone Layout** (see §4)
- Zone 1: ControlPanel (56px)
- Zone 2: CommunityPanel (260px) | GraphPanel (fill) | MetricsPanel (280px)
- Zone 3: TimelinePanel (120px) + ConversationPanel (fill)
- WebSocket connection to real-time step updates
- No active simulation → empty state with "Go to Projects" CTA
- **Inline simulation creation:** "New Simulation" 버튼은 페이지 이동 없이 API 직접 호출로 시뮬레이션 생성
- LLM Dashboard: collapsible overlay at bottom
- Agent Inspector: right drawer when agent selected
- SimulationReportModal: auto-shows on completion
- @spec UI_01_SIMULATION_MAIN.md

### CommunitiesDetailPage (`/communities`, `/communities/:communityId`)
- KPI cards (2×2 mobile, 4-col desktop)
- Community cards grid (1/2/3-col responsive)
- Community detail with metrics
- @spec UI_02_COMMUNITIES_DETAIL.md

### CommunityManagePage (`/communities/manage`)
- CRUD for community templates
- Template cards with personality profile display
- Create/Edit/Delete actions via `/communities/templates/` API

### TopInfluencersPage (`/influencers`)
- Agent influence ranking 테이블
- Pagination (page size selector, page navigation)
- Multi-criteria filter popover (InfluencersFilter)
- Search input
- @spec UI_03, UI_08, UI_09

### AgentDetailPage (`/agents/:agentId`)
- Tabs: Overview, Connections, Memory
- Overview: personality radar, emotion bars, belief gauge, action history
- Connections: EgoGraph (ego-network subgraph)
- Memory: memory record list
- Intervene modal (AgentInterveneModal)
- @spec UI_04, UI_10, UI_11

### GlobalMetricsPage (`/metrics`)
- System-wide KPI cards (2×2 mobile, 4-col desktop)
- Adoption/Sentiment/Diffusion charts (Recharts)
- Community comparison charts
- @spec UI_05_GLOBAL_METRICS.md

### SettingsPage (`/settings`)
- LLM Provider config (Ollama/Claude/OpenAI)
- Ollama connection settings (base URL, model, test connection)
- API key management (Anthropic, OpenAI)
- Simulation defaults (SLM/LLM ratio, Tier 3 ratio, cache TTL)
- @spec UI_12_SETTINGS.md

### ScenarioOpinionsPage (`/opinions`)
- Community opinion breakdown
- Stat cards (2×2 mobile, 4-col desktop)
- Community cards grid (1/2/3-col responsive)
- @spec UI_13_SCENARIO_OPINIONS.md

### CommunityOpinionPage (`/opinions/:communityId`)
- Single community opinion detail with thread list
- @spec UI_14_COMMUNITY_OPINION.md

### ConversationThreadPage (`/opinions/:communityId/thread/:threadId`)
- Thread messages with stance badges, reactions, replies
- @spec UI_15_CONVERSATION_THREAD.md

### ComparisonPage (`/compare/:otherId`)
- Side-by-side metric charts
- Winner highlight, emergent event diff

### AnalyticsPage (`/analytics`)
- Post-run analytics dashboard
- Full metric history, community adoption comparison

### LoginPage (`/login`)
- Username/password form
- Register/Login toggle
- JWT token stored in localStorage

---

## 4. Main Simulation Page — Panel Layout

```
┌──────────────────────────────────────────────────────────────────┐
│ Zone 1: ControlPanel (56px)                                       │
│ [New Sim] [▶ Play] [⏸ Pause] [⏭ Step] [⏹ Stop]  Step: 14/50    │
│ Speed: [1x▼]  Project: [▼]  Sim: [▼]                             │
├──────────┬──────────────────────────────┬────────────────────────┤
│ Zone 2L  │ Zone 2C                      │ Zone 2R               │
│ Community│ GraphPanel                   │ MetricsPanel           │
│ Panel    │ (Cytoscape.js)               │ (280px)               │
│ (260px)  │ (fill)                       │                        │
├──────────┴──────────────────────────────┴────────────────────────┤
│ Zone 3: TimelinePanel (120px) + ConversationPanel (fill)          │
├──────────────────────────────────────────────────────────────────┤
│ LLM Dashboard (collapsible)                                       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Component Specs

### graph/ directory

#### GraphPanel
```typescript
// components/graph/GraphPanel.tsx
// @spec docs/spec/07_FRONTEND_SPEC.md#graphpanel
```
- Renders Cytoscape.js graph with nodes = agents, edges = influence links
- Node color: community, Node size: influence_score (10px–40px)
- Node border: emotion state, Edge opacity: weight, Edge color: sentiment polarity
- Hover tooltip: agent_type, community, action, adoption status
- Click → opens AgentInspector
- Community highlight via `highlightedCommunity` store state

#### CommunityPanel
```typescript
// components/graph/CommunityPanel.tsx
```
- Left panel (260px) in Zone 2
- Community list with adoption rates, member counts
- Click to highlight community on graph

#### MetricsPanel
```typescript
// components/graph/MetricsPanel.tsx
```
- Right panel (280px) in Zone 2
- Real-time metrics: adoption rate, sentiment, diffusion rate, action distribution

#### AgentNode
```typescript
// components/graph/AgentNode.tsx
```
- Custom Cytoscape node renderer

#### EgoGraph
```typescript
// components/graph/EgoGraph.tsx
// @spec docs/spec/ui/UI_11_AGENT_CONNECTIONS.md
```
- Ego-network subgraph for agent connections tab
- Community-based filtering (popover with checkboxes)

### control/ directory

#### ControlPanel
```typescript
// components/control/ControlPanel.tsx
// @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md
```
- Simulation lifecycle buttons: Play, Pause, Step, Stop
- Speed selector (1x/2x/5x/10x)
- Project/Simulation selectors
- "New Simulation" button: inline creation via API (no page navigation)
- Inject Event, Replay, Monte Carlo, Engine Control 버튼 → 모달 열기

#### ConversationPanel
```typescript
// components/control/ConversationPanel.tsx
```
- Bottom zone conversation feed
- Agent messages from current step

#### EngineControlPanel
```typescript
// components/control/EngineControlPanel.tsx
```
- SLM/LLM ratio slider with 4-indicator display
- Budget input → auto-adjusts ratio
- Calls `POST /engine-control` (requires PAUSED state)

### shared/ directory

| Component | File | Purpose |
|-----------|------|---------|
| `AppSidebar` | `shared/AppSidebar.tsx` | Collapsible sidebar navigation, project links |
| `AgentInterveneModal` | `shared/AgentInterveneModal.tsx` | Agent intervention modal (UI_10) |
| `InfluencersFilter` | `shared/InfluencersFilter.tsx` | Multi-criteria filter popover (UI_09) |
| `InjectEventModal` | `shared/InjectEventModal.tsx` | Event injection modal |
| `MonteCarloModal` | `shared/MonteCarloModal.tsx` | Monte Carlo configuration modal |
| `ReplayModal` | `shared/ReplayModal.tsx` | Replay from step modal |
| `SimulationReportModal` | `shared/SimulationReportModal.tsx` | Post-completion summary report |
| `PageNav` | `shared/PageNav.tsx` | Breadcrumb navigation |
| `StatCard` | `shared/StatCard.tsx` | Reusable KPI stat card |
| `ThemeToggle` | `shared/ThemeToggle.tsx` | Dark/Light mode toggle |
| `ToastNotification` | `shared/ToastNotification.tsx` | Toast notification container |

### Other directories

| Component | File | Purpose |
|-----------|------|---------|
| `TimelinePanel` | `timeline/TimelinePanel.tsx` | Step charts (adoption, sentiment, diffusion, action distribution) |
| `AgentInspector` | `agent/AgentInspector.tsx` | Right drawer with agent detail + edit panel (when paused) |
| `LLMDashboard` | `llm/LLMDashboard.tsx` | Collapsible LLM stats + prompt log |

---

## 6. State Management (Zustand)

```typescript
// store/simulationStore.ts
interface SimulationStore {
  // Core simulation state
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
  speed: number;                              // Playback speed (1/2/5/10)
  theme: 'dark' | 'light';                   // Dark/light mode

  // Project context
  currentProjectId: string | null;
  projects: ProjectSummary[];
  scenarios: ScenarioInfo[];

  // Engine control
  slmLlmRatio: number;
  tierDistribution: TierDistribution | null;
  impactAssessment: EngineImpactReport | null;

  // Clone flow
  cloneConfig: CreateSimulationConfig | null;

  // Toast notifications
  toasts: Toast[];

  // Actions
  setSimulation: (sim: SimulationRun) => void;
  appendStep: (step: StepResult) => void;
  appendEmergentEvent: (event: EmergentEvent) => void;
  setStatus: (status: SimulationStatus) => void;
  selectAgent: (agentId: string | null) => void;
  setSlmLlmRatio: (ratio: number) => void;
  setSpeed: (speed: number) => void;
  toggleTheme: () => void;
  toggleLLMDashboard: () => void;
  setHighlightedCommunity: (id: string | null) => void;
  setCurrentProject: (id: string | null) => void;
  setProjects: (projects: ProjectSummary[]) => void;
  setScenarios: (scenarios: ScenarioInfo[]) => void;
  setCloneConfig: (config: CreateSimulationConfig | null) => void;
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;
}
```

---

## 7. Hooks

### useSimulationSocket

```typescript
// hooks/useSimulationSocket.ts
function useSimulationSocket(simulationId: string | null): {
  connected: boolean;
  lastMessage: WSMessage | null;
  send: (message: WSClientMessage) => void;
}
```

**Reconnection Policy:**
- Auto-reconnect: exponential backoff (1s, 2s, 4s, 8s, 16s, max 30s)
- Max 5 retry attempts
- `JSON.parse` wrapped in try/catch

> **미구현 항목:** heartbeat ping (30s), "Click to retry" banner — TODO

### useSimulationData

```typescript
// hooks/useSimulationData.ts — TanStack Query wrappers
export function useSimulation(id: string | null): UseQueryResult<SimulationRun>;
export function useSimulationList(): UseQueryResult<SimulationRun[]>;
export function useStepMutation(id: string): UseMutationResult<StepResult>;
export function useNetworkGraph(id: string | null): UseQueryResult<CytoscapeGraph>;
export function useLLMStats(id: string | null): UseQueryResult<LLMStats>;
export function useSimulationRun(): UseMutationResult<RunAllReport>;
```

---

## 8. API Client

```typescript
// src/api/client.ts
const apiClient = {
  simulations: {
    create: (config: CreateSimulationConfig) => Promise<SimulationRun>,
    get: (id: string) => Promise<SimulationRun>,
    list: () => Promise<{ items: SimulationRun[]; total: number }>,
    start: (id: string) => Promise<{ status: string }>,
    step: (id: string) => Promise<StepResult>,
    pause: (id: string) => Promise<{ status: string }>,
    resume: (id: string) => Promise<{ status: string }>,
    stop: (id: string) => Promise<{ status: string }>,
    getSteps: (id: string) => Promise<StepResult[]>,
    injectEvent: (id: string, event) => Promise<{ event_id: string; effective_step: number }>,
    replay: (id: string, step: number) => Promise<{ replay_id: string; from_step: number }>,
    compare: (id: string, otherId: string) => Promise<Record<string, unknown>>,
    monteCarlo: (id: string, opts) => Promise<{ job_id: string }>,
    getMonteCarloJob: (id: string, jobId: string) => Promise<Record<string, unknown>>,
    engineControl: (id: string, body) => Promise<Record<string, unknown>>,
    runAll: (id: string) => Promise<RunAllReport>,
    recommendEngine: (body) => Promise<Record<string, unknown>>,
    export: (id: string, format: 'json' | 'csv') => void,  // window.open
  },
  agents: {
    list: (simId: string, params?) => Promise<{ items: AgentSummary[]; total: number }>,
    get: (simId: string, agentId: string) => Promise<AgentDetail>,
    modify: (simId: string, agentId: string, body) => Promise<AgentDetail>,
    getMemory: (simId: string, agentId: string) => Promise<{ memories: MemoryRecord[] }>,
  },
  communities: {
    list: (simId: string) => Promise<{ communities: CommunityInfo[] }>,
  },
  communityThreads: {
    list: (simId: string, communityId: string) => Promise<{ threads: ThreadSummary[] }>,
    get: (simId: string, communityId: string, threadId: string) => Promise<ThreadDetail>,
  },
  communityTemplates: {
    list: () => Promise<{ templates: CommunityTemplate[] }>,
    create: (data: CommunityTemplateInput) => Promise<CommunityTemplate>,
    update: (id: string, data: CommunityTemplateInput) => Promise<CommunityTemplate>,
    delete: (id: string) => Promise<void>,
  },
  projects: {
    list: () => Promise<ProjectSummary[]>,
    get: (id: string) => Promise<ProjectDetail>,
    create: (data) => Promise<ProjectSummary>,
    createScenario: (projectId: string, data) => Promise<ScenarioInfo>,
    runScenario: (projectId: string, scenarioId: string) => Promise<{ simulation_id: string; status: string }>,
    deleteScenario: (projectId: string, scenarioId: string) => Promise<void>,
    update: (id: string, data) => Promise<ProjectSummary>,
    delete: (id: string) => Promise<void>,
  },
  network: {
    get: (simId: string) => Promise<CytoscapeGraph>,     // hardcodes ?format=cytoscape
    getMetrics: (simId: string) => Promise<NetworkMetrics>,
  },
  llm: {
    getStats: (simId: string) => Promise<LLMStats>,
    getImpact: (simId: string) => Promise<EngineImpactReport>,
  },
  auth: {
    register: (username: string, password: string) => Promise<{ user_id: string; username: string }>,
    login: (username: string, password: string) => Promise<{ token: string; user_id: string; username: string }>,
    me: () => Promise<{ user_id: string; username: string }>,
  },
  settings: {
    get: () => Promise<SettingsResponse>,
    update: (data: SettingsUpdateRequest) => Promise<{ status: string }>,
    listOllamaModels: () => Promise<{ models: string[] }>,
    testOllama: () => Promise<{ status: string; model?: string; latency_ms?: number; message?: string }>,
    listPlatforms: () => Promise<{ platforms: unknown[] }>,
    listRecsys: () => Promise<{ algorithms: unknown[] }>,
  },
}
```

### Data Fetching — TanStack Query (Required)

모든 API 호출은 `@tanstack/react-query`의 `useQuery`/`useMutation`을 통해 수행한다.
직접 `fetch`나 `apiClient` 호출을 컴포넌트에서 하지 않는다.

---

## 9. TypeScript Types

All backend response types are mirrored in `src/types/` and `src/api/client.ts`:

```typescript
// src/types/simulation.ts
export type SimulationStatus = 'created' | 'configured' | 'running' | 'paused' | 'completed' | 'failed';
export type AgentAction = 'ignore' | 'like' | 'share' | 'adopt' | ...;
export interface SimulationRun { ... }
export interface StepResult { ... }
export interface EmergentEvent { ... }
export interface CommunityStepMetrics { ... }
export interface TierDistribution { ... }
export interface EngineImpactReport { ... }

// src/api/client.ts (co-located interfaces)
export interface AgentSummary { ... }
export interface AgentDetail extends AgentSummary { ... }
export interface CommunityInfo { ... }
export interface ThreadSummary { ... }
export interface ThreadDetail { ... }
export interface ProjectSummary { ... }
export interface ProjectDetail { ... }
export interface ScenarioInfo { ... }
export interface CytoscapeGraph { nodes: [...]; edges: [...] }
export interface NetworkMetrics { ... }
export interface RunAllReport { ... }
export interface SettingsResponse { ... }
export interface CommunityTemplate { ... }
```

---

## 10. Error Specification

| Situation | Recovery | User Feedback |
|-----------|----------|---------------|
| WebSocket disconnect | Exponential backoff reconnect (1s–30s, max 5 retries) | Toast: "Connection lost. Reconnecting..." |
| WebSocket reconnect failure (5x) | Stop retry | Banner: "Connection failed. Click to retry." (TODO) |
| API call HTTP 4xx | Show error detail from RFC 7807 response | Toast: error `detail` field |
| API call HTTP 5xx | Show generic error, log to console | Toast: "Server error. Please try again." |
| Cytoscape render crash | React ErrorBoundary → fallback UI | "Graph too large. Apply filters." |
| Invalid form submit | Block submit, highlight fields | Inline field-level error messages |
| Agent inspector stale data | Auto-refetch on panel open | Spinner while loading |
| List/data loading | Show spinner during fetch | Spinner overlay on list containers |

### 10.1 API Response Null Safety (필수)

모든 컴포넌트는 API 응답의 선택적 필드에 대해 **null/undefined guard**를 적용해야 한다.

```typescript
// BAD — API 응답에 event_type이 없으면 크래시
event.event_type.replace(/_/g, " ")

// GOOD — null safety
(event.event_type ?? "event").replace(/_/g, " ")
```

**특히 주의할 패턴:**
- `.replace()`, `.toLocaleString()`, `.toFixed()`, `.map()` — undefined 호출 시 크래시
- `community_metrics[key].adoption_count` — API serializer가 필드를 누락할 수 있음
- `emergentEvents[idx].event_type` — 배열이 비어있을 수 있음

**규칙:** API 응답에서 가져온 모든 값은 `??` 또는 `?.` 로 guard한다.

### 10.2 Loading States (필수)

데이터를 비동기로 가져오는 모든 컴포넌트는 로딩 상태를 표시해야 한다.

| 컴포넌트 | 로딩 시점 | 표시 방식 |
|----------|----------|----------|
| CommunityPanel | 시뮬레이션 로드 시 | Skeleton shimmer |
| TopInfluencersPage | 에이전트 목록 fetch | Spinner + "Loading agents..." |
| AgentDetailPage | 에이전트 상세 fetch | Spinner 오버레이 |
| GlobalMetricsPage | steps fetch | Skeleton cards |
| ControlPanel 시나리오 | 프로젝트 변경 시 | Spinner in dropdown |
| CommunitiesDetailPage | 커뮤니티 fetch | Spinner + skeleton cards |

---

## 11. Testing

### Unit Tests (Vitest)
- Framework: **Vitest** + **@testing-library/react** + **jsdom**
- Config: `vite.config.ts` (test section) + `src/test/setup.ts`
- Run: `npx vitest run`
- Tests: `src/__tests__/*.test.{ts,tsx}` (180+ tests)
- Covers: API client methods, Zustand store actions, component rendering, page rendering

### E2E Tests (Playwright)
- Framework: **Playwright** (Chromium)
- Config: `playwright.config.ts`
- Run: `npx playwright test`
- Tests: `e2e/*.spec.ts` (26 tests)
- Requires Docker Compose (backend + frontend + PostgreSQL)

---

## 12. Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| FE-01 | Graph panel renders 1000 nodes without freeze | Frame rate >= 30fps |
| FE-02 | Step update refreshes graph within 500ms | WebSocket → Cytoscape update |
| FE-03 | Agent hover shows correct tooltip data | Matches backend AgentState |
| FE-04 | Play/Pause buttons change simulation status | Backend status matches UI |
| FE-05 | Agent inspector edit form disabled when RUNNING | Edit controls not interactable |
| FE-06 | Emergent event appears as vertical line on timeline | Correct step position |
| FE-07 | LLM dashboard updates call count in real-time | Zustand state updates |
| FE-08 | WebSocket reconnects after disconnect | `connected` returns to true |
| FE-09 | Community highlight filters graph nodes | Non-selected nodes dimmed |
| FE-10 | Simulation setup form validates required fields | Submit blocked on invalid input |
| FE-11 | Inline "New Simulation" creates sim without page navigation | API call + store update |
| FE-12 | Dark/Light theme toggle works across all pages | CSS variables switch correctly |
| FE-13 | All sidebar pages render without errors | No console errors |
| FE-14 | Project CRUD (create/update/delete) works | API integration verified |
| FE-15 | Community template CRUD works | Templates persist across sessions |
