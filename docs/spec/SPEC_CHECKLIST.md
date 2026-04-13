# SPEC Compliance Checklist — Prophet (MCASP)

> Last updated: 2026-04-11 (Round 6 cleanup)
> Backend: **981 passing**, 2 skipped | Frontend: **609 tests**, tsc 0 errors, eslint 0 errors
>
> **Note:** Core SPEC files (00-09, UI) are local-only for IP protection. The checklist below
> is maintained as a record of implementation/test status — it reflects the state of the code
> regardless of the absence of SPEC files.
>
> **Recent changes (v0.1.1.0):**
> - SPEC 19_SIMULATION_QUALITY (P1): Fatigue / EdgeWeight / ExpertScore / PromptInjection
> - SPEC 19_SIMULATION_INTEGRITY: Friedkin opinion, cognition coupling, persistence safety
> - SPEC 20_SIMULATION_QUALITY_P2: EmotionalContagion / BoundedConfidence / ContentGeneration
> - SPEC 20_CLEAN_ARCHITECTURE: `app/repositories/`, `app/services/`, FE `types/api.ts` separation
> - SPEC 21_SIMULATION_QUALITY_P3: Reflection / Homophily / Memory Persistence (in progress)
> - SPEC 22_CONVERSATION_THREAD: real thread capture + storage + `/communities/{id}/threads`
> - SPEC 23_EXPERT_LLM: LLM-assisted expert reasoning + rule-based fallback
> - LLM tier routing hardening + API error handling
>
> **Previous changes (v0.3.1):**
> - Echo chamber detection: revised to be based on real network topology (removed hardcoding)
> - PersonalityDrift: connected to both sync/async tick paths
> - Controversy parameter: CampaignConfig → MessageStrength flow completed
> - Monte Carlo: asyncio.Semaphore(max_concurrency=3) parallel execution applied
> - ControlPanel: refactored into 8 separate files
> - API historical simulation graceful degradation handling
> - DB session safety: background task session safety secured
> - Startup query: converted from raw SQL to ORM
>
> **Previous changes (v0.3.0):**
> - GraphPanel: Cytoscape 2D → react-force-graph-3d (three.js WebGL 3D)
> - SimulationListPage newly added (`/simulation` → list, `/simulation/:id` → detail)
> - AgentDetailPage: removed MOCK_AGENT, real-data-only + loading/not-found gate
> - EgoGraph: mock → real network API connected
> - TanStack Query migration completed across all pages
> - Agent/Communities/Replay endpoint exception handling strengthened (removed silent swallow)
> - LLM Gateway: `is_fallback_stub` flag + `fallback_stub_count` telemetry
> - GlobalMetricsPage: `/llm/stats` real tier_breakdown integration + real cascade statistics
> - 3 Opinion pages + CommunitiesDetailPage mock removed
> - Backend startup: `running/paused` simulation → `failed` auto-transition (orphan prevention)

---

## Backend SPECs

### 00 ARCHITECTURE — System Architecture
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| FastAPI + React 18 + PostgreSQL + Valkey layered architecture | ✅ | ⚠️ | sanity test only |
| pgvector + NetworkX in-process graph | ✅ | ⚠️ | no architecture-level integration tests |
| Docker Compose 5 services | ✅ | ✅ | 5/5 healthy |
| Constants externalized (config.py + .env) | ✅ | ✅ | 96 settings, Pydantic Settings |

### 01 AGENT_SPEC — 6-Layer Agent Engine
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| Perception Layer | ✅ | ✅ | test_01_perception.py |
| Memory Layer (episodic + semantic) | ✅ | ✅ | test_01_memory.py |
| Emotion Layer | ✅ | ✅ | test_01_emotion.py |
| Cognition Layer (Tier 1/2/3) | ✅ | ✅ | test_01_cognition.py |
| Decision Layer | ✅ | ✅ | test_01_decision.py |
| Influence Layer | ✅ | ✅ | test_01_influence.py |
| Agent Schema + Types | ✅ | ✅ | test_01_schema.py |
| Tier Selector (SLM/Heuristic/LLM) | ✅ | ✅ | test_01_tier_selector.py |
| Personality Drift | ✅ | ✅ | test_01_drift.py — sync/async tick both paths connected |

