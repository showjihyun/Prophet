# HARNESS.md — Harness Engineering Context Strategy

**Prophet 프로젝트의 AI 에이전트 컨텍스트 전략 프레임워크**

> AI 에이전트가 올바르게 작동할 수 있는 맥락(정보+환경)을 도구화하여 제공하는 기술.
> 에이전트가 코드를 한 줄도 직접 쓰지 않더라도 대규모 시스템을 자율적으로 구축할 수 있도록,
> 그리고 그 결과가 일관되게 고품질이도록 보장하는 구조적 원칙을 정의한다.

---

## 문서 관계

```
HARNESS.md (왜? 원칙)            ← 이 문서
    │
    ├── CLAUDE.md (무엇? 운영 규칙)
    │     "SPEC 없이 구현하지 않는다" → 왜? → 계약 기반 컨텍스트 원칙 (§2)
    │
    ├── AGENTS.md (누가? 역할 분배)
    │     "backend-agent는 Sonnet" → 왜? → 인지 자원 배분 원칙 (§4)
    │
    ├── docs/spec/09_HARNESS_SPEC.md (어떻게? 테스트 도구 구현)
    │     "MockLLM, Sandbox, Replay" → 왜? → 검증 루프 원칙 (§3)
    │
    └── docs/spec/15_DEV_WORKFLOW_SPEC.md (어떻게? 모델 선택 구현)
          "Think with Opus, Code with Sonnet" → 왜? → 인지 자원 배분 원칙 (§4)
```

---

## §1. Context Hierarchy — 컨텍스트 계층 구조

에이전트에게 제공되는 컨텍스트는 단일 프롬프트가 아니라 **5개 계층**으로 구성된다.
상위 계층일수록 안정적이고 오래 지속되며, 하위 계층일수록 휘발성이 높다.

```
┌─────────────────────────────────────────────────────────┐
│  L5: Session Memory                                      │  영구 (cross-session)
│  ┌─────────────────────────────────────────────────────┐│
│  │  L4: Project Identity                               ││  대화 전체 (always loaded)
│  │  ┌─────────────────────────────────────────────────┐││
│  │  │  L3: SPEC Contract                              │││  작업 단위 (on-demand)
│  │  │  ┌─────────────────────────────────────────────┐│││
│  │  │  │  L2: Agent Role                             ││││  에이전트 수명
│  │  │  │  ┌─────────────────────────────────────────┐│││││
│  │  │  │  │  L1: Task Prompt                        ││││││  1회 실행
│  │  │  │  └─────────────────────────────────────────┘│││││
│  │  │  └─────────────────────────────────────────────┘││││
│  │  └─────────────────────────────────────────────────┘│││
│  └─────────────────────────────────────────────────────┘││
└─────────────────────────────────────────────────────────┘│
```

### 각 계층의 역할

| Layer | 파일/메커니즘 | 수명 | 역할 | Prophet 적용 |
|-------|-------------|------|------|-------------|
| **L5** | `MEMORY.md` + 개별 `.md` | 영구 | 사용자 프로필, 프로젝트 전략, 과거 피드백 | 사용자 역할, Prophet 하이브리드 전략 기억 |
| **L4** | `CLAUDE.md` | 대화 전체 | 프로젝트 규칙, 기술 스택, Phase 상태, 절대 규칙 | SPEC-GATE, uv 전용, Phase 진행 테이블 |
| **L3** | `docs/spec/*.md` | 작업 단위 | 함수 시그니처, 입출력 타입, Acceptance Criteria | 15개 SPEC + 16개 UI SPEC |
| **L2** | `AGENTS.md` + Agent prompt | 에이전트 수명 | 담당 모듈, 사용 모델, 코딩 규칙 | backend-agent=Sonnet, plan-agent=Opus |
| **L1** | Agent tool 호출 시 prompt | 1회 실행 | 구체적 작업 지시, 파일 경로, 변경 내용 | "Implement InjectEventModal per SPEC..." |

### 설계 원칙

