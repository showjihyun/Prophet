# UI-16 — Campaign Setup SPEC
Version: 0.1.0 | Status: DRAFT
Route: `/setup` | `/projects/:projectId/new-scenario`

---

## 1. Overview

Campaign Setup은 새 시뮬레이션을 생성하기 위한 폼 페이지이다. 사용자는 프로젝트를 선택하고, 캠페인 파라미터(메시지, 예산, 채널, 타겟 커뮤니티)를 설정하며, 커뮤니티 구성을 커스터마이징한 뒤 시뮬레이션을 생성한다. Clone 기능을 통해 기존 시뮬레이션 설정을 복사할 수 있다.

**진입 경로:**
- Projects List (UI-06) → "+ New Scenario" 버튼
- Project Scenarios (UI-07) → "+ New Scenario" 버튼
- Simulation List → "New Simulation" 버튼
- ControlPanel → "Clone" 버튼 (pre-fill 모드)

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| +---------+----------------------------------------------------------+ |
| | Sidebar | Main Content (centered, max-w-2xl)                       | |
| | 256px   |                                                          | |
| | [SvySF] | Breadcrumb: Projects > [Project Name] > Campaign Setup   | |
| |         |                                                          | |
| | [Nav]   | Page Title: "Create New Simulation"                      | |
| | Projects|                                                          | |
| | Simulat.| Section 1: Project Selector                              | |
| | Global  | [Project dropdown / read-only if from URL]                | |
| | Insights|                                                          | |
| | Settings| Section 2: Campaign Info                                 | |
| |         | [Campaign Name] [Budget ($)]                             | |
| |         | [Channels: checkboxes]                                   | |
| |         | [Campaign Message: textarea]                             | |
| |         |                                                          | |
| |         | Section 3: Target Communities                             | |
| |         | [Community toggle pills]                                 | |
| |         |                                                          | |
| |         | Section 4: Campaign Attributes                           | |
| |         | [Controversy: slider 0–1]                                | |
| |         | [Novelty: slider 0–1]                                    | |
| |         | [Utility: slider 0–1]                                    | |
| |         |                                                          | |
| |         | Section 5: Community Configuration (collapsible)         | |
| |         | [Load from Templates] button                             | |
| |         | +----------------------------------------------------+   | |
| |         | | Community Card: Alpha                              |   | |
| |         | | Agent Type: [dropdown] | Count: [number]           |   | |
| |         | | Personality: 5 sliders (openness, skepticism, ...)  |   | |
| |         | | [Remove]                                            |   | |
| |         | +----------------------------------------------------+   | |
| |         | | Community Card: Beta ...                            |   | |
| |         | +----------------------------------------------------+   | |
| |         | [+ Add Community] button                                 | |
| |         |                                                          | |
| |         | Section 6: Advanced Settings (collapsible)               | |
| |         | [Max Steps] [Random Seed] [SLM/LLM Ratio slider]        | |
| |         | [LLM Provider: dropdown]                                 | |
| |         |                                                          | |
| |         | [Error display area]                                     | |
| |         | [Create Simulation] primary button                       | |
| +---------+----------------------------------------------------------+ |
+------------------------------------------------------------------------+
```

---

## 3. Components

### 3.1 Page Navigation (Breadcrumb)

| Element | Description |
|---------|-------------|
| Breadcrumb | `Projects > [Project Name] > Campaign Setup` |
| Back link | Projects 또는 Project Scenarios로 복귀 |

- URL에 `projectId`가 있으면 해당 프로젝트명 표시
- 없으면 `Projects > Campaign Setup`

### 3.2 Project Selector

| Element | Type | Description |
|---------|------|-------------|
| Label | text | "Project" (required) |
| Dropdown | `<select>` | 프로젝트 목록 (API: `GET /projects`) |
| Read-only input | `<input readOnly>` | URL에 projectId가 있을 때 |

- 프로젝트 미선택 시 Submit 차단, 에러 메시지 표시
- URL에 `projectId`가 있으면 read-only로 잠금

### 3.3 Campaign Info Section

| Field | Type | Validation | Default |
|-------|------|------------|---------|
| Campaign Name | text input | required, min 1 char | "" |
| Budget ($) | number input | min 0 | 0 |
| Channels | checkbox group | min 1 recommended | empty |
| Campaign Message | textarea (4 rows) | optional | "" |

**Channels 옵션:** `SNS`, `Influencer`, `Online Ads`, `TV`, `Email`

### 3.4 Target Communities

| Element | Type | Description |
|---------|------|-------------|
| Community pills | toggle buttons | 클릭 시 선택/해제 |
| Visual | color-coded pill | 선택 시 배경색 = 커뮤니티 컬러, 미선택 시 outline |

**기본 커뮤니티:**
| ID | Name | Color |
|----|------|-------|
| alpha | Alpha | `#3b82f6` (blue) |
| beta | Beta | `#22c55e` (green) |
| gamma | Gamma | `#f97316` (orange) |
| delta | Delta | `#a855f7` (purple) |
| bridge | Bridge | `#ef4444` (red) |

