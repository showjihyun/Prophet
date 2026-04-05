# 11 — Community Management SPEC
Version: 0.1.0 | Status: DRAFT | Date: 2026-04-05

---

## 1. Overview

시뮬레이션 실행 중 커뮤니티를 동적으로 관리하는 기능.
캠페인 셋업 시 초기 구성 외에, **paused 상태에서** 커뮤니티 편집/추가/삭제/에이전트 재배정이 가능하다.

**핵심 원칙:**
- 시뮬레이션이 `paused` 또는 `configured` 상태일 때만 변경 가능
- `running` 상태에서는 읽기 전용
- 모든 변경은 in-memory state에 즉시 반영, DB에 비동기 persist

---

## 2. API Endpoints

### 2.1 커뮤니티 편집 (Update)

```
PATCH /api/v1/simulations/{simulation_id}/communities/{community_id}
```

**Request:**
```json
{
  "name": "Early Adopters (Revised)",
  "personality_profile": {
    "openness": 0.9,
    "skepticism": 0.2,
    "trend_following": 0.8,
    "brand_loyalty": 0.3,
    "social_influence": 0.7
  }
}
```

**Response 200:**
```json
{
  "community_id": "uuid",
  "name": "Early Adopters (Revised)",
  "size": 100,
  "personality_profile": { ... },
  "agents_updated": 100
}
```

**Error:**
- 409: 시뮬레이션이 `running` 상태
- 404: community_id가 존재하지 않음

**동작:**
- `personality_profile`이 변경되면, 해당 커뮤니티의 **모든 에이전트** 성격 값을
  새 프로파일 기준으로 ±10% 랜덤 편차를 유지하며 업데이트
- `name` 변경은 display 전용 (에이전트에 영향 없음)

### 2.2 커뮤니티 추가 (Create)

```
POST /api/v1/simulations/{simulation_id}/communities
```

**Request:**
```json
{
  "name": "New Segment",
  "agent_type": "consumer",
  "size": 50,
  "personality_profile": {
    "openness": 0.5,
    "skepticism": 0.5,
    "trend_following": 0.5,
    "brand_loyalty": 0.5,
    "social_influence": 0.4
  }
}
```

**Response 201:**
```json
{
  "community_id": "uuid",
  "name": "New Segment",
  "size": 50,
  "agents_created": 50,
  "edges_created": 120
}
```

**동작:**
- `size`개의 새 에이전트를 생성 (personality = profile ±10% 편차)
- 기존 네트워크에 `cross_community_prob` 확률로 cross-community 엣지 추가
- 커뮤니티 내부 엣지는 Watts-Strogatz 방식으로 생성

### 2.3 커뮤니티 삭제 (Delete)

```
DELETE /api/v1/simulations/{simulation_id}/communities/{community_id}
```

**Response 200:**
```json
{
  "community_id": "uuid",
  "agents_removed": 100,
  "edges_removed": 350
}
```

**제약:** 최소 1개 커뮤니티는 유지해야 함 (마지막 커뮤니티 삭제 시 400)

**동작:**
- 해당 커뮤니티의 모든 에이전트를 `agents` 리스트에서 제거
- 제거된 에이전트와 연결된 모든 엣지를 네트워크에서 제거
- step_history에 영향 없음 (과거 데이터 유지)

### 2.4 에이전트 재배정 (Reassign)

```
POST /api/v1/simulations/{simulation_id}/communities/{community_id}/reassign
```

**Request:**
```json
{
  "agent_ids": ["uuid1", "uuid2"],
  "target_community_id": "uuid-target"
}
```

**Response 200:**
```json
{
  "reassigned_count": 2,
  "source_community_id": "uuid-source",
  "target_community_id": "uuid-target"
}
```

**동작:**
- 에이전트의 `community_id`를 target으로 변경
- 기존 cross-community 엣지는 유지
- 새 커뮤니티 내 에이전트와의 엣지를 `cross_community_prob`로 생성

