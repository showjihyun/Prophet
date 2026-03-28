# CLAUDE.md — Prophet (MCASP)

이 파일은 Claude Code가 이 프로젝트에서 작업할 때 항상 참조하는 지침서입니다.

---

## 프로젝트 개요

**Prophet = MCASP (Multi-Community Agent Simulation Platform)**

AI 기반 가상 사회에서 마케팅 캠페인/정책/메시지의 확산을 사전 시뮬레이션하는 플랫폼.
LLM + GraphRAG + Viral Diffusion 을 결합한 Agent 기반 사회 시뮬레이션 엔진.

- SPEC 문서: `docs/spec/`
- 원본 기획서: `docs/init/` (읽기 전용 참조)
- Master SPEC: `docs/spec/MASTER_SPEC.md`

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

### SPEC 파일 매핑

| SPEC 문서 | 커버 범위 | Backend 경로 | Frontend 경로 |
|-----------|----------|-------------|--------------|
| `00_ARCHITECTURE.md` | 시스템 아키텍처 | `backend/app/` | `frontend/src/` |
| `01_AGENT_SPEC.md` | 6-Layer Agent Engine | `backend/app/engine/agent/` | — |
| `02_NETWORK_SPEC.md` | Network Generator | `backend/app/engine/network/` | — |
| `03_DIFFUSION_SPEC.md` | Diffusion Engine | `backend/app/engine/diffusion/` | — |
| `04_SIMULATION_SPEC.md` | Simulation Orchestrator | `backend/app/engine/simulation/` | — |
| `05_LLM_SPEC.md` | LLM Adapter | `backend/app/llm/` | — |
| `06_API_SPEC.md` | REST/WebSocket API | `backend/app/api/` | `frontend/src/api/` |
| `07_FRONTEND_SPEC.md` | UI Components | — | `frontend/src/` |
| `08_DB_SPEC.md` | DB Schema/Migrations | `backend/app/models/` | — |
| `09_HARNESS_SPEC.md` | Test Harness (F18-F30) | `backend/harness/` | — |

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
6. LLM 의존 기능은 반드시 Rule Engine fallback을 가져야 한다.

---

## 기술 스택

### 백엔드
- **Python 3.12+** / **FastAPI** (async)
- **SQLAlchemy 2.0** (async ORM) + **Alembic** (마이그레이션)
- **PostgreSQL 16** + **pgvector** (벡터 메모리)
- **Valkey** (LLM 캐시, 세션)
- **NetworkX** (소셜 그래프 런타임)
- **Celery** (Monte Carlo 백그라운드 작업)

### LLM
- **Ollama** (로컬, 기본값) — `ollama-python`
- **Claude API** — `anthropic` SDK
- **OpenAI API** — `openai` SDK

### 프론트엔드
- **React 18** + **TypeScript** + **Vite**
- **Cytoscape.js** (GraphRAG 시각화)
- **Recharts** (Timeline/Metric 차트)
- **Zustand** (상태 관리)
- **TanStack Query** (서버 상태)
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
├── docs/
│   ├── init/          ← 원본 기획서 (읽기 전용)
│   └── spec/          ← SPEC 문서 (항상 먼저 확인)
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

### DB
- 모든 마이그레이션은 Alembic으로 (`uv run alembic revision --autogenerate`)
- 직접 DDL 실행 금지 (migrations/ 경유 필수)

---

## Phase 진행 상태

| Phase | 내용 | 상태 |
|-------|------|------|
| **Phase 0** | SPEC 작성 | ✅ 완료 |
| **Phase 1** | 프로젝트 구조 + 하네스 기반 | 대기 |
| **Phase 2** | Agent Core | 대기 |
| **Phase 3** | Network Generator | 대기 |
| **Phase 4** | Diffusion Engine | 대기 |
| **Phase 5** | LLM Integration | 대기 |
| **Phase 6** | Simulation Orchestrator | 대기 |
| **Phase 7** | Visualization (Frontend) | 대기 |

---

## 중요 원칙

- **⛔ SPEC 없이 구현하지 않는다** — `docs/spec/`에 SPEC이 없으면 SPEC부터 작성한다. 절대로 SPEC 없이 코드를 생성하지 않는다.
- **⛔ SPEC 변경 시 테스트 필수 갱신** — Backend/Frontend SPEC이 변경되면 해당 테스트 코드를 반드시 생성/갱신한다.
- **⛔ pip 사용 금지** — `uv` 만 사용
- **LLM fallback 필수** — 모든 Tier 3 기능은 Tier 1/2 fallback 보유
- **하네스 먼저** — 구현 전 하네스 픽스처/목 먼저 작성
- **PostgreSQL이 source of truth** — 인메모리 상태는 캐시일 뿐
- **SPEC 트레이서빌리티** — 모든 모듈 docstring에 SPEC 문서 참조를 명시한다