- 빈 선택 = "all" (전체 대상)
- Community Configuration Section에서 커뮤니티를 추가하면 여기에도 반영

### 3.5 Campaign Attributes Section (NEW)

캠페인의 확산 특성을 제어하는 3가지 속성. Backend `CampaignInput` 스키마에 이미 존재하지만 현재 프론트엔드에 미노출.

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| Controversy | range slider | 0.0–1.0 | 0.1 | 논란 수준 — 높을수록 양극화 유발 |
| Novelty | range slider | 0.0–1.0 | 0.5 | 새로움 — 높을수록 주목도 증가 |
| Utility | range slider | 0.0–1.0 | 0.5 | 실용성 — 높을수록 채택 가능성 증가 |

- 각 슬라이더 옆에 현재 값 표시 (소수점 1자리)
- 툴팁으로 속성 설명 제공

### 3.6 Community Configuration Section (NEW — collapsible)

커뮤니티별 에이전트 구성을 세부 조정하는 섹션. 06_API_SPEC의 `communities` 배열에 매핑.

#### Load from Templates
- 버튼: "Load from Templates"
- API: `GET /communities/templates/`
- 기본 5개 커뮤니티 템플릿 로드

#### Community Card (반복)

| Field | Type | Validation | Description |
|-------|------|------------|-------------|
| Community Name | text input | required | e.g., "Early Adopters" |
| Agent Type | dropdown | required | `early_adopter`, `mainstream`, `skeptic`, `influencer`, `bridge` |
| Agent Count | number input | min 10, max 5000 | 커뮤니티 내 에이전트 수 |
| Openness | range slider | 0.0–1.0 | 개방성 |
| Skepticism | range slider | 0.0–1.0 | 회의성 |
| Trend Following | range slider | 0.0–1.0 | 트렌드 추종 |
| Brand Loyalty | range slider | 0.0–1.0 | 브랜드 충성 |
| Social Influence | range slider | 0.0–1.0 | 사회적 영향력 |
| Remove button | button | min 1 community required | 커뮤니티 삭제 |

#### Add Community
- 버튼: "+ Add Community"
- 기본값으로 새 커뮤니티 카드 추가
- 최소 1개 커뮤니티 필수

### 3.7 Advanced Settings (collapsible `<details>`)

| Field | Type | Range | Default | Description |
|-------|------|-------|---------|-------------|
| Max Steps | number input | 1–1000 | 365 | 시뮬레이션 일수 |
| Random Seed | number input | any integer | 42 | 재현성용 시드 |
| SLM/LLM Ratio | range slider | 0–100% | 80% SLM | SLM 비율 |
| LLM Provider | dropdown | ollama/claude/openai | ollama | 기본 LLM 프로바이더 |

- SLM/LLM Ratio 슬라이더 아래에 `{n}% SLM / {100-n}% LLM` 표시

### 3.8 Submit Area

| Element | Condition | Action |
|---------|-----------|--------|
| Error display | 에러 시 표시 | destructive 스타일 alert |
| "Create Simulation" button | name + project required | POST /simulations → POST /projects/{id}/scenarios |
| Loading state | submitting | "Creating..." + disabled |

---

## 4. Data Flow

### 4.1 Submit Flow

```
1. Validate form (name required, project required, min 1 community)
2. Build CreateSimulationConfig:
   {
     name, description,
     campaign: { name, budget, channels, message, target_communities,
                 controversy, novelty, utility },
     communities: [ { id, name, size, agent_type, personality_profile } ],
     max_steps, default_llm_provider, random_seed,
     slm_llm_ratio, budget_usd
   }
3. POST /api/v1/simulations → SimulationCreateResponse
4. Store result in Zustand (setSimulation, setStatus)
5. POST /api/v1/projects/{projectId}/scenarios (link simulation)
6. Navigate to /simulation
```