**1. 상위 계층은 하위 계층을 제약한다.**
- L4(CLAUDE.md)의 "SPEC 없이 구현 금지"가 L1(Task Prompt)의 모든 구현 작업을 제약
- L2(Agent Role)의 "Sonnet으로 구현"이 L1의 모델 선택을 제약

**2. 하위 계층은 상위 계층을 참조한다.**
- L1(Task)에서 L3(SPEC)을 읽어야 구현 가능
- L2(Agent Role)에서 L4(CLAUDE.md)의 규칙을 따라야 작업 허용

**3. 계층 간 토큰 예산을 관리한다.**
- L4(CLAUDE.md)는 매번 로드되므로 간결해야 함 (200줄 이내 권장)
- L3(SPEC)은 필요할 때만 읽으므로 상세할 수 있음
- L5(Memory)는 인덱스만 로드하고 본문은 on-demand

---

## §2. Contract-First Context — 계약 기반 컨텍스트

> **원칙: 컨텍스트의 최소 단위는 자연어가 아니라 인터페이스 계약(Contract)이다.**

### 왜 계약인가

자연어 지시는 모호하다. 에이전트가 1,000줄의 코드를 생성할 때, "에이전트 인지를 처리하는 함수를 만들어줘"라는 지시만으로는 입출력 타입, 제약조건, 에러 처리를 보장할 수 없다.

반면 계약은 **검증 가능한 형태**로 기대를 명시한다:

```
❌ 약한 컨텍스트 (자연어)
"에이전트의 인지를 처리하는 함수를 만들어줘"

✅ 강한 컨텍스트 (계약)
SPEC: 01_AGENT_SPEC.md#layer-3-cognition
Input:  CognitionInput(perception: PerceptionResult, memories: list[MemoryRecord])
Output: CognitionResult(reasoning: str, action_intent: ActionIntent, confidence: float)
Constraint: tier=1 → rule-based, tier=3 → LLM call with fallback
```

### Prophet의 계약 체계

```
SPEC 문서 (계약 정의)
    │
    ├── 함수 시그니처: 이름, 파라미터, 반환 타입
    ├── 데이터 타입: dataclass / Pydantic / TypeScript interface
    ├── 제약조건: 범위, 불변조건, 선행조건
    ├── 에러 명세: 어떤 예외를 어떤 상황에서 발생시키는가
    └── Acceptance Criteria: 계약 준수를 검증하는 테스트 기준
```

### SPEC-GATE = 계약 강제 메커니즘

CLAUDE.md의 SPEC-GATE 규칙은 이 원칙의 운영적 구현이다:

```
구현 요청 수신
      │
      ▼
  SPEC이 존재하는가? ── No ──→ SPEC 먼저 작성 (계약 생성)
      │
      Yes
      ▼
  SPEC에 시그니처/타입이 정의되었는가? ── No ──→ SPEC 갱신 (계약 보강)
      │
      Yes
      ▼
  테스트 코드 생성 (계약 검증기 생성)
      │
      ▼
  코드 구현 (계약 이행)
```

### 트레이서빌리티 = 계약 추적

모든 코드에 SPEC 참조를 명시하는 규칙은 **계약과 구현의 연결을 유지**하기 위한 것이다:

```python
class PerceptionLayer:
    """Agent Perception Layer.
    SPEC: docs/spec/01_AGENT_SPEC.md#layer-1-perception
    """
```

이것은 단순 주석이 아니라, "이 코드가 어떤 계약을 이행하는지" 추적하는 메커니즘이다.
계약이 변경되면 이 참조를 통해 영향받는 코드를 찾을 수 있다.

---

## §3. Verification Loop — 검증 루프

> **원칙: 컨텍스트는 일방적 제공이 아니라, 피드백 루프로 작동한다.**

### 단방향 vs 양방향

