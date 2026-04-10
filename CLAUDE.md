# CLAUDE.md — Prophet (MCASP)

이 파일은 Claude Code가 이 프로젝트에서 작업할 때 항상 참조하는 지침서입니다.

---

## 프로젝트 개요

**Prophet = MCASP (Multi-Community Agent Simulation Platform)**

AI 기반 가상 사회에서 마케팅 캠페인/정책/메시지의 확산을 사전 시뮬레이션하는 플랫폼.
LLM + GraphRAG + Viral Diffusion 을 결합한 Agent 기반 사회 시뮬레이션 엔진.

- SPEC 문서: `docs/spec/` (현재 4개 파일 — 상세 목록은 `docs/spec/MASTER_SPEC.md`)
- 원본 기획서: `docs/init/` (읽기 전용 참조)
- Master SPEC: `docs/spec/MASTER_SPEC.md` (인덱스)
- **컨텍스트 전략**: `HARNESS.md` (6가지 원칙 — 계층/계약/검증/인지배분/병렬분할/부패방지)

> **Note:** 핵심 SPEC (00-09, UI) 은 `.gitignore` 로 관리됨 (비공개 IP 보호).
> 로컬에서 삭제된 상태라면 코드 docstring 의 `SPEC:` 참조는 역사적 참조로 취급한다.

---

## 개발 방식

**SPEC DRIVEN + 하네스 엔지니어링**

### ⛔ SPEC-GATE 규칙 (절대 위반 금지)

1. **SPEC 없으면 코드 없다**
   - 구현하려는 기능의 SPEC이 `docs/spec/`에 존재하지 않으면 **코드를 작성하지 않는다.**
   - SPEC이 없는 기능을 요청받으면 반드시 **SPEC을 먼저 작성**한 뒤 구현에 진입한다.
   - SPEC 작성 → 사용자 확인 → 구현 순서를 반드시 따른다.

2. **SPEC 매핑 확인 절차**
   - 코드 구현 전 아래 체크리스트를 반드시 수행:
     ```
     □ 해당 기능의 SPEC 문서가 docs/spec/ 에 존재하는가?
     □ SPEC에 함수 시그니처, 입출력 타입이 정의되어 있는가?
     □ SPEC 버전과 현재 구현 대상이 일치하는가?
     ```
   - 하나라도 NO이면 **구현을 중단**하고 SPEC 작성/갱신부터 한다.

3. **SPEC-to-Code 트레이서빌리티**
   - 모든 모듈/클래스 docstring에 SPEC 참조를 명시한다:
     ```python
     class PerceptionLayer:
         """Agent Perception Layer.
         SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perception
         """
     ```
     ```typescript
     /**
      * SimulationDashboard component
      * @spec docs/spec/07_FRONTEND_SPEC.md#simulation-dashboard
      */
     ```

4. **SPEC 인터페이스 계약은 법이다**
   - SPEC에 정의된 함수 시그니처, 입출력 타입을 위반하지 않는다.
   - 인터페이스를 변경해야 하면 **SPEC을 먼저 수정**하고, 버전을 올린 뒤 코드를 변경한다.

### 현재 SPEC 파일 (docs/spec/)

| SPEC 문서 | 커버 범위 | 상태 |
|-----------|----------|------|
| `MASTER_SPEC.md` | 전체 인덱스 | ✅ 현행 |
| `SPEC_CHECKLIST.md` | 전체 테스트 수/coverage 체크리스트 | ✅ 현행 |
| `16_COMMUNITY_MGMT_SPEC.md` | 커뮤니티 CRUD + 템플릿 관리 | ✅ 현행 |
| `17_PERFORMANCE_SPEC.md` | 백엔드 성능 최적화 | ✅ 현행 |
| `18_FRONTEND_PERFORMANCE_SPEC.md` | 프론트엔드 성능 + 3D Graph + AgentDetail + SimulationList | ✅ 현행 |
| `19_SIMULATION_INTEGRITY_SPEC.md` | 시뮬레이션 신뢰성 감사 (6 Phase) | ✅ 현행 |
| `20_CLEAN_ARCHITECTURE_SPEC.md` | Clean Architecture (Repository/Service/Controller) | ✅ 현행 |
| `21_SIMULATION_QUALITY_SPEC.md` | 시뮬레이션 품질 (P1 SQ + P2 EC/BC/CG + P3 RF/HM/MP 통합본) | ✅ 현행 |
| `22_CONVERSATION_THREAD_SPEC.md` | 실 thread capture + storage + API | ✅ 현행 |
| `23_EXPERT_LLM_SPEC.md` | Expert engine LLM 통합 (+ rule-based fallback) | ✅ 현행 |

