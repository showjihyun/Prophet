# MASTER SPEC — Prophet (MCASP)
**Multi-Community Agent Simulation Platform**
Version: 0.2.0 | Status: REVIEW | Date: 2026-04-04

---

## 1. Project Overview

Prophet is an AI-driven virtual society simulation engine that models how campaigns, messages, and behaviors propagate through multi-community social networks. It enables marketing teams, researchers, and policymakers to run pre-launch simulations on a virtual population before committing real-world resources.

### Strategic Positioning — Hybrid Approach

Prophet의 자체 **6-Layer 엔진 + Viral Cascade Algorithm**을 유지하되,
OASIS의 **RecSys 개념**(추천 알고리즘 기반 노출 모델)과 **시간 모델**(가변 시간 단위)을 차용하는 하이브리드 전략.

**Prophet 고유 강점 (OASIS에 없는 것):**
- **3-Tier 비용 제어** — Mass SLM → Heuristic → Elite LLM 단계적 호출로 비용 최적화
- **수학적 예측 (Cascade Detection)** — Viral/Polarization/Collapse 자동 감지
- **마케팅 메트릭** — viral_probability, community_adoption, expert_sensitivity 등 기업용 KPI

**OASIS에서 차용하는 요소:**
- **RecSys-style Exposure Model** — 단순 랜덤 노출이 아닌, 추천 알고리즘 시뮬레이션으로 feed ranking
- **Temporal Model** — 고정 tick이 아닌, 이벤트 유형에 따른 가변 시간 단위 지원

**MiroFish 참조 아키텍처:** MiroFish = OASIS + GraphRAG + Zep Cloud (장기 기억)

**OASIS 알려진 한계 (Prophet 설계 시 회피 대상):**
1. LLM 편향 — 비검열 모델은 극단화, 정렬 모델은 과도한 중립화
2. 전파 깊이 — 현실 대비 일관되게 낮음
3. 컴퓨팅 비용 — 100K 유저 = A100 5대, 10스텝에 ~2일
4. 플랫폼 범위 — Twitter/Reddit만 지원
5. 합성 프로필 — 실제 인간 행동 복잡성 재현 한계

### Competitive Reference

| Platform | Strength | Gap vs Prophet | Prophet 차용 |
|----------|----------|----------------|-------------|
| **Miro Fish** | Visual social graph exploration | No diffusion engine, no LLM cognition | — |
| **Stanford Smallville** | Realistic LLM-driven agent behavior | No social network model, no diffusion | — |
| **NetLogo** | Mature ABM framework | No LLM, no GraphRAG, no real-time UI | — |
| **OASIS** | Large-scale social sim, RecSys model | No marketing focus, no SaaS, no cost control (CAMEL-AI open source, core of MiroFish) | **RecSys exposure + time model** |
| **Prophet (MCASP)** | LLM + GraphRAG + Viral Diffusion + Marketing SaaS | **This system** | — |

Prophet's differentiation: combining **Network Science + Behavioral Economics + LLM Cognition** in a single platform, purpose-built for marketing/policy use cases. OASIS의 RecSys/시간 모델을 차용하여 노출 현실성을 강화하되, 3-Tier 비용 제어와 마케팅 메트릭은 Prophet 고유 경쟁력으로 유지.

---

## 2. Tech Stack

### Backend
| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.12+ |
| API Framework | FastAPI | 0.115+ |
| ORM | SQLAlchemy (async) | 2.0+ |
| Task Queue | asyncio.create_task (Monte Carlo, in-process) | built-in |
| Async Engine | asyncio (step loop, real-time) | built-in |
| SLM Inference | Ollama (vLLM optional) | local GPU/CPU |
| WebSocket | FastAPI WebSocket | built-in |
| Graph Engine | NetworkX | 3.x |
| Numerics | NumPy, SciPy | latest |
| Package Manager | **uv** (only — pip is prohibited) | latest |

### LLM
| Provider | Client Library | Role |
|----------|---------------|------|
| Ollama (local) | `ollama-python` | Primary (cost-free, default) |
| Anthropic Claude | `anthropic` SDK | High-quality reasoning |
| OpenAI | `openai` SDK | Alternative cloud |

LLM calls are abstracted behind `LLMAdapter` interface — provider is swappable per agent or per simulation run.

### Database
| Store | Technology | Purpose |
|-------|-----------|---------|
| Primary DB | PostgreSQL 16 | All relational data |
| Vector Store | pgvector (extension) | Agent memory embeddings |
| Cache | Valkey | LLM response cache, session state |
| Graph Store | In-process (NetworkX) | Runtime social graph |