### 02 NETWORK_SPEC — Network Generator
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| Hybrid WS + BA generator | ✅ | ✅ | test_02_network_acceptance.py |
| Community graph + influencer layer | ✅ | ✅ | |
| Network validation (clustering, path length) | ✅ | ⚠️ | no dedicated metric threshold tests |
| Network evolution (evolve_step) | ✅ | ⚠️ | indirectly verified in acceptance tests |

### 03 DIFFUSION_SPEC — Diffusion Engine
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| Exposure Model | ✅ | ✅ | test_03_exposure.py |
| Propagation Model | ✅ | ✅ | test_03_propagation.py |
| Sentiment Model | ✅ | ✅ | test_03_sentiment.py |
| Cascade Detector | ✅ | ✅ | test_03_cascade.py |
| Echo chamber detection (real topology) | ✅ | ✅ | hardcoding removed, based on network topology |
| RecSys Feed Ranking (OASIS style) | ✅ | ✅ | **G-2 resolved**: test_03_recsys_feed.py (+10 tests) |

### 04 SIMULATION_SPEC — Simulation Orchestrator
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| Simulation lifecycle (CRUD + state transitions) | ✅ | ✅ | test_04_simulation_acceptance.py |
| CommunityOrchestrator (3-Phase step) | ✅ | ✅ | test_04_community_orchestrator.py |
| StepRunner | ✅ | ✅ | test_04_step_runner.py |
| MetricCollector | ✅ | ✅ | test_04_metric_collector.py |
| Run-all endpoint | ✅ | ✅ | |
| Monte Carlo parallel execution (asyncio.Semaphore) | ✅ | ✅ | max_concurrency=3 |
| API historical simulation graceful degradation | ✅ | ✅ | |
| DB session safety (background tasks) | ✅ | ✅ | |
| Startup query ORM conversion | ✅ | ✅ | raw SQL removed |

### 05 LLM_SPEC — LLM Integration
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| LLMAdapter interface | ✅ | ✅ | test_05_adapter.py |
| Multi-provider (Ollama/Claude/OpenAI/Gemini) | ✅ | ✅ | test_05_registry.py |
| Controversy parameter (CampaignConfig → MessageStrength) | ✅ | ✅ | flow completed |
| 3-tier cache (memory → Valkey → pgvector) | ✅ | ✅ | test_05_cache.py |
| Quota / Budget management | ✅ | ✅ | test_05_quota.py |
| Engine Control (SLM/LLM ratio) | ✅ | ✅ | test_05_engine_control.py |
| Prompt Builder | ✅ | ✅ | test_05_prompt_builder.py |
| 768-dim embedding projection | ✅ | ✅ | **G-3 resolved**: test_05_embed_dim.py (+5 tests) |

### 06 API_SPEC — REST/WebSocket API
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| Simulation CRUD + step control | ✅ | ✅ | test_06_api_simulations.py |
| Agent API (list, detail, intervene) | ✅ | ✅ | test_06_api_agents.py |
| WebSocket live streaming | ✅ | ✅ | test_06_api_ws.py |
| Settings API | ✅ | ✅ | test_06_api_settings.py |
| Communities API (threads) | ✅ | ✅ | **G-4 resolved**: test_06_api_communities.py (+12 tests) |

### 08 DB_SPEC — Database Schema
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| 16-table schema + FK/indexes | ✅ | ✅ | test_08_db_errors.py |
| Alembic migrations | ✅ | ⚠️ | no migration execution verification |
| pgvector HNSW index | ✅ | ✅ | **G-1 resolved**: test_08_db_vector.py (+8 tests) |
| llm_vector_cache table | ✅ | ✅ | test_08_db_vector.py |

### 09 HARNESS_SPEC — Test Harness
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| F18-F20: Agent/Network/Diffusion harness | ✅ | ✅ | test_09_harness_*.py |
| F21-F22: Replay/Scenario comparator | ✅ | ✅ | |
| F24: Mock environment (sandbox) | ✅ | ✅ | |
| F25: Metric logger | ✅ | ✅ | |
| F26: API hooks | ✅ | ✅ | test_09_harness_f26_api_hooks.py |
| F27-F28: Performance/Recovery | ✅ | ✅ | |
| F23: Scenario comparison | ✅ | ⚠️ | indirect tests only |
| F30: Hybrid exec | ✅ | ✅ | **G-7 resolved**: hybrid_exec.py + 18 tests |