> **통합 이력**: 구 `19_SIMULATION_QUALITY_SPEC.md`, `20_SIMULATION_QUALITY_P2_SPEC.md`,
> `21_SIMULATION_QUALITY_P3_SPEC.md` 3개 파일은 2026-04-10 `21_SIMULATION_QUALITY_SPEC.md`
> 로 통합되었다. 기존의 `SQ-`, `EC-`, `BC-`, `CG-`, `RF-`, `HM-`, `MP-` anchor 는 전부 보존됨.
>
> 핵심 엔진 SPEC (00-09) 과 UI SPEC (16개) 은 IP 보호를 위해 `.gitignore` 등록됨.
> 코드 docstring 의 `SPEC: docs/spec/01_AGENT_SPEC.md#...` 참조는 역사적 참조.

### SPEC 변경 시 테스트 자동 생성 규칙

> **핵심 원칙: SPEC 변경 → 테스트 먼저 생성 → 그 다음 코드 구현 (Red-Green-Refactor)**
>
> 테스트는 SPEC 계약을 검증하는 것이지, 구현을 추종하는 것이 아니다.
> SPEC만으로 테스트를 작성할 수 있어야 하며, 구현이 없는 상태에서 테스트는 FAIL 해야 정상이다.

**Backend SPEC 변경 시:**
- SPEC에 정의된 모든 public 인터페이스에 대해 `backend/tests/` 에 테스트 파일을 **코드 구현 전에** 생성/갱신한다.
- 테스트 파일 네이밍: `test_{spec번호}_{모듈명}.py`
  - 예: `01_AGENT_SPEC.md` 변경 → `test_01_perception.py`, `test_01_memory.py`, ...
- 테스트는 **구현이 없는 상태에서 실패(Red)** 하도록 작성한다:
  ```python
  """
  Auto-generated from SPEC: docs/spec/01_AGENT_SPEC.md
  SPEC Version: 0.1.0
  Generated BEFORE implementation — tests define the contract.
  """
  import pytest

  class TestPerceptionLayer:
      """SPEC: 01_AGENT_SPEC.md#layer-1-perception"""

      def test_observe_returns_perception_result(self):
          """SPEC 계약: observe() → PerceptionResult"""
          from app.engine.agent.perception import PerceptionLayer
          layer = PerceptionLayer()
          result = layer.observe(agent=..., events=[], neighbors=[])
          assert hasattr(result, 'feed_items')
          assert hasattr(result, 'social_signals')
          assert hasattr(result, 'total_exposure_score')

      def test_observe_ranks_by_exposure_score(self):
          """SPEC 계약: feed_items ranked by exposure_score desc"""
          from app.engine.agent.perception import PerceptionLayer
          layer = PerceptionLayer()
          result = layer.observe(agent=..., events=mock_events, neighbors=[])
          scores = [item.exposure_score for item in result.feed_items]
          assert scores == sorted(scores, reverse=True)
  ```
- 테스트 작성 후 `uv run pytest --collect-only` 로 테스트가 수집되는지 확인
- 하네스 테스트도 함께 갱신: `backend/harness/` 의 해당 러너

**Frontend SPEC 변경 시:**
- SPEC에 정의된 모든 컴포넌트/훅에 대해 `frontend/src/__tests__/` 에 테스트 파일을 **코드 구현 전에** 생성/갱신한다.
- 테스트 파일 네이밍: `{ComponentName}.test.tsx` 또는 `{hookName}.test.ts`
- 테스트는 **구현이 없는 상태에서 실패(Red)** 하도록 작성한다:
  ```typescript
  /**
   * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md
   * SPEC Version: 0.1.0
   * Generated BEFORE implementation — tests define the contract.
   */
  import { render, screen } from '@testing-library/react';

  describe('SimulationDashboard', () => {
    /** @spec 07_FRONTEND_SPEC.md#simulation-dashboard */
    it('renders graph visualization panel', () => {
      // Will fail until SimulationDashboard is implemented
      const { SimulationDashboard } = require('@/components/SimulationDashboard');
      render(<SimulationDashboard />);
      expect(screen.getByTestId('graph-panel')).toBeInTheDocument();
    });

    it('displays real-time metrics via WebSocket', () => {
      const { SimulationDashboard } = require('@/components/SimulationDashboard');
      render(<SimulationDashboard />);
      expect(screen.getByTestId('metrics-panel')).toBeInTheDocument();
    });
  });
  ```