### Frontend
| Layer | Technology | Version |
|-------|-----------|---------|
| Framework | React | 18.x |
| Build Tool | Vite | 5.x |
| Graph Visualization | Cytoscape.js | 3.x |
| Timeline/Metrics | Recharts | 2.x |
| State Management | Zustand | 4.x |
| Data Fetching | TanStack Query | 5.x |
| Styling | Tailwind CSS | 3.x |
| Real-time | WebSocket (native) | — |

---

## 3. SPEC Document Index

| # | Document | Version | Description | Status |
|---|----------|---------|-------------|--------|
| 00 | [ARCHITECTURE.md](./00_ARCHITECTURE.md) | 0.2.0 | System architecture, component diagram | REVIEW |
| 01 | [AGENT_SPEC.md](./01_AGENT_SPEC.md) | 0.3.0 | Agent 6-Layer interface contracts | REVIEW |
| 02 | [NETWORK_SPEC.md](./02_NETWORK_SPEC.md) | 0.1.0 | Hybrid network generator spec | DRAFT |
| 03 | [DIFFUSION_SPEC.md](./03_DIFFUSION_SPEC.md) | 0.1.0 | Social diffusion engine spec | DRAFT |
| 04 | [SIMULATION_SPEC.md](./04_SIMULATION_SPEC.md) | 0.2.0 | Simulation orchestrator spec | REVIEW |
| 05 | [LLM_SPEC.md](./05_LLM_SPEC.md) | 0.2.0 | LLM adapter + prompt management + gateway | REVIEW |
| 06 | [API_SPEC.md](./06_API_SPEC.md) | 0.2.0 | FastAPI endpoint contracts (53 endpoints) | REVIEW |
| 07 | [FRONTEND_SPEC.md](./07_FRONTEND_SPEC.md) | 0.2.0 | React 18 — 16 pages, 30+ components | REVIEW |
| 08 | [DB_SPEC.md](./08_DB_SPEC.md) | 0.2.0 | PostgreSQL schema + pgvector + projects | REVIEW |
| 09 | [HARNESS_SPEC.md](./09_HARNESS_SPEC.md) | 0.1.0 | Test harness F18–F30 spec | DRAFT |
| 10 | [VALIDATION_SPEC.md](./10_VALIDATION_SPEC.md) | 0.1.0 | Validation methodology (Twitter15/16 reference) | DRAFT |
| 11 | [SKILLS_SPEC.md](./11_SKILLS_SPEC.md) | 0.1.0 | Plugins & custom skills configuration | DRAFT |
| -- | [INIT_REQUIREMENTS.md](./INIT_REQUIREMENTS.md) | 원본 기획서 9개 통합 (source of truth) | BASELINE |
| UI-01 | [UI_01_SIMULATION_MAIN.md](./ui/UI_01_SIMULATION_MAIN.md) | Main simulation screen (Pencil sync) | DRAFT |
| UI-02 | [UI_02_COMMUNITIES_DETAIL.md](./ui/UI_02_COMMUNITIES_DETAIL.md) | Communities detail screen (Pencil sync) | DRAFT |
| UI-03 | [UI_03_TOP_INFLUENCERS.md](./ui/UI_03_TOP_INFLUENCERS.md) | Top influencers screen (Pencil sync) | DRAFT |
| UI-04 | [UI_04_AGENT_DETAIL.md](./ui/UI_04_AGENT_DETAIL.md) | Agent detail screen (Pencil sync) | DRAFT |
| UI-05 | [UI_05_GLOBAL_METRICS.md](./ui/UI_05_GLOBAL_METRICS.md) | Global insight & metrics screen (Pencil sync) | DRAFT |
| UI-06 | [UI_06_PROJECTS_LIST.md](./ui/UI_06_PROJECTS_LIST.md) | Projects list screen (Pencil sync) | DRAFT |
| UI-07 | [UI_07_PROJECT_SCENARIOS.md](./ui/UI_07_PROJECT_SCENARIOS.md) | Project scenarios screen (Pencil sync) | DRAFT |
| UI-08 | [UI_08_INFLUENCERS_PAGINATION.md](./ui/UI_08_INFLUENCERS_PAGINATION.md) | Influencers with pagination (Pencil sync) | DRAFT |
| UI-09 | [UI_09_INFLUENCERS_FILTER.md](./ui/UI_09_INFLUENCERS_FILTER.md) | Influencers filter popover (Pencil sync) | DRAFT |
| UI-10 | [UI_10_AGENT_INTERVENE.md](./ui/UI_10_AGENT_INTERVENE.md) | Agent intervention modal (Pencil sync) | DRAFT |
| UI-11 | [UI_11_AGENT_CONNECTIONS.md](./ui/UI_11_AGENT_CONNECTIONS.md) | Agent connections tab (Pencil sync) | DRAFT |
| UI-12 | [UI_12_SETTINGS.md](./ui/UI_12_SETTINGS.md) | Settings page (Pencil sync) | DRAFT |
| 12 | [PLATFORM_PLUGIN_SPEC.md](./platform/12_PLATFORM_PLUGIN_SPEC.md) | SNS platform plugins (Twitter/Reddit/Instagram) | DRAFT |
| 13 | [SCALE_VALIDATION_SPEC.md](./platform/13_SCALE_VALIDATION_SPEC.md) | Scale benchmark & validation pipeline | DRAFT |
| 14 | [LLM_GATEWAY_SPEC.md](./platform/14_LLM_GATEWAY_SPEC.md) | LLM gateway + cache chain + quota | DRAFT |
| 15 | [15_DEV_WORKFLOW_SPEC.md](./15_DEV_WORKFLOW_SPEC.md) | Development workflow & model selection strategy | DRAFT |
| UI-13 | [UI_13_SCENARIO_OPINIONS.md](./ui/UI_13_SCENARIO_OPINIONS.md) | Scenario opinions overview (Pencil sync) | DRAFT |
| UI-14 | [UI_14_COMMUNITY_OPINION.md](./ui/UI_14_COMMUNITY_OPINION.md) | Community opinion detail (Pencil sync) | DRAFT |
| UI-15 | [UI_15_CONVERSATION_THREAD.md](./ui/UI_15_CONVERSATION_THREAD.md) | Conversation thread view (Pencil sync) | DRAFT |
| UI-16 | [UI_16_CAMPAIGN_SETUP.md](./ui/UI_16_CAMPAIGN_SETUP.md) | Campaign setup wizard (community config, LLM provider) | DRAFT |