```
❌ 단방향 (컨텍스트 제공만)
SPEC ──→ 에이전트 ──→ 코드 (맞는지 모름)

✅ 양방향 (컨텍스트 + 검증)
SPEC ──→ 테스트(Red) ──→ 에이전트 ──→ 코드 ──→ 테스트(Green?) ──→ 완료 or 재시도
              ↑                                        │
              └──────────── FAIL 시 피드백 ──────────────┘
```

### Red-Green-Refactor = 검증 루프의 구현

Prophet의 하네스 우선 개발 흐름:

```
1. SPEC 확인/작성              ← 계약 정의
2. 테스트 코드 생성 (SPEC 기반) ← 검증기 생성
3. 테스트 실행 → 전부 FAIL (Red) ← 검증기가 작동함을 확인
4. 코드 구현                   ← 에이전트가 계약 이행
5. 테스트 실행 → 전부 PASS (Green) ← 이행 완료 확인
6. 리팩토링 (테스트 유지)       ← 계약 불변 하에 개선
```

### 검증 도구 = 09_HARNESS_SPEC의 구현

| 검증 도구 | 역할 | 09_HARNESS_SPEC 참조 |
|-----------|------|---------------------|
| `pytest` | 백엔드 계약 검증 | F18 Unit Test Hooks |
| `MockLLMAdapter` | 외부 의존성 없이 검증 | F19 Mock Environment |
| `SimulationSandbox` | 격리된 통합 검증 | F24 Simulation Sandbox |
| `vitest` | 프론트엔드 계약 검증 | — (07_FRONTEND_SPEC §9.5) |
| `playwright` | E2E 사용자 시나리오 검증 | — (07_FRONTEND_SPEC §9.5) |
| `tsc --noEmit` | 타입 계약 검증 | — (TypeScript strict mode) |

### 에이전트의 자가 수정 능력

검증 루프의 핵심 가치: 에이전트가 "완료"를 스스로 판단할 수 있게 된다.

```
에이전트: 코드 작성 완료
    ↓
에이전트: uv run pytest tests/ -x -q 실행
    ↓
하네스: 586 passed, 0 failed
    ↓
에이전트: "Phase 완료" 판단 가능    ← 자연어 판단이 아닌 객관적 근거
```

만약 실패하면:

```
하네스: 3 failed — test_perception_returns_ranked_feed
    ↓
에이전트: 에러 메시지를 읽고 코드 수정
    ↓
에이전트: 재실행 → passed
    ↓
에이전트: 완료
```

이 루프가 없으면 에이전트는 "아마 맞을 것이다"라고 추정할 수밖에 없다.
루프가 있으면 "맞다"를 증명할 수 있다.

---

## §4. Cognitive Resource Allocation — 인지 자원 배분

> **원칙: 컨텍스트 전략은 어떤 작업에 어떤 수준의 인지를 투입할지 결정하는 것을 포함한다.**

### Prophet의 3-Tier 대응

Prophet 시뮬레이션은 에이전트 인지에 3-Tier를 적용한다.
개발 워크플로우에도 동일한 원칙을 적용한다:

| Prophet 시뮬레이션 | 개발 워크플로우 | 비율 |
|-------------------|---------------|------|
| **Tier 1: Mass SLM** (80%) | **Sonnet 4.6**: 코드 구현, 테스트, 리팩토링 | ~80% |
| **Tier 2: Heuristic** (10%) | **직접 도구**: Glob, Grep, Read (모델 불필요) | ~10% |
| **Tier 3: Elite LLM** (10%) | **Opus 4.6**: SPEC, Plan, 아키텍처, 감사 | ~10% |

### 왜 분리하는가

모든 작업에 최고 모델을 사용하면:
- **비용**: 67% 더 비쌈 (Phase B 기준 $0.72 vs $0.24)
- **속도**: 2.7배 더 느림 (Opus 45s vs Sonnet 15s per component)
- **품질**: 향상 없음 (SPEC이 있으면 Sonnet도 정확히 구현)

**핵심 통찰**: SPEC이 충분히 상세하면, 구현 에이전트에게 깊은 추론은 불필요하다.
깊은 추론은 SPEC을 **작성**할 때 필요하지, SPEC을 **따를** 때는 불필요하다.

