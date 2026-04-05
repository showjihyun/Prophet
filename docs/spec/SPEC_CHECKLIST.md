# SPEC Compliance Checklist — Prophet (MCASP)

> 마지막 업데이트: 2026-04-05
> Backend: 819 tests | Frontend: 344 tests | Playwright E2E: 29 tests | Total: 1,192 tests

---

## Backend SPECs

### 00 ARCHITECTURE — 시스템 아키텍처
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| FastAPI + React 18 + PostgreSQL + Valkey 레이어드 아키텍처 | ✅ | ⚠️ | sanity test만 존재 |
| pgvector + NetworkX 인프로세스 그래프 | ✅ | ⚠️ | 아키텍처 레벨 통합 테스트 없음 |
| Docker Compose 5 services | ✅ | ✅ | 5/5 healthy |
| 상수 외부화 (config.py + .env) | ✅ | ✅ | 96개 설정, Pydantic Settings |

### 01 AGENT_SPEC — 6-Layer Agent Engine
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| Perception Layer | ✅ | ✅ | test_01_perception.py |
| Memory Layer (episodic + semantic) | ✅ | ✅ | test_01_memory.py |
| Emotion Layer | ✅ | ✅ | test_01_emotion.py |
| Cognition Layer (Tier 1/2/3) | ✅ | ✅ | test_01_cognition.py |
| Decision Layer | ✅ | ✅ | test_01_decision.py |
| Influence Layer | ✅ | ✅ | test_01_influence.py |
| Agent Schema + Types | ✅ | ✅ | test_01_schema.py |
| Tier Selector (SLM/Heuristic/LLM) | ✅ | ✅ | test_01_tier_selector.py |
| Personality Drift | ✅ | ✅ | test_01_drift.py |

### 02 NETWORK_SPEC — Network Generator
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| Hybrid WS + BA 생성기 | ✅ | ✅ | test_02_network_acceptance.py |
| Community graph + influencer layer | ✅ | ✅ | |
| Network validation (clustering, path length) | ✅ | ⚠️ | 메트릭 threshold 전용 테스트 없음 |
| Network evolution (evolve_step) | ✅ | ⚠️ | acceptance 테스트에서 간접 검증 |

### 03 DIFFUSION_SPEC — Diffusion Engine
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| Exposure Model | ✅ | ✅ | test_03_exposure.py |
| Propagation Model | ✅ | ✅ | test_03_propagation.py |
| Sentiment Model | ✅ | ✅ | test_03_sentiment.py |
| Cascade Detector | ✅ | ✅ | test_03_cascade.py |
| RecSys Feed Ranking (OASIS 스타일) | ✅ | ✅ | **G-2 해소**: test_03_recsys_feed.py (+10 tests) |

### 04 SIMULATION_SPEC — Simulation Orchestrator
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| Simulation lifecycle (CRUD + 상태 전이) | ✅ | ✅ | test_04_simulation_acceptance.py |
| CommunityOrchestrator (3-Phase step) | ✅ | ✅ | test_04_community_orchestrator.py |
| StepRunner | ✅ | ✅ | test_04_step_runner.py |
| MetricCollector | ✅ | ✅ | test_04_metric_collector.py |
| Monte Carlo Runner | ✅ | ⚠️ | 동시성 제한(max-3) 테스트 없음 |
| Run-all endpoint | ✅ | ✅ | |

### 05 LLM_SPEC — LLM Integration
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| LLMAdapter 인터페이스 | ✅ | ✅ | test_05_adapter.py |
| Multi-provider (Ollama/Claude/OpenAI/Gemini) | ✅ | ✅ | test_05_registry.py |
| 3-tier 캐시 (memory → Valkey → pgvector) | ✅ | ✅ | test_05_cache.py |
| Quota / Budget 관리 | ✅ | ✅ | test_05_quota.py |
| Engine Control (SLM/LLM ratio) | ✅ | ✅ | test_05_engine_control.py |
| Prompt Builder | ✅ | ✅ | test_05_prompt_builder.py |
| 768-dim embedding projection | ✅ | ✅ | **G-3 해소**: test_05_embed_dim.py (+5 tests) |

### 06 API_SPEC — REST/WebSocket API
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| Simulation CRUD + step control | ✅ | ✅ | test_06_api_simulations.py |
| Agent API (list, detail, intervene) | ✅ | ✅ | test_06_api_agents.py |
| WebSocket live streaming | ✅ | ✅ | test_06_api_ws.py |
| Settings API | ✅ | ✅ | test_06_api_settings.py |
| Communities API (threads) | ✅ | ✅ | **G-4 해소**: test_06_api_communities.py (+12 tests) |
| Monte Carlo API (DB persist) | ✅ | ✅ | **G-5 해소**: test_06_api_monte_carlo.py (+11 tests) |

### 08 DB_SPEC — Database Schema
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| 16 테이블 스키마 + FK/인덱스 | ✅ | ✅ | test_08_db_errors.py |
| Alembic 마이그레이션 | ✅ | ⚠️ | 마이그레이션 실행 검증 없음 |
| pgvector HNSW 인덱스 | ✅ | ✅ | **G-1 해소**: test_08_db_vector.py (+8 tests) |
| llm_vector_cache 테이블 | ✅ | ✅ | test_08_db_vector.py |

