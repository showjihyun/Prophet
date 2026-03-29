# 15_DEV_WORKFLOW_SPEC — Development Workflow & Model Selection Strategy

**Version:** 0.1.0 | **Status:** DRAFT | **Date:** 2026-03-29

---

## 1. Overview

Prophet 개발에 사용하는 AI 모델 역할 분리 전략을 정의한다.
프로젝트의 3-Tier LLM 전략 (Mass SLM → Heuristic → Elite LLM)을 **개발 워크플로우 자체에도 적용**하여 비용 대비 품질을 최적화한다.

### 핵심 원칙: "Think with Opus, Code with Sonnet"

```
┌───────────────────────────────────────────────────────────┐
│              Development Model Selection                   │
│                                                           │
│   Opus 4.6 (Architect)         Sonnet 4.6 (Builder)      │
│   ┌─────────────────┐         ┌─────────────────┐        │
│   │ SPEC 작성/리뷰   │         │ 코드 구현        │        │
│   │ 아키텍처 설계     │   →     │ 컴포넌트 생성     │        │
│   │ Plan 수립/리뷰   │         │ 테스트 작성       │        │
│   │ 복잡한 디버깅     │         │ 리팩토링         │        │
│   │ 트레이드오프 분석  │         │ 반복적 구현       │        │
│   └─────────────────┘         └─────────────────┘        │
│         ~20% 시간                  ~80% 시간              │
└───────────────────────────────────────────────────────────┘
```

### Rationale

| 요인 | Opus 4.6 | Sonnet 4.6 |
|------|----------|------------|
| **추론 깊이** | 깊은 사고, 복잡한 의존성 파악 | 패턴 기반 빠른 생성 |
| **출력 속도** | 느림 (정밀 분석) | 빠름 (높은 처리량) |
| **비용** | 높음 | 낮음 |
| **컨텍스트 활용** | 전체 아키텍처 조망 | 로컬 스코프 집중 |
| **최적 작업** | 설계, 분석, 판단 | 구현, 생성, 변환 |

---

## 2. Model Selection Matrix

### 2.1 Opus 4.6 — Architect Mode (계획/분석/판단)

**사용 시점:**

| 작업 유형 | 설명 | 예시 |
|-----------|------|------|
| **SPEC 작성** | 새 SPEC 문서 초안 작성 | `15_DEV_WORKFLOW_SPEC.md` 작성 |
| **SPEC 리뷰** | 기존 SPEC 간 정합성 검증 | 01_AGENT_SPEC ↔ 04_SIMULATION_SPEC 계약 검증 |
| **아키텍처 설계** | 모듈 간 의존성, 데이터 흐름 설계 | CommunityOrchestrator 3-Phase 설계 |
| **Plan 수립** | Phase별 작업 분해, 의존성 정렬 | Phase B 작업 리스트 도출 |
| **Plan 리뷰** | CEO/Eng/Design 리뷰 실행 | `/plan-eng-review`, `/plan-ceo-review` |
| **복잡한 디버깅** | 다중 모듈 걸친 근본 원인 분석 | WebSocket + Orchestrator + Agent 연쇄 버그 |
| **트레이드오프 분석** | 기술 선택지 비교 | Neo4j vs pgvector, Celery vs asyncio |
| **OASIS 비교 분석** | 외부 시스템 대비 gap 분석 | `docs/OASIS_vs_Prophet.md` 작성 |
| **코드 탐색/감사** | 전체 코드베이스 정합성 검토 | 전체 SPEC 대비 구현 완성도 감사 |

**Claude Code 적용:**
```
# Plan Mode 진입 시 자동으로 Opus 사용 (기본)
/plan

# Explore agent — Opus로 깊이 있는 탐색
Agent(subagent_type="Explore", model="opus")

# Plan agent — 아키텍처 설계
Agent(subagent_type="Plan", model="opus")
```

### 2.2 Sonnet 4.6 — Builder Mode (구현/생성/변환)

**사용 시점:**