### Decision Flowchart

```
작업 요청 수신
      │
      ▼
  새 SPEC/아키텍처 판단 필요? ── Yes ──→ Opus (Architect)
      │ No
      ▼
  다중 모듈 복잡 디버깅? ── Yes ──→ Opus (Architect)
      │ No
      ▼
  SPEC이 이미 존재하는 구현? ── Yes ──→ Sonnet (Builder)
      │ No
      ▼
  파일 검색/읽기? ── Yes ──→ 직접 도구 (Glob/Grep/Read)
      │ No
      ▼
  Opus (안전한 기본값)
```

상세 구현: `docs/spec/15_DEV_WORKFLOW_SPEC.md`

---

## §5. Parallel Decomposition — 병렬 분할

> **원칙: 대규모 작업은 SPEC 경계에서 분할하고, 인터페이스 계약으로 연결한다.**

### SPEC = 분할 경계

```
01_AGENT_SPEC ──── 독립 ──── 02_NETWORK_SPEC
       │                            │
       └──── 둘 다 필요 ────→ 03_DIFFUSION_SPEC
                                    │
                              04_SIMULATION_SPEC (전부 필요)
```

이 의존성 그래프가 자연스럽게 병렬 작업 단위를 결정한다:

```
Phase 2 (Agent) ──┐
                  ├── 병렬 실행 가능 (서로 독립)
Phase 3 (Network) ┘
                  ├── Phase 4 (Diffusion) ← 2+3 완료 후
                  └── Phase 5 (LLM) ──── 병렬 ──── Phase 7 (Frontend)
                                    └── Phase 6 (Orchestrator) ← 2+3+4+5 완료 후
```

### 인터페이스 계약 = 연결 고리

병렬로 작업하는 에이전트들은 서로의 내부 구현을 모른다.
오직 **SPEC에 정의된 인터페이스 계약**만이 연결 고리다:

```
backend-agent (Agent Core)         backend-agent (Network Generator)
  │                                  │
  ├── AgentState (output)            ├── SocialNetwork (output)
  └── AgentTickResult (output)       └── NetworkMetrics (output)
           │                                  │
           └────── 둘 다 ──────→ DiffusionEngine (consumer)
                                SPEC: 03_DIFFUSION_SPEC.md
                                Input: list[AgentState] + SocialNetwork
```

에이전트 A가 `AgentState`의 필드를 변경하면?
→ SPEC을 먼저 수정 → 소비자 에이전트가 SPEC 변경을 인지 → 자기 코드 갱신

### AGENTS.md = 분할 매트릭스의 운영 구현

`AGENTS.md`의 Phase별 병렬 작업 매트릭스는 이 원칙의 구체적 실행 계획이다.

---

## §6. Context Decay Prevention — 컨텍스트 부패 방지

> **원칙: 컨텍스트는 시간이 지나면 부패한다. Source of truth와 동기화 메커니즘이 필수다.**

### 부패 유형과 방지

| 부패 유형 | 증상 | 원인 | 방지 메커니즘 |
|-----------|------|------|-------------|
| **SPEC-Code 불일치** | 코드가 SPEC과 다르게 동작 | 코드 변경 후 SPEC 미갱신 | SPEC-GATE: SPEC 먼저 수정 → 코드 변경 |
| **Test-Code 괴리** | 테스트 통과하지만 실제 동작 다름 | 구현 변경 후 테스트 미갱신 | SPEC 변경 → 테스트 자동 갱신 규칙 |
| **Phase 상태 오류** | 완료된 줄 알았는데 미완료 | 진행 상황 주관적 판단 | CLAUDE.md Phase 테이블에 테스트 수 명시 |
| **메모리 노후화** | 없는 함수/파일 추천 | 리팩토링 후 메모리 미갱신 | 메모리 사용 전 현재 코드와 교차 검증 |
| **의존성 드리프트** | 모듈 간 인터페이스 불일치 | 한쪽만 변경 | API 계약 테스트 (양쪽 모두 검증) |