**API SPEC 변경 시 (양쪽 모두):**
- Backend: `backend/tests/test_06_api_{endpoint}.py` 생성
- Frontend: `frontend/src/api/__tests__/{endpoint}.test.ts` 생성
- API 계약 테스트는 요청/응답 스키마 검증을 반드시 포함

### SPEC 신규 작성 절차

SPEC이 존재하지 않는 기능 요청 시:

```
1. docs/spec/ 에 해당 SPEC 문서 생성 (기존 번호 체계 준수)
2. MASTER_SPEC.md 에 참조 추가
3. 사용자에게 SPEC 리뷰 요청
4. 승인 후 테스트 코드 생성 (구현 전에!)
5. 테스트가 FAIL 하는 것을 확인 (Red)
6. 코드 구현 시작 (테스트 통과 목표)
7. 테스트 PASS 확인 (Green)
```

### 하네스 우선 개발 흐름 (Red-Green-Refactor)

```
SPEC 확인/작성
     ↓
테스트 코드 생성 (SPEC 계약 기반, 구현 전에!)
     ↓
테스트 실행 → 전부 FAIL 확인 (Red)
     ↓
하네스 픽스처/목 작성
     ↓
코드 구현 (테스트 통과 목표)
     ↓
테스트 실행 → 전부 PASS 확인 (Green)
     ↓
리팩토링 (테스트 유지한 채 코드 개선)
     ↓
Phase 완료
```

5. 각 Phase는 하네스 테스트가 통과해야 다음 Phase로 진행한다.
6. LLM 의존 기능은 반드시 SLM(Tier 1) fallback을 가져야 한다.

### 개발 모델 선택 전략 (Think with Opus, Code with Sonnet)

> **SPEC: `docs/spec/15_DEV_WORKFLOW_SPEC.md`**

Prophet 시뮬레이션의 3-Tier 전략을 개발 워크플로우에도 적용한다.

| 작업 유형 | 모델 | 비율 |
|-----------|------|------|
| **계획/분석**: SPEC 작성, Plan 수립, 아키텍처 설계, 감사, 복잡한 디버깅 | **Opus 4.6** | ~10% |
| **구현/테스트**: 코드 작성, 테스트 생성, 리팩토링, 코드 리뷰, 보일러플레이트 | **Sonnet 4.6** | ~80% |
| **직접 도구**: Glob, Grep, Read (모델 불필요) | — | ~10% |

**Agent tool 호출 시 `model` 파라미터를 명시한다:**
```
# Planning — Opus
Agent(subagent_type="Plan", model="opus")

# Code implementation — Sonnet
Agent(subagent_type="general-purpose", model="sonnet")

# Deep exploration — Opus
Agent(subagent_type="Explore", model="opus")

# Code review — Sonnet
Agent(subagent_type="feature-dev:code-reviewer", model="sonnet")
```

**예외**: 사용자가 모델을 명시적으로 지정하면 즉시 반영.

---

## 기술 스택

### 백엔드
- **Python 3.12+** / **FastAPI** (async)
- **SQLAlchemy 2.0** (async ORM) + **Alembic** (마이그레이션)
- **PostgreSQL 16** + **pgvector** (벡터 메모리)
- **Valkey** (LLM 캐시, 세션)
- **NetworkX** (소셜 그래프 런타임)


### LLM
- **Ollama** (로컬, 기본값) — `ollama-python`
- **Claude API** — `anthropic` SDK
- **OpenAI API** — `openai` SDK

### 프론트엔드
- **React 18** + **TypeScript** + **Vite**
- **react-force-graph-3d** (three.js 기반 3D 그래프 시각화)
- **Cytoscape.js** (EgoGraph 등 보조 2D 그래프)
- **Recharts** (Timeline/Metric 차트)
- **Zustand** (상태 관리)
- **TanStack Query** (서버 상태 — 전 페이지 마이그레이션 완료)
- **Tailwind CSS** + **shadcn/ui**