| 작업 유형 | 설명 | 예시 |
|-----------|------|------|
| **컴포넌트 구현** | SPEC 기반 코드 작성 | `InjectEventModal.tsx` 생성 |
| **테스트 작성** | SPEC 계약 기반 테스트 코드 | `test_06_api_inject_event.py` |
| **리팩토링** | 패턴 기반 코드 변환 | CSS 변수 전환, 하드코딩 제거 |
| **반복 구현** | 유사 패턴의 다수 파일 생성 | 5개 modal 컴포넌트 연속 생성 |
| **보일러플레이트** | 라우트, 스키마, 모델 생성 | Pydantic 모델, API 엔드포인트 |
| **버그 수정** | 단일 모듈 내 명확한 수정 | TypeError, import 오류 |
| **문서 갱신** | 기존 패턴 따르는 문서 업데이트 | README, CHANGELOG |
| **코드 리뷰** | 스타일/패턴 준수 확인 | lint, type check, convention |

**Claude Code 적용:**
```
# 코드 구현 에이전트 — Sonnet으로 빠르게
Agent(subagent_type="general-purpose", model="sonnet",
      prompt="Implement InjectEventModal per SPEC...")

# 코드 리뷰 에이전트 — Sonnet으로 효율적
Agent(subagent_type="feature-dev:code-reviewer", model="sonnet")

# 코드 정리 — Sonnet으로
Agent(subagent_type="code-simplifier:code-simplifier", model="sonnet")
```

### 2.3 Decision Flowchart

```
작업 요청 수신
      │
      ▼
  ┌─────────────────┐
  │ 새 SPEC 작성이    │──── Yes ──→ Opus (Architect)
  │ 필요한가?         │
  └────────┬────────┘
           │ No
           ▼
  ┌─────────────────┐
  │ 아키텍처/설계     │──── Yes ──→ Opus (Architect)
  │ 판단이 필요한가?   │
  └────────┬────────┘
           │ No
           ▼
  ┌─────────────────┐
  │ 다중 모듈 걸친    │──── Yes ──→ Opus (Architect)
  │ 복잡한 디버깅?    │
  └────────┬────────┘
           │ No
           ▼
  ┌─────────────────┐
  │ SPEC이 이미      │──── Yes ──→ Sonnet (Builder)
  │ 존재하는 구현?    │
  └────────┬────────┘
           │ No
           ▼
  ┌─────────────────┐
  │ 패턴이 확립된    │──── Yes ──→ Sonnet (Builder)
  │ 반복 작업?       │
  └────────┬────────┘
           │ No
           ▼
      Opus (default for ambiguous tasks)
```

---

## 3. Workflow Integration

### 3.1 SPEC-GATE + Model Selection

기존 SPEC-GATE 규칙과 모델 선택을 통합한 워크플로우:

```
1. [Opus]  SPEC 확인/작성
     ↓
2. [Opus]  Plan 수립 (작업 분해, 의존성 정렬)
     ↓
3. [Opus]  Plan 리뷰 (Eng/CEO/Design 리뷰)
     ↓
4. [Sonnet] 테스트 코드 생성 (SPEC 계약 기반, Red)
     ↓
5. [Sonnet] 코드 구현 (테스트 통과 목표, Green)
     ↓
6. [Sonnet] 리팩토링 (코드 정리, Refactor)
     ↓
7. [Opus]  코드 감사 (아키텍처 정합성 최종 확인)
     ↓
8. [Sonnet] 코드 리뷰 (스타일/패턴 준수)
     ↓
Phase 완료
```

### 3.2 Parallel Agent Model Assignment

AGENTS.md의 에이전트 역할과 모델 매핑:

| Agent Role | Primary Model | Fallback | 근거 |
|------------|---------------|----------|------|
| **Plan agent** | Opus | — | 아키텍처 설계, 전체 조망 필요 |
| **Explore agent** | Opus | Sonnet (quick 탐색) | 깊은 분석 시 Opus, 단순 파일 찾기 시 Sonnet |
| **backend-agent** (구현) | Sonnet | Opus (복잡한 로직) | 대부분 SPEC 기반 코드 생성 |
| **frontend-agent** (구현) | Sonnet | — | 컴포넌트/페이지 생성 |
| **harness-agent** (테스트) | Sonnet | — | 테스트 코드 생성 |
| **db-agent** (마이그레이션) | Sonnet | Opus (스키마 설계) | 마이그레이션 생성 |
| **code-reviewer** | Sonnet | — | 패턴 기반 리뷰 |
| **code-simplifier** | Sonnet | — | 코드 정리 |