### 10 VALIDATION_SPEC — Validation Pipeline
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| VAL-01~08 pipeline | ✅ | ✅ | test_10_validation_pipeline.py |
| Cascade Detection F1 | ⚠️ | ⚠️ | no isolated F1 score tests |
| NRMSE accuracy | ⚠️ | ⚠️ | no threshold assertion |

---

## Frontend SPECs

### 07 FRONTEND_SPEC — UI Components
| Page | Impl | Test | Test File |
|--------|:----:|:------:|------------|
| SimulationPage (UI-01) | ✅ | ✅ | SimulationPage.test.tsx, SimulationMain.test.tsx |
| CommunitiesDetailPage (UI-02) | ✅ | ✅ | CommunitiesDetail.test.tsx |
| TopInfluencersPage (UI-03) | ✅ | ✅ | TopInfluencers.test.tsx |
| AgentDetailPage (UI-04) | ✅ | ✅ | AgentDetail.test.tsx |
| GlobalMetricsPage (UI-05) | ✅ | ✅ | GlobalMetrics.test.tsx |
| ProjectsListPage (UI-06) | ✅ | ✅ | ProjectsListPage.test.tsx |
| ProjectScenariosPage (UI-07) | ✅ | ✅ | ProjectScenariosPage.test.tsx |
| SettingsPage (UI-12) | ✅ | ✅ | SettingsPage.test.tsx |
| ScenarioOpinionsPage (UI-13) | ✅ | ✅ | ScenarioOpinions.test.tsx |
| CommunityOpinionPage (UI-14) | ✅ | ✅ | CommunityOpinion.test.tsx |
| ConversationThreadPage (UI-15) | ✅ | ✅ | ConversationThread.test.tsx |
| CampaignSetupPage (UI-16) | ✅ | ✅ | CampaignSetupPage.test.tsx |
| LoginPage | ✅ | ✅ | LoginPage.test.tsx |
| AnalyticsPage | ✅ | ✅ | AnalyticsPage.test.tsx (51 tests) — SPEC: 26_ANALYTICS_SPEC.md v0.3.0 (§4.5.2 round-trip closed; Cascade §4.6, filter §4.5.1, chart a11y §7). Round-trip tests live in SimulationPage.test.tsx + simulationStore.test.ts. |
| ComparisonPage | ✅ | ✅ | ComparisonPage.test.tsx |
| CommunityManagePage | ✅ | ✅ | CommunityManagePage.test.tsx |

### Frontend Infrastructure
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| Zustand Store | ✅ | ✅ | simulationStore.test.ts |
| API Client | ✅ | ✅ | apiClient.test.ts |
| WebSocket Hook | ✅ | ✅ | useSimulationSocket.test.ts |
| FactionMapView (Cytoscape) | ✅ | ✅ | FactionMapView.test.tsx (21 tests) |
| UI_FLOW_SPEC E2E flow verification | ✅ | ✅ | **G-6 resolved**: UIFlowSpec.test.tsx (29 tests) |
| Playwright browser E2E | ✅ | ✅ | 29 tests (navigation + simulation + modals + API lifecycle) |
| constants.ts constants integration | ✅ | ✅ | 120+ constants, referenced in 12 files |
| ControlPanel refactoring (8 files) | ✅ | ✅ | separated into control/hooks/ + 7 components |

### UI_FLOW_SPEC Known Gaps (10 items)
| Item | Status | Note |
|------|:----:|------|
| WS heartbeat (30s ping) | ✅ | already implemented |
| "Click to retry" banner | ✅ | retryExhausted + banner added |
| ProjectScenarios Stop button | ✅ | already implemented |
| ProjectScenarios More(⋯) button | ✅ | already implemented |
| AgentDetail Messages tab | ✅ | getMemory API connected, Mock fallback |
| ConversationThread reaction | ✅ | local toggle |
| ScenarioOpinions Map/Faction | ✅ | already implemented |
| CommunityOpinion Sort | ✅ | already implemented |
| `llm.getCalls` API method | ✅ | apiClient.llm.getCalls() added |

---

## Product / Feature SPECs (16+)

### 16 COMMUNITY_MGMT — Community CRUD & Templates
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| Community CRUD | ✅ | ✅ | `app/api/communities.py` |
| Template management | ✅ | ✅ | `data/community_templates.json` |
| Reassignment / Merge / Split | ✅ | ✅ | |