---

## 3. Frontend UI

### 3.1 커뮤니티 상세 페이지 (`/communities/:communityId`)

기존 `CommunitiesDetailPage`의 `:communityId` 라우트를 실제 상세 페이지로 구현.

**표시 내용:**
- 커뮤니티 프로필 카드 (이름, 타입, 에이전트 수, 생성 시 personality profile)
- 소속 에이전트 목록 (테이블, 페이지네이션)
- 감정/행동 분포 차트
- 연결 강도 (이 커뮤니티 ↔ 다른 커뮤니티)

**액션 버튼 (paused/configured 시에만 활성화):**
- [Edit] → 커뮤니티 편집 모달
- [Delete] → 확인 다이얼로그 후 삭제

### 3.2 커뮤니티 편집 모달

**필드:**
- Community Name (text)
- Personality Profile (5 sliders: openness, skepticism, trend_following, brand_loyalty, social_influence)

**동작:**
- PATCH API 호출 → 성공 시 Toast "Community updated (N agents affected)"
- 실패 시 에러 토스트

### 3.3 커뮤니티 추가 버튼

`CommunitiesDetailPage`에 [+ Add Community] 버튼 추가.
- 클릭 → 추가 모달 (name, type, size, personality sliders)
- POST API → 성공 시 목록에 즉시 반영 + Toast

### 3.4 CommunitiesDetailPage 개선

- 각 커뮤니티 카드에 [Edit] [Delete] 아이콘 버튼 추가
- `simulation.status`가 `paused`/`configured`일 때만 활성화
- 삭제 시 confirm 다이얼로그

---

## 4. Orchestrator Integration

### SimulationOrchestrator 확장

```python
async def update_community(
    self,
    simulation_id: UUID,
    community_id: str,
    name: str | None = None,
    personality_profile: dict[str, float] | None = None,
) -> dict:
    """Update community properties. Requires PAUSED/CONFIGURED state."""

async def add_community(
    self,
    simulation_id: UUID,
    name: str,
    agent_type: str,
    size: int,
    personality_profile: dict[str, float],
) -> dict:
    """Add a new community with agents and edges."""

async def remove_community(
    self,
    simulation_id: UUID,
    community_id: str,
) -> dict:
    """Remove community and its agents/edges."""

async def reassign_agents(
    self,
    simulation_id: UUID,
    agent_ids: list[UUID],
    target_community_id: str,
) -> dict:
    """Move agents to a different community."""
```

### 상태 제약

| 현재 상태 | 허용 | 비허용 |
|----------|------|--------|
| `configured` | 모든 커뮤니티 관리 | — |
| `paused` | 모든 커뮤니티 관리 | — |
| `running` | 읽기 전용 | 편집/추가/삭제/재배정 → 409 |
| `completed` | 읽기 전용 | 편집/추가/삭제/재배정 → 409 |

---

## 5. Error Specification

| Condition | HTTP | Response |
|-----------|------|----------|
| 시뮬레이션 running/completed | 409 | "Community changes only allowed when paused or configured" |
| community_id not found | 404 | "Community not found" |
| 마지막 커뮤니티 삭제 시도 | 400 | "Cannot delete last community" |
| size < 1 or size > 10000 | 422 | Validation error |
| target_community_id not found (reassign) | 404 | "Target community not found" |
| agent_id not in source community | 400 | "Agent not in this community" |

---

## 6. Acceptance Criteria

- **CM-01:** PATCH community → 해당 커뮤니티의 모든 에이전트 personality 업데이트
- **CM-02:** POST community → 새 에이전트 + 네트워크 엣지 생성
- **CM-03:** DELETE community → 에이전트 + 엣지 제거, 최소 1개 유지
- **CM-04:** POST reassign → 에이전트 community_id 변경
- **CM-05:** running 상태에서 변경 시도 → 409
- **CM-06:** UI에서 편집/추가/삭제 버튼이 paused에서만 활성화