---

## 4. Non-Functional Requirements

| ID | Category | Requirement |
|----|----------|-------------|
| NF01 | Performance | 1,000 agent step execution ≤ 1 second (rule engine path) |
| NF02 | Scalability | Agent count, community count, LLM provider are all pluggable |
| NF03 | Reliability | LLM call failure triggers retry (3x) then fallback to rule engine |
| NF04 | Real-time | WebSocket pushes step results within 500ms of completion |
| NF05 | Testability | Every module has harness mock + unit test hook (F18–F30) |
| NF06 | LLM Cost | LLM calls limited to ≤20% of agents per step (Tier 3 only) |
| NF07 | Observability | All LLM prompts/responses + step metrics logged to PostgreSQL |
| NF08 | Security | API Key management via env vars; pgvector data scoped per simulation |
| NF09 | CI/CD | GitHub Actions 사용하지 않음. 로컬 Docker Compose 기반 개발/배포 |
| NF10 | 배포 | Docker Compose (PostgreSQL + Valkey + Ollama + Backend + Frontend) |
| NF11 | Security | `.env.*` 패턴 전체 gitignore. API Key는 환경변수만 허용 |
| NF12 | CORS | `allow_origins`는 환경변수로 설정. localhost 하드코딩 금지 |

---

## 5. Core Data Models (Summary)

```
Simulation Run
  └── Campaign (input event)
  └── Communities [A, B, C, D, E]
        └── Agents (1000 total)
              ├── Memory (Episodic + Semantic + Social → pgvector)
              ├── Personality [openness, skepticism, trend_following, brand_loyalty, social_influence]
              ├── Emotion [interest, trust, skepticism, excitement]
              └── SocialLinks (NetworkX edges)
  └── Steps [t=0..N]
        └── AgentState per step
        └── Events (campaign exposure, expert review, viral cascade)
        └── Metrics (adoption_rate, sentiment, viral_probability)
```

---

## 6. Git & Repository

| 항목 | 값 |
|------|-----|
| **Repository** | `https://github.com/showjihyun/Prophet.git` |
| **기본 브랜치** | `master` |
| **CI/CD** | GitHub Actions 사용하지 않음 |
| **배포** | 로컬 Docker Compose |
| **커밋 규칙** | Phase 단위 커밋, Co-Authored-By trailer 포함 |

### 브랜치 전략

```
master (기본, 안정 브랜치)
  └── feature/* (기능 개발 시)
  └── fix/* (버그 수정 시)
```

- `master`에 직접 커밋 가능 (1인 개발)
- 대규모 변경 시 feature 브랜치 → PR 권장
- force push 금지

### Documentation Language