### 17 PERFORMANCE — Backend Performance
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| O(1) agent lookup | ✅ | ✅ | |
| asyncio.gather batching | ✅ | ✅ | |
| Bulk DB writes | ✅ | ✅ | |
| Memory caps | ✅ | ⚠️ | benchmark-based verification |

### 18 FRONTEND_PERFORMANCE — FE Perf + 3D Graph + AgentDetail
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| §5 3D Graph (G3D-01~09, AC-01~07) | ✅ | ✅ | react-force-graph-3d |
| §6 AgentDetail real-data-only (AD-01~07) | ✅ | ✅ | MOCK removed |
| §7.1 GraphPanel lazy loading | ✅ | ✅ | React.lazy + Suspense |
| §7.2 Scenario auto-provisioning | ✅ | ✅ | handleScenarioChange → runScenario |
| §7.3 persist_creation FK safety (PC-01~03) | ✅ | ✅ | flush ordering |

### 19 SIMULATION_INTEGRITY — Fidelity Audit Plan
| Phase | Item | Impl | Test | Note |
|-------|------|:----:|:------:|------|
| 1 | Data integrity & concurrency | ✅ | ✅ | `orchestrator.py`, `persistence.py` |
| 2 | Friedkin opinion model | ✅ | ✅ | `opinion_dynamics.py` |
| 3 | SIR/IC diffusion state machine | ✅ | ✅ | `propagation_model.py`, `tick.py` |
| 4 | Cognition & emotion coupling | ✅ | ✅ | `cognition.py`, `drift.py` |
| 5 | Network metric & scalability | ✅ | ✅ | `generator.py`, `evolution.py` |
| 6 | WebSocket & cascade reliability | ✅ | ✅ | `ws.py`, `cascade_detector.py`, `sentiment_model.py` |

### 20 CLEAN_ARCHITECTURE — Layered Refactor
| Item | Impl | Test | Note |
|------|:----:|:------:|------|
| §2.1 Simulation repository | ✅ | ⚠️ | `repositories/simulation_repo.py` |
| §2.2 Project repository | ✅ | ⚠️ | `repositories/project_repo.py` |
| §2.x Repository protocols | ✅ | ⚠️ | `repositories/protocols.py` |
| §3.1 Simulation service | ✅ | ⚠️ | `services/simulation_service.py` |
| §4.1 FE `types/api.ts` separation | ✅ | ✅ | `frontend/src/types/api.ts` |
| §4.x FE hooks/queries routing | ⚠️ | — | some components migration in progress |

### 21 SIMULATION_QUALITY — Consolidated (P1 + P2 + P3)
> The 3 original files `19_SIMULATION_QUALITY_SPEC.md`, `20_SIMULATION_QUALITY_P2_SPEC.md`,
> `21_SIMULATION_QUALITY_P3_SPEC.md` were merged on 2026-04-10.

#### Phase 1 — Immediate Quality Wins
| ID | Item | Impl | Test | Note |
|----|------|:----:|:------:|------|
| SQ-01 | Exposure fatigue model | ✅ | ✅ | `engine/agent/fatigue.py`, `test_21_simulation_quality_p1.py` |
| SQ-02 | Edge weight perception | ✅ | ✅ | `engine/agent/perception.py` |
| SQ-03 | Expert opinion score | ✅ | ✅ | `engine/agent/perception.py` |
| SQ-04 | Prompt injection defense | ✅ | ✅ | `llm/prompt_builder.py` |

#### Phase 2 — Social Realism Extensions
| ID | Item | Impl | Test | Note |
|----|------|:----:|:------:|------|
| EC-01~04 | Emotional Contagion | ✅ | ✅ | `engine/agent/emotion.py`, `test_21_simulation_quality_p2.py` |
| BC-01~07 | Bounded Confidence (Deffuant) | ✅ | ✅ | `engine/diffusion/opinion_dynamics.py` |
| CG-01~04 | Agent Content Generation | ✅ | ✅ | `llm/prompt_builder.py` |