---

## 패키지 관리 — uv 전용

```bash
# ✅ 올바른 방법
uv add <package>
uv add --dev <package>
uv sync
uv run <command>
uv run pytest
uv run uvicorn app.main:app --reload

# ❌ 절대 금지
pip install ...
pip3 install ...
python -m pip install ...
```

- 의존성 파일: `pyproject.toml` + `uv.lock`
- `requirements.txt` 생성 금지

---

## 디렉토리 구조

```
Prophet/
├── CLAUDE.md          ← 이 파일
├── AGENTS.md          ← 멀티 에이전트 작업 지침
├── DESIGN.md          ← UI 디자인 총괄 (Pencil 연동)
├── docs/
│   ├── init/          ← 원본 기획서 (읽기 전용, 12개 파일)
│   └── spec/          ← SPEC 문서 (현재 5개 파일, MASTER_SPEC.md 참조)
├── backend/           ← FastAPI 백엔드
│   ├── app/
│   ├── harness/       ← F18–F30 테스트 하네스
│   ├── tests/
│   ├── migrations/    ← Alembic
│   └── pyproject.toml
└── frontend/          ← React 18 프론트엔드
    ├── src/
    └── package.json
```

---

## 코딩 규칙

### Python
- `async/await` 우선 — 동기 코드는 I/O 없는 순수 계산에만 허용
- 타입 힌트 필수 — 모든 함수 파라미터와 반환값에 타입 명시
- `@dataclass` 또는 `pydantic BaseModel` 로 데이터 구조 정의
- 예외는 구체적인 타입으로 (`LLMTimeoutError`, `NetworkValidationError` 등)
- 테스트는 `uv run pytest` 로 실행

### TypeScript / React
- `interface` 우선 (`type` 은 유니온/인터섹션에만)
- React 18 — `use client` 없음 (Vite SPA)
- Zustand store는 `src/store/` 에만
- API 호출은 `src/api/client.ts` 를 통해서만
- **⛔ 도메인 enum 리터럴 하드코딩 금지** — `SimulationStatus`, `AgentAction` 등의
  값은 절대 인라인 문자열로 쓰지 않는다. `@/config/constants`의 `SIM_STATUS`,
  `TERMINAL_SIM_STATUSES`, `STARTABLE_SIM_STATUSES` 등 상수를 사용한다.
  새 enum 값이 필요하면 `constants.ts`에 먼저 추가한 후 import해서 쓴다.
  SPEC: `docs/spec/18_FRONTEND_PERFORMANCE_SPEC.md`

### DB
- 모든 마이그레이션은 Alembic으로 (`uv run alembic revision --autogenerate`)
- 직접 DDL 실행 금지 (migrations/ 경유 필수)

---

## Phase 진행 상태

| Phase | 내용 | 상태 |
|-------|------|------|
| **Phase 0** | SPEC 작성 | ✅ 완료 (15개 SPEC + 16개 UI SPEC) |
| **Phase 1** | 프로젝트 구조 + 하네스 기반 | ✅ 완료 (8/8 GREEN 테스트) |
| **Phase 2** | Agent Core (6-Layer) | ✅ 완료 (81/81 GREEN 테스트) |
| **Phase 3** | Network Generator | ✅ 완료 (19/19 GREEN 테스트) |
| **Phase 4** | Diffusion Engine | ✅ 완료 (78/78 GREEN 테스트) |
| **Phase 5** | LLM Integration | ✅ 완료 (92/92 GREEN 테스트) |
| **Phase 6** | Simulation Orchestrator + API | ✅ 완료 (127/127 GREEN 테스트) |
| **Phase 7** | Visualization (Frontend) | ✅ 완료 (tsc 0 errors, build OK) |
| **Phase A** | API→Frontend 37개 엔드포인트 연결 | ✅ 완료 |
| **Phase B** | 5개 기능 UI (Inject/Replay/MC/Engine/Compare) | ✅ 완료 |
| **Phase C** | Mock→Real API (5개 페이지) | ✅ 완료 |
| **Phase D** | Design tokens (70+색상) + Vitest (145 tests) | ✅ 완료 |
| **DB** | PostgreSQL persistence (fire-and-forget) | ✅ 완료 |
| **LLM** | Async Tier 3 cognition (evaluate_async) | ✅ 완료 |
| **VAL** | Validation pipeline VAL-01~08 (33 tests) | ✅ 완료 |
| **S** | Silent Stub 해소 (Network/LLM/Memory/Inject) | ✅ 완료 |
| **M** | Mock→Real 페이지 (GlobalMetrics/Opinions/Thread) | ✅ 완료 |
| **T** | 실패 테스트 41개 수정 + 4페이지 91개 추가 | ✅ 완료 |
| **F** | Campaign Setup + Project CRUD + EgoGraph Filter | ✅ 완료 |
| **N** | Run-All + GraphRAG + DB복원 + Platform + Lint 10.0 | ✅ 완료 |
| **H** | 09_HARNESS F18-F28 전체 구현 (+43 tests) | ✅ 완료 |
| **G** | SPEC 정합성 (메서드 rename + Sidebar + AgentInspector + AnalyticsPage) | ✅ 완료 |