### 3.3 CLAUDE.md 적용 규칙

```markdown
## Model Selection Rule

- **Planning/Analysis/SPEC**: Opus 4.6 사용
  - Plan mode, Explore (thorough), SPEC 작성, 아키텍처 설계, 감사
- **Implementation/Testing**: Sonnet 4.6 사용
  - 코드 구현, 테스트 작성, 리팩토링, 코드 리뷰, 보일러플레이트
- **Ambiguous**: Opus 4.6 (안전한 기본값)
- Agent tool 호출 시 model 파라미터를 명시한다
```

---

## 4. Cost-Benefit Analysis

### 4.1 예상 비용 절감

Prophet Phase B 기준 (5개 기능 UI 구현):

| 단계 | 모델 | 예상 토큰 | 단일 모델 비용 | 분리 전략 비용 |
|------|------|----------|--------------|--------------|
| SPEC 리뷰 | Opus | ~5K | $0.075 | $0.075 |
| Plan 수립 | Opus | ~3K | $0.045 | $0.045 |
| 코드 구현 (5개 파일) | **Sonnet** | ~25K | $0.375 (Opus) | $0.075 (Sonnet) |
| 테스트 작성 | **Sonnet** | ~10K | $0.150 (Opus) | $0.030 (Sonnet) |
| 코드 리뷰 | **Sonnet** | ~5K | $0.075 (Opus) | $0.015 (Sonnet) |
| **합계** | | ~48K | **$0.720** | **$0.240** |

**예상 절감: ~67%** (구현/테스트 단계에서 대부분 절감)

### 4.2 품질 트레이드오프

| 관점 | 리스크 | 완화 전략 |
|------|--------|----------|
| Sonnet이 아키텍처 의도를 놓칠 수 있음 | 중 | SPEC에 인터페이스 계약을 상세히 명시 |
| 모델 전환 시 컨텍스트 손실 | 낮 | Agent tool이 프롬프트에 필요 컨텍스트 전달 |
| 복잡한 구현에서 Sonnet 한계 | 낮 | Decision Flowchart로 Opus fallback |
| 일관성 (모델 간 스타일 차이) | 낮 | CLAUDE.md 코딩 규칙이 스타일 통일 |

### 4.3 속도 개선

| 단계 | Opus 소요 | Sonnet 소요 | 속도 향상 |
|------|----------|------------|----------|
| 컴포넌트 구현 (1개) | ~45s | ~15s | 3x |
| 테스트 파일 생성 | ~30s | ~10s | 3x |
| 리팩토링 | ~20s | ~8s | 2.5x |
| **5개 구현 총합** | ~8min | ~3min | **2.7x** |

---

## 5. Implementation Guide

### 5.1 Claude Code 설정

CLAUDE.md에 다음 규칙을 추가:

```markdown
## Development Model Strategy

### Model Selection
- **Opus 4.6**: SPEC 작성, Plan, 아키텍처 설계, 복잡한 디버깅, 감사
- **Sonnet 4.6**: 코드 구현, 테스트, 리팩토링, 코드 리뷰, 보일러플레이트
- Agent tool 호출 시 `model` 파라미터를 작업 유형에 맞게 명시

### Agent Model Parameter Examples
```python
# Planning — Opus
Agent(subagent_type="Plan", model="opus", prompt="...")

# Code implementation — Sonnet
Agent(subagent_type="general-purpose", model="sonnet", prompt="Implement X per SPEC...")

# Deep exploration — Opus
Agent(subagent_type="Explore", model="opus", prompt="Analyze architecture of...")

# Quick file search — Sonnet (or direct Glob/Grep)
Agent(subagent_type="Explore", model="sonnet", prompt="Find files matching...")