### Source of Truth 체계

```
SPEC 문서 ← Source of Truth (인간이 관리)
    │
    ├──→ 테스트 코드 ← Contract Verifier (SPEC에서 파생)
    │         │
    │         └──→ 프로덕션 코드 ← Derived (테스트를 통과해야 존재 의미)
    │
    ├──→ CLAUDE.md Phase 테이블 ← Status (테스트 수로 검증 가능)
    │
    └──→ Memory ← Point-in-time Snapshot (검증 후 사용)
```

### 동기화 규칙

1. **SPEC 변경 → 테스트 먼저 갱신 → 코드 갱신**
   - 순서 위반 시 SPEC-Code 불일치 발생
   - CLAUDE.md의 "SPEC 변경 시 테스트 자동 생성 규칙" 참조

2. **Phase 완료 = 테스트 통과 수로 정의**
   - "Phase 2 완료 = 81/81 GREEN" (주관적 판단 배제)
   - CLAUDE.md의 Phase 진행 테이블이 이 역할 수행

3. **Memory 사용 전 현재 상태 확인**
   - "Memory에 X 함수가 있다고 기록됨" → Grep으로 존재 확인 후 사용
   - Memory는 "과거에 이랬다"일 뿐, "지금도 이렇다"는 아님

4. **API 계약 양방향 테스트**
   - Backend: `test_06_api_{endpoint}.py` (서버 측 계약 검증)
   - Frontend: `apiClient.test.ts` (클라이언트 측 계약 검증)
   - 한쪽만 테스트하면 다른 쪽의 드리프트를 잡을 수 없음

---

## 요약: 6가지 원칙 한 눈에

```
┌─────────────────────────────────────────────────────────────────┐
│                    Harness Engineering                           │
│                    Context Strategy                              │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ §1       │  │ §2       │  │ §3       │                      │
│  │ Context  │  │ Contract │  │ Verify   │                      │
│  │ Hierarchy│  │ First    │  │ Loop     │                      │
│  │          │  │          │  │          │                      │
│  │ 5계층    │→│ 계약이    │→│ 테스트가  │                      │
│  │ 구조     │  │ 최소단위 │  │ 검증     │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
│       ↕              ↕              ↕                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
│  │ §4       │  │ §5       │  │ §6       │                      │
│  │ Cognitive│  │ Parallel │  │ Decay    │                      │
│  │ Alloc    │  │ Decomp   │  │ Prevent  │                      │
│  │          │  │          │  │          │                      │
│  │ Opus/    │  │ SPEC     │  │ SoT      │                      │
│  │ Sonnet   │  │ 경계분할 │  │ 동기화   │                      │
│  └──────────┘  └──────────┘  └──────────┘                      │
│                                                                 │
│  이 6가지가 결합되어:                                             │
│  "AI가 자율적으로 100만 줄을 만들되, 일관되게 고품질"을 달성한다.   │
└─────────────────────────────────────────────────────────────────┘
```

| # | 원칙 | 한 줄 요약 | Prophet 구현체 |
|---|------|-----------|---------------|
| §1 | Context Hierarchy | 컨텍스트는 5계층 구조 | MEMORY → CLAUDE.md → SPEC → AGENTS.md → Task |
| §2 | Contract-First | 최소 단위는 인터페이스 계약 | SPEC-GATE + 트레이서빌리티 |
| §3 | Verification Loop | 테스트가 완료를 증명 | Red-Green-Refactor + 09_HARNESS_SPEC |
| §4 | Cognitive Allocation | 작업별 인지 수준 배분 | Think with Opus, Code with Sonnet |
| §5 | Parallel Decomposition | SPEC 경계에서 분할 | AGENTS.md Phase별 매트릭스 |
| §6 | Decay Prevention | Source of truth 동기화 | SPEC 변경 → 테스트 → 코드 순서 |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-04-02 | Initial draft — 6 context strategy dimensions |