| 문서 | 언어 |
|------|------|
| `README.md` | **English only** |
| `CLAUDE.md` | Korean (Claude Code 지침) |
| `AGENTS.md` | Korean (에이전트 지침) |
| `DESIGN.md` | Korean + English mixed |
| `docs/spec/*.md` | English (코드 인터페이스) + Korean (설명) |

### .gitignore 주요 규칙

```
.venv/              # Python 가상환경 (uv 관리)
node_modules/       # Node 의존성
.env                # 환경변수 (secrets)
__pycache__/        # Python 캐시
.agents/            # skills.sh 스킬 원본
.claude/skills/     # 스킬 심볼릭 링크
.claude/settings.local.json  # 로컬 설정
```

---

## 7. Tooling Rules

### Package Management — uv only

**`pip` is prohibited in this project.** All Python package operations must use `uv`.

| Task | Command |
|------|---------|
| 프로젝트 초기화 | `uv init` |
| 의존성 추가 | `uv add <package>` |
| dev 의존성 추가 | `uv add --dev <package>` |
| 의존성 제거 | `uv remove <package>` |
| 환경 동기화 | `uv sync` |
| 스크립트 실행 | `uv run <script>` |
| pytest 실행 | `uv run pytest` |
| 패키지 잠금 | `uv lock` |

- 의존성 파일: `pyproject.toml` + `uv.lock` (requirements.txt 사용 금지)
- 가상환경은 `uv`가 자동 관리 (`.venv/` 디렉토리)
- CI/CD에서도 `pip install` 대신 `uv sync --frozen` 사용

---

## 8. Error Handling Policy (Cross-Cutting)

### 7.1 Exception Hierarchy

```
ProphetBaseError
├── ValidationError            — Invalid input at system boundary
│   ├── ConfigValidationError  — Invalid simulation/community config
│   └── SchemaValidationError  — Invalid data model fields
├── SimulationError            — Runtime simulation failures
│   ├── SimulationStepError    — Step execution crash
│   ├── SimulationCapacityError — Max concurrent simulations exceeded
│   ├── InvalidStateTransitionError — Illegal lifecycle state change
│   └── StepNotFoundError      — Replay target step not persisted
├── NetworkError               — Network generation/evolution failures
│   └── NetworkValidationError — Graph constraint violated
├── LLMError                   — LLM integration failures
│   ├── LLMTimeoutError        — Provider response timeout
│   ├── LLMParseError          — Invalid JSON response from provider
│   ├── LLMRateLimitError      — HTTP 429 rate limit
│   ├── LLMAuthError           — HTTP 401/403 authentication failure
│   ├── LLMProviderError       — HTTP 5xx server error
│   ├── LLMTokenLimitError     — Prompt exceeds model token limit
│   ├── OllamaConnectionError  — Local Ollama server unreachable
│   └── EmbeddingDimensionError — Embedding vector dimension mismatch
├── DBError                    — Database failures
│   ├── ConnectionPoolExhaustedError
│   ├── PgVectorUnavailableError
│   ├── MigrationConflictError
│   └── DBPersistenceError     — Write failure during step persistence
└── AgentError                 — Agent-level failures
    └── AgentNotFoundError     — Agent ID not found in DB
```

### 7.2 Recovery Strategy Matrix

| Strategy | When | Example |
|----------|------|---------|
| **Fallback Tier** | LLM failure | Tier 3 timeout → Tier 2 → Tier 1 |
| **Clamp** | Numeric boundary violation during computation | Probability 1.3 → 1.0 |
| **Reject** | Invalid input at system boundary | Config with negative agents |
| **Retry** | Transient failures (network, DB deadlock) | Max 3 retries with exponential backoff |
| **Graceful Degradation** | Non-critical subsystem down | pgvector down → recency-only memory |
| **Fatal** | Core subsystem down | Ollama unreachable → FAILED |
| **No-op** | Expected empty state | No active campaign → skip pipeline |

### 7.3 Logging Levels

| Level | Usage |
|-------|-------|
| **CRITICAL** | System cannot continue (Ollama down, migration conflict, disk full) |
| **ERROR** | Operation failed, requires attention (DB write fail, auth error) |
| **WARN** | Recovered automatically but noteworthy (clamped value, LLM fallback, retry) |
| **INFO** | Expected state transitions (quota block, cache eviction) |
| **DEBUG** | Diagnostic detail (missing edge default, skip inactive hour) |

### 7.4 Rules

1. **Never swallow exceptions silently** — Every catch must log or re-raise.
2. **Fallback chain is mandatory for LLM** — Tier 3 → Tier 2 → Tier 1. Simulation MUST complete.
3. **Clamp, don't crash** — Numeric overflows during computation are clamped with WARN log, not exceptions.
4. **Reject at boundaries, recover internally** — `ValueError` at API/config input; graceful recovery inside engine.
5. **Idempotent retries** — All retry-able operations must be safe to re-execute.