> **총 테스트: 1,382+ GREEN** (Backend 861 + Frontend 521)
> - Backend: `uv run pytest tests/` → 861 passed, 2 skipped
> - Frontend: `npx vitest run` → 521 passed (27 test files)
> - ESLint: 0 errors, 0 warnings
> - TypeScript: 0 errors
> - Docker: 5 services (4 healthy, ollama unhealthy)
> - API: 55+ endpoints, 20 pages, 21 routes
> - 3D Graph: react-force-graph-3d (three.js WebGL)
> - Sidebar: 전역 레이아웃 (SimulationPage detail/LoginPage 제외)

### 성능 벤치마크 (2026-03-30)

| 측정 | 결과 | SPEC 목표 |
|------|------|----------|
| 1,000 agents × 1 step | **287ms avg** | <1,000ms (NF01) |
| 시뮬레이션 생성 (1,000 agents + network) | 1,362ms | — |
| Docker E2E (5 services healthy) | ✅ | — |

---

## 중요 원칙

- **⛔ SPEC 없이 구현하지 않는다** — `docs/spec/`에 SPEC이 없으면 SPEC부터 작성한다. 절대로 SPEC 없이 코드를 생성하지 않는다.
- **⛔ SPEC 변경 시 테스트 필수 갱신** — Backend/Frontend SPEC이 변경되면 해당 테스트 코드를 반드시 생성/갱신한다.
- **⛔ SPEC은 비공개 자산 — public commit 금지** — `docs/spec/`, `docs/init/`,
  `docs/BUSINESS_REPORT.md`, `docs/MARKETING_STRATEGY.md`, `docs/OASIS_vs_Prophet.md`는
  프로젝트의 IP/모트이므로 `.gitignore`에 등록되어 있다. 이 파일들은 로컬에서만 사용하고
  GitHub에 push하지 않는다. README.md 등 공개 문서를 작성할 때는 SPEC 문서나 그 내부
  내용을 인용/링크하지 말 것 — 누구든 SPEC만 보고 Prophet을 재현할 수 있기 때문이다.
- **⛔ pip 사용 금지** — `uv` 만 사용
- **SLM fallback 필수** — 모든 Tier 3 (Elite LLM) 기능은 Tier 1 (Mass SLM) fallback 보유
- **하네스 먼저** — 구현 전 하네스 픽스처/목 먼저 작성
- **PostgreSQL이 source of truth** — 인메모리 상태는 캐시일 뿐
- **SPEC 트레이서빌리티** — 모든 모듈 docstring에 SPEC 문서 참조를 명시한다

## Health Stack

- typecheck: cd frontend && npx tsc -b
- lint: cd frontend && npx eslint .
- test-fe: cd frontend && npx vitest run
- test-be: cd backend && uv run pytest tests/ -q
- deadcode: (not installed)
- shell: (not installed)

> **⛔ typecheck 주의 — `tsc --noEmit` 사용 금지**. 루트 `tsconfig.json` 이
> `"files": []` + references-only 구조라 `-b` 없이 실행하면 빈 프로젝트만
> 컴파일되어 **0 errors를 거짓 반환**한다 (no-op). 반드시 `tsc -b` 로 돌려서
> `tsconfig.app.json`, `tsconfig.node.json` 양쪽 project reference를 체크해야
> 한다. (2026-04-10 발견: 이 실수로 130개 타입 에러가 조용히 누적된 사건 있음)

## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health