### 4.2 Clone Flow (Pre-fill)

```
1. ControlPanel에서 "Clone" → setCloneConfig(config) in Zustand
2. Navigate to /setup
3. CampaignSetupPage mount → read cloneConfig
4. Pre-fill all form fields from cloneConfig
5. Clear cloneConfig (setCloneConfig(null))
6. 사용자가 수정 후 Submit
```

### 4.3 API Dependencies

| API Call | Timing | Purpose |
|----------|--------|---------|
| `GET /projects` | on mount | 프로젝트 목록 로드 |
| `GET /communities/templates/` | on "Load from Templates" click | 커뮤니티 템플릿 로드 |
| `POST /simulations` | on submit | 시뮬레이션 생성 |
| `POST /projects/{id}/scenarios` | after simulation created | 프로젝트에 시나리오 연결 |

---

## 5. State Management

### Local State (useState)

| State | Type | Purpose |
|-------|------|---------|
| name | string | 캠페인 이름 |
| budget | string | 예산 (string for input) |
| channels | Set\<string\> | 선택된 채널 |
| message | string | 캠페인 메시지 |
| targetCommunities | Set\<string\> | 선택된 타겟 커뮤니티 |
| controversy | number | 논란도 (0–1) |
| novelty | number | 새로움 (0–1) |
| utility | number | 실용성 (0–1) |
| communities | CommunityConfig[] | 커뮤니티 상세 구성 |
| maxSteps | number | 최대 스텝 |
| randomSeed | number | 랜덤 시드 |
| slmLlmRatio | number | SLM 비율 (0–100) |
| llmProvider | string | LLM 프로바이더 |
| submitting | boolean | 제출 중 |
| error | string \| null | 에러 메시지 |

### Zustand (shared)

| State | Read/Write | Purpose |
|-------|------------|---------|
| cloneConfig | read + clear | Clone pre-fill 데이터 |
| setSimulation | write | 생성된 시뮬레이션 저장 |
| setStatus | write | 시뮬레이션 상태 저장 |

---

## 6. Validation Rules

| Rule | Field(s) | Error Message |
|------|----------|---------------|
| Project required | selectedProjectId | "Please select a project before creating a simulation." |
| Name required | name | "Campaign name is required." |
| Budget non-negative | budget | "Budget must be 0 or greater." |
| Max steps range | maxSteps | "Max steps must be between 1 and 1000." |
| Min 1 community | communities | "At least one community is required." |
| Agent count range | community.size | "Agent count must be between 10 and 5000." |
| Personality range | personality sliders | Auto-clamped by slider (0.0–1.0) |
| Attribute range | controversy/novelty/utility | Auto-clamped by slider (0.0–1.0) |

---

## 7. Acceptance Criteria

| ID | Test | Expected |
|----|------|----------|
| CS-01 | 프로젝트 미선택 시 Submit 차단 | 에러 메시지 표시, Submit disabled |
| CS-02 | 캠페인 이름 미입력 시 Submit 차단 | HTML required validation |
| CS-03 | Clone 진입 시 모든 필드 pre-fill | cloneConfig의 모든 값 반영 |
| CS-04 | Community Configuration에서 커뮤니티 추가/삭제 | 최소 1개 유지, 새 카드 추가 가능 |
| CS-05 | Load from Templates 클릭 | 5개 기본 커뮤니티 로드 |
| CS-06 | 성공적 Submit | Simulation 생성 → Scenario 연결 → /simulation 이동 |
| CS-07 | Submit 실패 시 에러 표시 | 에러 메시지 표시, submitting 해제 |
| CS-08 | Controversy/Novelty/Utility 슬라이더 | 값 변경 → API 요청에 반영 |
| CS-09 | Advanced Settings 토글 | collapsible 열기/닫기 |
| CS-10 | URL에 projectId 포함 시 | Project selector read-only |

---

## 8. Implementation Gap (현재 → 목표)

| Item | Current State | Target |
|------|--------------|--------|
| Campaign Attributes (controversy/novelty/utility) | Backend에만 존재, Frontend 미노출 | 3 슬라이더 추가 |
| Community Configuration Section | 하드코딩된 5개 토글 버튼만 | 편집 가능한 커뮤니티 카드 + 템플릿 로드 |
| LLM Provider 선택 | 미구현 | dropdown 추가 |
| Form validation | 최소 (name + project만) | 전체 필드 validation |
| communities 배열 전송 | null (서버 기본값 사용) | 사용자 구성값 전송 |