### 09 HARNESS_SPEC — Test Harness
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| F18-F20: Agent/Network/Diffusion harness | ✅ | ✅ | test_09_harness_*.py |
| F21-F22: Replay/Scenario comparator | ✅ | ✅ | |
| F24: Mock environment (sandbox) | ✅ | ✅ | |
| F25: Metric logger | ✅ | ✅ | |
| F26: API hooks | ✅ | ✅ | test_09_harness_f26_api_hooks.py |
| F27-F28: Performance/Recovery | ✅ | ✅ | |
| F23: Scenario comparison | ✅ | ⚠️ | 간접 테스트만 |
| F30: Hybrid exec | ✅ | ✅ | **G-7 해소**: hybrid_exec.py + 18 tests |

### 10 VALIDATION_SPEC — Validation Pipeline
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| VAL-01~08 파이프라인 | ✅ | ✅ | test_10_validation_pipeline.py |
| Cascade Detection F1 | ⚠️ | ⚠️ | F1 score 격리 테스트 없음 |
| NRMSE 정확도 | ⚠️ | ⚠️ | threshold assertion 없음 |

---

## Frontend SPECs

### 07 FRONTEND_SPEC — UI Components
| 페이지 | 구현 | 테스트 | 테스트 파일 |
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
| AnalyticsPage | ✅ | ✅ | AnalyticsPage.test.tsx |
| ComparisonPage | ✅ | ✅ | ComparisonPage.test.tsx |
| CommunityManagePage | ✅ | ✅ | CommunityManagePage.test.tsx |

### Frontend 인프라
| 항목 | 구현 | 테스트 | 비고 |
|------|:----:|:------:|------|
| Zustand Store | ✅ | ✅ | simulationStore.test.ts |
| API Client | ✅ | ✅ | apiClient.test.ts |
| WebSocket Hook | ✅ | ✅ | useSimulationSocket.test.ts |
| FactionMapView (Cytoscape) | ✅ | ✅ | FactionMapView.test.tsx (21 tests) |
| UI_FLOW_SPEC E2E 흐름 검증 | ✅ | ✅ | **G-6 해소**: UIFlowSpec.test.tsx (29 tests) |
| Playwright 브라우저 E2E | ✅ | ✅ | 29 tests (navigation + simulation + modals + API lifecycle) |
| constants.ts 상수 통합 | ✅ | ✅ | 120+ 상수, 12개 파일에서 참조 |

### UI_FLOW_SPEC Known Gaps (10항목)
| 항목 | 상태 | 비고 |
|------|:----:|------|
| WS heartbeat (30s ping) | ✅ | 이미 구현됨 |
| "Click to retry" 배너 | ✅ | retryExhausted + 배너 추가 |
| ProjectScenarios Stop 버튼 | ✅ | 이미 구현됨 |
| ProjectScenarios More(⋯) 버튼 | ✅ | 이미 구현됨 |
| AgentDetail Messages 탭 | ✅ | getMemory API 연동, Mock fallback |
| ConversationThread reaction | ✅ | 로컬 토글 |
| ScenarioOpinions Map/Faction | ✅ | 이미 구현됨 |
| CommunityOpinion Sort | ✅ | 이미 구현됨 |
| Monte Carlo in Analytics | ✅ | 이미 구현됨 |
| `llm.getCalls` API 메서드 | ✅ | apiClient.llm.getCalls() 추가 |

---

## GAP 요약

| # | GAP | 상태 | 비고 |
|---|-----|:----:|------|
| G-1 | pgvector 벡터 검색 + trgm 테스트 | ✅ | +8 tests |
| G-2 | RecSys feed ranking 테스트 | ✅ | +10 tests |
| G-3 | embed 768-dim projection 테스트 | ✅ | +5 tests |
| G-4 | Communities API 전용 테스트 | ✅ | +12 tests |
| G-5 | Monte Carlo DB persist 테스트 | ✅ | +11 tests |
| G-6 | UI_FLOW_SPEC E2E 검증 | ✅ | +29 tests (Vitest) |
| G-7 | F30 Hybrid exec 구현 | ✅ | SPEC + 구현 + 18 tests |

---

## 잔여 ⚠️ 항목 (LOW priority)

| 항목 | SPEC | 설명 |
|------|------|------|
| Network validation threshold 전용 테스트 | 02_NETWORK | clustering/path length bounds 테스트 |
| Network evolution 전용 테스트 | 02_NETWORK | evolve_step 격리 테스트 |
| Monte Carlo 동시성(max-3) 테스트 | 04_SIMULATION | 병렬 제한 검증 |
| F23 Scenario comparison 격리 테스트 | 09_HARNESS | 간접 테스트만 존재 |
| Cascade F1 score 격리 테스트 | 10_VALIDATION | F1 threshold assertion |
| NRMSE 정확도 threshold 테스트 | 10_VALIDATION | threshold assertion |
| Alembic 마이그레이션 실행 검증 | 08_DB | 마이그레이션 통합 테스트 |
| ~~Playwright 브라우저 E2E~~ | ~~07_FRONTEND~~ | ✅ 29 tests passed |

---

## Health Stack Quick Check

```bash
# 전체 확인 명령어
cd backend && uv run pytest tests/ -q          # 819 tests
cd frontend && npx vitest run                   # 344 tests
cd frontend && npx tsc --noEmit                 # 0 errors
cd frontend && npx eslint .                     # 0 errors
docker compose ps                               # 5/5 healthy
```

## 범례
- ✅ 구현 + 테스트 완료
- ⚠️ 구현됨, 테스트 부분적/미흡
- ❌ 미구현 또는 테스트 없음