#### Phase 3 — Strategic Depth
| ID | Item | Impl | Test | Note |
|----|------|:----:|:------:|------|
| RF-01~05 | Agent Reflection (Simulacra) | ⚠️ | ⚠️ | `engine/agent/reflection.py`, `test_21_simulation_quality_p3.py` — in progress |
| HM-01~04 | Homophily edge weighting | ⚠️ | ⚠️ | `engine/network/generator.py` — in progress |
| MP-01~04 | Memory persistence (pgvector) | ✅ | ✅ | `engine/agent/memory.py`, `test_21_memory_pgvector.py` |

### 22 CONVERSATION_THREAD — Real Thread Capture
| ID | Item | Impl | Test | Note |
|----|------|:----:|:------:|------|
| CT-01~03 | Thread capture in tick / community orchestrator | ✅ | ✅ | `engine/simulation/thread_capture.py` |
| CT-04 | Thread model | ✅ | ✅ | `models/thread.py` |
| CT-05 | Thread persistence | ✅ | ✅ | `engine/simulation/persistence.py#CT-05` |
| CT-06~08 | Thread API | ✅ | ✅ | `test_22_conversation_threads.py` |

### 23 EXPERT_LLM — Expert Engine LLM Integration
| ID | Item | Impl | Test | Note |
|----|------|:----:|:------:|------|
| EX-01 | LLM expert reasoning | ✅ | ✅ | `engine/agent/expert_engine.py` |
| EX-02 | Score synthesis | ✅ | ✅ | |
| EX-03 | Fallback to rule-based | ✅ | ✅ | `test_23_expert_llm.py` |
| EX-04 | Prompt template | ✅ | ✅ | `llm/prompt_builder.py` |

---

## GAP Summary

| # | GAP | Status | Note |
|---|-----|:----:|------|
| G-1 | pgvector vector search + trgm tests | ✅ | +8 tests |
| G-2 | RecSys feed ranking tests | ✅ | +10 tests |
| G-3 | embed 768-dim projection tests | ✅ | +5 tests |
| G-4 | Communities API dedicated tests | ✅ | +12 tests |
| G-5 | Monte Carlo parallel execution | ✅ | asyncio.Semaphore(max_concurrency=3) applied |
| G-6 | UI_FLOW_SPEC E2E verification | ✅ | +29 tests (Vitest) |
| G-7 | F30 Hybrid exec implementation | ✅ | SPEC + implementation + 18 tests |

---

## Remaining ⚠️ Items (LOW priority)

| Item | SPEC | Description |
|------|------|------|
| Network validation threshold dedicated tests | 02_NETWORK | clustering/path length bounds tests |
| Network evolution dedicated tests | 02_NETWORK | evolve_step isolated tests |
| F23 Scenario comparison isolated tests | 09_HARNESS | indirect tests only |
| Cascade F1 score isolated tests | 10_VALIDATION | F1 threshold assertion |
| NRMSE accuracy threshold tests | 10_VALIDATION | threshold assertion |
| Alembic migration execution verification | 08_DB | migration integration tests |
| ~~Playwright browser E2E~~ | ~~07_FRONTEND~~ | ✅ 29 tests passed |

---

## Remaining Technical Debt (Known Remaining Gaps)

| # | Item | Severity | Description |
|---|------|:------:|------|
| KG-1 | Memory persistence (pgvector not connected) | ⚠️ | MemoryLayer is in-memory only, pgvector not connected |
| KG-2 | Valkey cache not initialized | ⚠️ | LLM cache layer effectively disabled |
| KG-3 | Expert signals hardcoded | ⚠️ | real external data source not connected |
| KG-4 | Sync tick embedding dead code | ℹ️ | embedding code in sync tick path unused |
| KG-5 | Network edge cap (5000) | ℹ️ | limits large-scale network scenarios |
| KG-6 | Content ID placeholder | ℹ️ | some content IDs use placeholders |

---

## Health Stack Quick Check

```bash
# Full verification commands
cd backend && uv run pytest tests/ -q          # 952 collected / 861 passing, 2 skipped
cd frontend && npx vitest run                   # 521 tests (27 files)
cd frontend && npx tsc --noEmit                 # 0 errors
cd frontend && npx eslint .                     # 0 errors
docker compose ps                               # 5/5 healthy (ollama occasionally unhealthy)
```

## Legend
- ✅ Implementation + tests complete
- ⚠️ Implemented, tests partial/insufficient
- ❌ Not implemented or no tests
