# AGENTS.md — Prophet 멀티 에이전트 작업 지침

이 파일은 Claude Code가 병렬 서브에이전트(Agent tool)로 작업할 때 참조하는 지침서입니다.

---

## 에이전트 작업 원칙

1. **SPEC 기반 작업** — 모든 에이전트는 작업 전 `docs/spec/` 의 해당 SPEC 문서를 읽는다.
2. **인터페이스 계약 준수** — 모듈 간 경계는 SPEC에 정의된 인터페이스만 사용한다.
3. **독립적 병렬 작업** — 서로 의존하지 않는 모듈은 병렬 에이전트로 동시 진행한다.
4. **하네스 검증** — 구현 후 반드시 `uv run pytest` 로 하네스 테스트를 통과해야 한다.

---

## 에이전트 역할 분류

### backend-agent
**담당:** 백엔드 Python 코드 구현

| 모듈 | SPEC 문서 | 디렉토리 |
|------|-----------|----------|
| Agent Engine | `01_AGENT_SPEC.md` | `backend/app/engine/agent/` |
| Network Generator | `02_NETWORK_SPEC.md` | `backend/app/engine/network/` |
| Diffusion Engine | `03_DIFFUSION_SPEC.md` | `backend/app/engine/diffusion/` |
| Simulation Orchestrator | `04_SIMULATION_SPEC.md` | `backend/app/engine/simulation/` |
| LLM Adapter | `05_LLM_SPEC.md` | `backend/app/llm/` |
| API Routes | `06_API_SPEC.md` | `backend/app/api/` |
| DB Models | `08_DB_SPEC.md` | `backend/app/models/` |

**규칙:**
- `uv` 만 사용 (pip 금지)
- 모든 함수에 타입 힌트 필수
- `async/await` 우선
- 구현 전 SPEC의 인터페이스 시그니처를 정확히 따른다

---

### frontend-agent
**담당:** React 18 프론트엔드 구현

**디자인 총괄:** `DESIGN.md` (Pencil 연동, 디자인 토큰, 컴포넌트 매핑)

| 모듈 | SPEC 문서 | UI SPEC (Pencil) | 디렉토리 |
|------|-----------|-----------------|----------|
| Simulation Page | `07_FRONTEND_SPEC.md` §2 | `ui/UI_01_SIMULATION_MAIN.md` | `frontend/src/pages/` |
| Communities Page | `07_FRONTEND_SPEC.md` §2 | `ui/UI_02_COMMUNITIES_DETAIL.md` | `frontend/src/pages/` |
| Influencers Page | `07_FRONTEND_SPEC.md` §2 | `ui/UI_03_TOP_INFLUENCERS.md` | `frontend/src/pages/` |
| Agent Detail Page | `07_FRONTEND_SPEC.md` §2 | `ui/UI_04_AGENT_DETAIL.md` | `frontend/src/pages/` |
| Global Metrics Page | `07_FRONTEND_SPEC.md` §2 | `ui/UI_05_GLOBAL_METRICS.md` | `frontend/src/pages/` |
| Graph Panel | `07_FRONTEND_SPEC.md` §4 | `DESIGN.md` §5 Graph Engine | `frontend/src/components/graph/` |
| Timeline Panel | `07_FRONTEND_SPEC.md` §4 | — | `frontend/src/components/timeline/` |
| Control Panel | `07_FRONTEND_SPEC.md` §4 | — | `frontend/src/components/control/` |
| LLM Dashboard | `07_FRONTEND_SPEC.md` §4 | — | `frontend/src/components/llm/` |
| Zustand Store | `07_FRONTEND_SPEC.md` §5 | — | `frontend/src/store/` |
| API Client | `07_FRONTEND_SPEC.md` §8 | — | `frontend/src/api/` |
| TypeScript Types | `07_FRONTEND_SPEC.md` §7 | — | `frontend/src/types/` |

**규칙:**
- TypeScript strict mode
- `interface` 우선 (`type` 은 유니온/인터섹션에만)
- 컴포넌트 props는 SPEC에 정의된 인터페이스를 그대로 사용
- Cytoscape.js 그래프는 1000 노드에서 30fps 이상 유지
- 디자인 토큰은 `DESIGN.md` §3의 CSS Variables 사용 (하드코딩 금지)
- Pencil Frame ID와 React 컴포넌트 매핑은 `DESIGN.md` §10 참조

---

### harness-agent
**담당:** 테스트 하네스 및 pytest 구현

| 모듈 | SPEC 문서 | 디렉토리 |
|------|-----------|----------|
| Mock Environment | `09_HARNESS_SPEC.md` §4 | `backend/harness/mocks/` |
| Fixtures | `09_HARNESS_SPEC.md` §13 | `backend/harness/fixtures/` |
| Runners | `09_HARNESS_SPEC.md` §3 | `backend/harness/runners/` |
| Sandbox | `09_HARNESS_SPEC.md` §8 | `backend/harness/sandbox.py` |
| Acceptance Tests | 각 SPEC 마지막 §Acceptance | `backend/tests/` |

**규칙:**
- 하네스 코드는 프로덕션 코드보다 먼저 작성
- `MockLLMAdapter`, `MockDatabase`는 외부 의존성 없이 동작해야 한다
- pytest mark 필수: `@pytest.mark.phase1`, `@pytest.mark.acceptance` 등
- `uv run pytest -v -m "phaseN"` 으로 Phase별 실행 가능해야 한다

---

### db-agent
**담당:** PostgreSQL 스키마 및 마이그레이션