# Code review — Sonnet
Agent(subagent_type="feature-dev:code-reviewer", model="sonnet", prompt="Review...")
```
```

### 5.2 AGENTS.md 갱신 사항

에이전트 역할 분류 테이블에 `Model` 컬럼 추가:

```markdown
| Agent Role | Model | 작업 유형 |
|------------|-------|----------|
| backend-agent (구현) | Sonnet | 코드 작성, API 라우트 |
| frontend-agent (구현) | Sonnet | 컴포넌트, 페이지 |
| harness-agent (테스트) | Sonnet | 테스트 코드 |
| db-agent (마이그레이션) | Sonnet | 마이그레이션 생성 |
| plan-agent (설계) | Opus | SPEC, Plan, 아키텍처 |
| audit-agent (감사) | Opus | 정합성 검증 |
```

---

## 6. Exceptions & Override Rules

### 6.1 Sonnet → Opus Escalation

다음 상황에서는 Sonnet 작업 중이라도 Opus로 전환:

1. **구현 중 SPEC 모호성 발견** — SPEC 해석이 필요하면 Opus로 전환
2. **다중 모듈 연쇄 버그** — 단일 모듈 수정으로 해결 안 되면 Opus
3. **성능 최적화 설계** — 알고리즘 선택/자료구조 설계 판단 필요 시
4. **보안 관련 코드** — 인증, 권한, 입력 검증 로직은 Opus로 리뷰

### 6.2 Opus → Sonnet Delegation

Opus 작업 중 다음은 Sonnet에 위임:

1. **Plan 확정 후 구현** — Plan이 승인되면 구현은 Sonnet으로
2. **SPEC 작성 후 테스트 생성** — SPEC 완성되면 테스트 코드는 Sonnet으로
3. **감사 후 수정** — 감사로 발견된 수정 사항은 Sonnet으로 적용

### 6.3 User Override

사용자는 언제든 모델 선택을 오버라이드할 수 있다:
- `"Opus로 구현해줘"` → 모든 구현을 Opus로
- `"Sonnet으로 분석해줘"` → 분석도 Sonnet으로
- `"빠르게 해줘"` → 전부 Sonnet
- `"꼼꼼하게 해줘"` → 전부 Opus

---

## 7. Acceptance Criteria

| ID | Criteria | 검증 방법 |
|----|----------|----------|
| DEV-01 | Plan/SPEC 작업에 Opus 사용 | Agent tool 호출 시 `model="opus"` 확인 |
| DEV-02 | 코드 구현에 Sonnet 사용 | Agent tool 호출 시 `model="sonnet"` 확인 |
| DEV-03 | Decision Flowchart 준수 | 모호한 작업은 Opus로 기본 처리 |
| DEV-04 | Escalation 규칙 준수 | SPEC 모호성/다중 모듈 버그 시 Opus 전환 |
| DEV-05 | User Override 지원 | 사용자 명시적 모델 지정 시 즉시 반영 |
| DEV-06 | 빌드/테스트 품질 유지 | Sonnet 구현 후 tsc 0 errors, pytest 통과 |

---

## 8. Prophet 3-Tier 대응

개발 워크플로우의 모델 선택이 Prophet 시뮬레이션의 3-Tier 전략과 동일한 철학을 공유:

| Prophet 시뮬레이션 | 개발 워크플로우 | 비율 |
|-------------------|---------------|------|
| **Tier 1: Mass SLM** (80%) | **Sonnet 4.6**: 코드 구현, 테스트, 리팩토링 | ~80% |
| **Tier 2: Heuristic** (10%) | **직접 도구 사용**: Glob, Grep, Read (모델 불필요) | ~10% |
| **Tier 3: Elite LLM** (10%) | **Opus 4.6**: SPEC, Plan, 아키텍처, 감사 | ~10% |

> "Prophet이 에이전트 시뮬레이션에서 비용을 최적화하듯,
> 개발 과정에서도 동일한 원칙으로 AI 모델 비용을 최적화한다."

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-03-29 | Initial draft — model selection strategy |