---

## 9. SPEC DRIVEN Development Rules

1. **SPEC first** — No implementation begins without a corresponding SPEC section.
2. **Interface contract is law** — Function signatures, input/output types, and behavior defined in SPEC must not be violated by implementation.
3. **Harness gates implementation** — Each Phase must have passing harness tests before the next Phase begins.
4. **SLM is base, LLM is optional** — Tier 1 runs on local SLM. Every Tier 3 (Elite LLM) behavior must have Tier 1 (SLM) fallback so simulation runs without any external LLM provider.
5. **PostgreSQL is source of truth** — All simulation state must be persisted; in-memory state is cache only.
6. **SPEC changes require version bump** — Breaking SPEC changes increment minor version; additive changes increment patch.
7. **uv only** — No `pip`, `pip3`, `pip install` anywhere in the codebase, scripts, Dockerfile, or CI.

---

## 10. Implementation Status (2026-04-04)

### Phase Completion

| Phase | 내용 | 상태 | 테스트 |
|-------|------|------|--------|
| Phase 0 | SPEC 작성 | ✅ 완료 | 15 SPEC + 16 UI SPEC |
| Phase 1 | 프로젝트 구조 + 하네스 기반 | ✅ 완료 | 8/8 GREEN |
| Phase 2 | Agent Core (6-Layer) | ✅ 완료 | 81/81 GREEN |
| Phase 3 | Network Generator | ✅ 완료 | 19/19 GREEN |
| Phase 4 | Diffusion Engine | ✅ 완료 | 78/78 GREEN |
| Phase 5 | LLM Integration | ✅ 완료 | 92/92 GREEN |
| Phase 6 | Simulation Orchestrator + API | ✅ 완료 | 127/127 GREEN |
| Phase 7 | Visualization (Frontend) | ✅ 완료 | tsc 0 errors |
| Phase A | API→Frontend 37 endpoints 연결 | ✅ 완료 | — |
| Phase B | 5개 기능 UI (Inject/Replay/MC/Engine/Compare) | ✅ 완료 | — |
| Phase C | Mock→Real API (5 pages) | ✅ 완료 | — |
| Phase D | Design tokens (70+ 색상) + Vitest (145 tests) | ✅ 완료 | — |
| DB | PostgreSQL persistence (fire-and-forget) | ✅ 완료 | — |
| LLM | Async Tier 3 cognition | ✅ 완료 | — |
| VAL | Validation pipeline VAL-01~08 | ✅ 완료 | 33 tests |
| S | Silent Stub 해소 | ✅ 완료 | — |
| M | Mock→Real (GlobalMetrics/Opinions/Thread) | ✅ 완료 | — |
| T | 실패 테스트 수정 + CampaignSetup | ✅ 완료 | — |
| F | Campaign Setup + Project CRUD + EgoGraph Filter | ✅ 완료 | — |

### Test Summary

| Target | Count | Command |
|--------|-------|---------|
| Backend | 586 passed, 1 skipped | `uv run pytest tests/` |
| Frontend | 180+ passed | `npx vitest run` |
| E2E | 26 tests (Docker required) | `npx playwright test` |
| **Total** | **795+** | — |

### Performance Benchmarks (2026-03-30)

| Metric | Result | SPEC Goal |
|--------|--------|-----------|
| 1,000 agents x 1 step | **287ms avg** | <1,000ms (NF01) |
| Simulation creation (1,000 agents + network) | 1,362ms | — |
| Docker E2E (5 services healthy) | ✅ | — |

### Key Capabilities (Post-SPEC additions)

| Feature | Status | Notes |
|---------|--------|-------|
| JWT Authentication | ✅ | `/api/v1/auth/*` endpoints |
| Project/Scenario Management | ✅ | Full CRUD |
| Community Templates | ✅ | File-based persistence |
| LLM Gateway (3-tier cache) | ✅ | InMemory → Vector → Valkey |
| vLLM Adapter | ✅ | Distributed inference |
| Export (JSON/CSV) | ✅ | `GET /simulations/{id}/export` |
| Group Chat | ✅ | Multi-agent discussions |
| Agent Interview | ✅ | Mid-simulation interviews |
| Dark/Light Theme | ✅ | CSS variables + Zustand |
| Inline Simulation Creation | ✅ | No page navigation |
| Run-All Endpoint | ✅ | `POST /simulations/{id}/run-all` |
| 53 API Endpoints | ✅ | 16 pages, 15 routes |