| 모듈 | SPEC 문서 | 디렉토리 |
|------|-----------|----------|
| SQLAlchemy Models | `08_DB_SPEC.md` §2 | `backend/app/models/` |
| Alembic Migrations | `08_DB_SPEC.md` §4 | `backend/migrations/` |
| pgvector Setup | `08_DB_SPEC.md` §2 (agent_memories) | `backend/app/models/memory.py` |

**규칙:**
- 직접 DDL 실행 금지 — Alembic migration 경유 필수
- `uv run alembic revision --autogenerate -m "description"`
- pgvector IVFFlat 인덱스는 데이터 100건 이상에서만 생성

---

## Phase별 병렬 작업 매트릭스

아래 표는 각 Phase에서 어떤 에이전트가 병렬로 작업할 수 있는지 보여준다.

### Phase 1: 프로젝트 구조 + 하네스 기반

```
┌─────────────────────────────────────────────────────────┐
│ 병렬 작업 가능                                            │
│                                                          │
│  backend-agent          frontend-agent    harness-agent  │
│  ├ uv init              ├ npm create vite  ├ conftest.py │
│  ├ pyproject.toml       ├ package.json     ├ MockLLM     │
│  ├ FastAPI skeleton     ├ Vite config      ├ MockDB      │
│  └ Alembic init         └ Tailwind setup   └ Sandbox     │
│                                                          │
│  db-agent (depends on backend-agent init)                │
│  ├ SQLAlchemy models                                     │
│  └ Initial migration                                     │
└─────────────────────────────────────────────────────────┘
```

### Phase 2–4: 엔진 구현

```
┌─────────────────────────────────────────────────────────┐
│ Phase 2             Phase 3              Phase 4         │
│ (Agent Core)       (Network Generator)  (Diffusion)      │
│                                                          │
│  backend-agent:     backend-agent:       backend-agent:  │
│  ├ agent_core.py    ├ generator.py       ├ exposure.py   │
│  ├ perception.py    ├ community_graph.py ├ propagation.py│
│  ├ memory_layer.py  ├ influencer.py      ├ cascade.py    │
│  ├ emotion.py       └ edge_weights.py    └ sentiment.py  │
│  ├ cognition.py                                          │
│  ├ decision.py      harness-agent:       harness-agent:  │
│  └ influence.py     └ NET-01 ~ NET-10   └ DIF-01~DIF-10 │
│                                                          │
│  harness-agent:                                          │
│  └ AGT-01 ~ AGT-08                                      │
│                                                          │
│  ⚠ Phase 2 와 Phase 3 은 서로 독립 → 병렬 가능            │
│  ⚠ Phase 4 는 Phase 2 + 3 완료 후 시작                    │
└─────────────────────────────────────────────────────────┘
```

### Phase 5–7: 통합

```
┌─────────────────────────────────────────────────────────┐
│ Phase 5               Phase 6              Phase 7       │
│ (LLM Integration)    (Orchestrator)       (Frontend)     │
│                                                          │
│  backend-agent:       backend-agent:       frontend-agent│
│  ├ adapter.py         ├ orchestrator.py    ├ Pages       │
│  ├ ollama_client.py   ├ step_runner.py     ├ GraphPanel  │
│  ├ claude_client.py   ├ metric_collector   ├ Timeline    │
│  ├ openai_client.py   ├ monte_carlo.py     ├ Control     │
│  ├ prompt_builder.py  └ WebSocket          ├ LLM Dash    │
│  └ cache.py                                └ API Client  │
│                                                          │
│  ⚠ Phase 5 와 Phase 7 은 독립 → 병렬 가능                │
│  ⚠ Phase 6 은 Phase 2+3+4+5 완료 후 시작                 │
└─────────────────────────────────────────────────────────┘
```

---

## 에이전트 간 통신 규칙

1. **인터페이스 경계** — 에이전트는 SPEC에 정의된 인터페이스만 통해 다른 모듈과 통신한다. 다른 에이전트의 내부 구현에 직접 의존하지 않는다.

2. **공유 타입** — 모든 공유 데이터 타입은 다음 위치에 정의:
   - Backend: `backend/app/engine/types.py` (공통 dataclass/enum)
   - Frontend: `frontend/src/types/` (TypeScript interfaces)

3. **DB 스키마 변경** — `db-agent` 만 마이그레이션을 생성할 수 있다. 다른 에이전트가 스키마 변경이 필요하면 SPEC을 먼저 업데이트하고 `db-agent`에 위임한다.

4. **API 계약** — `06_API_SPEC.md` 의 엔드포인트 계약이 backend-agent와 frontend-agent의 유일한 접점이다. 양쪽 모두 이 계약을 준수한다.

---

## 에이전트 실행 예시

```
# Phase 1 — 4개 에이전트 병렬 실행
User: "Phase 1 시작해줘"

Claude:
  ├── Agent(backend-agent):  uv init + FastAPI skeleton
  ├── Agent(frontend-agent): Vite + React 18 init
  ├── Agent(harness-agent):  conftest.py + MockLLM + MockDB + Sandbox
  └── Agent(db-agent):       SQLAlchemy models + Alembic init  (after backend init)
```

---

## 체크리스트 — 에이전트 작업 완료 조건

- [ ] SPEC 인터페이스 시그니처와 정확히 일치하는가?
- [ ] 해당 Phase의 Acceptance Criteria 테스트가 작성되었는가?
- [ ] `uv run pytest -v -m "phaseN"` 이 통과하는가?
- [ ] pip을 사용한 곳이 없는가?
- [ ] LLM 호출이 있으면 fallback이 구현되었는가?
- [ ] async/await 패턴을 준수하는가?
- [ ] 타입 힌트가 모든 함수에 있는가?
