# UI Flow SPEC — Prophet (MCASP) User Journey
Version: 0.1.0 | Status: REVIEW | Date: 2026-04-04

이 문서는 Prophet 프론트엔드의 모든 사용자 흐름(User Flow)을 정의한다.
**검증 목적:** 각 플로우가 문서대로 작동하는지 확인할 때 사용.

---

## 1. 앱 진입 흐름

### FLOW-01: 최초 접속

```
브라우저 → /
  ├── localStorage["prophet-token"] 존재?
  │    ├── YES → Redirect → /projects (ProjectsListPage)
  │    └── NO  → Redirect → /projects (인증은 optional)
  └── 모든 경로에 ErrorBoundary 적용
```

**검증 항목:**
- [ ] `/` 접속 시 `/projects`로 리다이렉트
- [ ] ErrorBoundary: 컴포넌트 에러 발생 시 "Something went wrong" + "Reload" 버튼 표시

### FLOW-02: 로그인/회원가입

```
/login (LoginPage)
  ├── Username + Password 입력
  ├── [Login] 클릭
  │    → POST /api/v1/auth/login
  │    → 성공: localStorage에 token+username 저장 → /projects 이동
  │    → 실패: "Invalid username or password" 표시
  ├── [Register] 클릭
  │    → POST /api/v1/auth/register
  │    → 성공: 자동 로그인 → /projects 이동
  │    → 실패 409: "Username already taken"
  └── Enter 키: Login 실행
```

**검증 항목:**
- [ ] 빈 필드: Submit 버튼 비활성화
- [ ] 로그인 성공: `localStorage["prophet-token"]` 저장됨
- [ ] 회원가입 성공: 자동 로그인 후 `/projects` 이동
- [ ] 에러 메시지가 화면에 표시됨

### FLOW-03: 로그아웃

```
AppSidebar → Logout 버튼 클릭
  → localStorage["prophet-token"] 삭제
  → localStorage["prophet-username"] 삭제
  → /login 이동
```

**검증 항목:**
- [ ] 로그아웃 후 token 삭제됨
- [ ] `/login` 페이지로 이동

---

## 2. 프로젝트 관리 흐름

### FLOW-04: 프로젝트 생성

```
/projects (ProjectsListPage)
  → [New Project] 클릭
  → window.prompt("New project name:")
  → 입력 확인
  → POST /api/v1/projects/
  → 프로젝트 목록에 즉시 추가 (로컬 state)
```

**검증 항목:**
- [ ] 프로젝트 이름 입력 → 목록에 새 프로젝트 표시
- [ ] 빈 이름 또는 취소 → 아무 동작 없음
- [ ] API 에러 → 조용히 무시 (현재 동작)

### FLOW-05: 프로젝트 열기 → 시나리오 목록

```
/projects → 프로젝트 카드 클릭
  → simulationStore.setCurrentProject(projectId)
  → /projects/:projectId (ProjectScenariosPage)
  → GET /api/v1/projects/:projectId
  → 시나리오 목록 표시
```

**검증 항목:**
- [ ] 프로젝트 클릭 → 시나리오 목록 페이지 이동
- [ ] 시나리오가 없으면 "No scenarios yet" 표시
- [ ] 브레드크럼 "Projects" 클릭 → `/projects` 이동

### FLOW-06: 시나리오 실행 → 시뮬레이션 진입

```
/projects/:projectId → 시나리오 [Run] 클릭
  → POST /api/v1/projects/:projectId/scenarios/:scenarioId/run
  → GET /api/v1/simulations/:simulationId
  → simulationStore.setSimulation(sim)
  → /simulation 이동
```

**검증 항목:**
- [ ] Run 버튼 클릭 → `/simulation` 이동
- [ ] 시뮬레이션 store에 데이터 로드됨
- [ ] status가 "draft" 또는 "created"일 때만 Run 버튼 표시

### FLOW-07: 완료된 시나리오 결과 보기

```
/projects/:projectId → 시나리오 [Results] 클릭 (status === "completed")
  → GET /api/v1/simulations/:simulationId
  → simulationStore.setSimulation(sim)
  → /simulation 이동
```

**검증 항목:**
- [ ] Results 버튼 클릭 → 시뮬레이션 페이지에서 완료 상태 표시
- [ ] status "completed"일 때만 Results 버튼 표시

### FLOW-08: 시나리오 삭제

```
/projects/:projectId → 시나리오 [삭제(🗑)] 클릭
  → window.confirm("Delete scenario?")
  → DELETE /api/v1/projects/:projectId/scenarios/:scenarioId
  → 목록에서 즉시 제거 (로컬 state)
```

**검증 항목:**
- [ ] 확인 다이얼로그에서 "확인" → 시나리오 삭제됨
- [ ] "취소" → 아무 동작 없음

---

## 3. 캠페인 설정 흐름

### FLOW-09: 새 시나리오 생성 (Campaign Setup)

```
/projects/:projectId → [New Scenario] 클릭
  → /projects/:projectId/new-scenario (CampaignSetupPage)
  → GET /api/v1/projects/ (프로젝트 목록 로드)
  → 폼 작성:
     - 프로젝트 선택 (URL에서 자동 설정, 잠금)
     - 캠페인 이름 (필수)
     - 예산, 채널, 메시지, 타겟 커뮤니티
     - Campaign Attributes (controversy/novelty/utility 슬라이더)
     - Community Configuration (템플릿 로드 가능)
     - Advanced Settings (max_steps, seed, LLM 설정)
  → [Create Simulation] 클릭
     → POST /api/v1/simulations (시뮬레이션 생성)
     → POST /api/v1/projects/:projectId/scenarios (시나리오 연결)
     → simulationStore.setSimulation(sim)
     → /simulation 이동
```

**검증 항목:**
- [ ] 프로젝트 미선택 → 생성 불가
- [ ] 커뮤니티 이름 빈칸 → 빨간 테두리 + 생성 불가
- [ ] 에이전트 수 10 미만 또는 5000 초과 → 생성 불가
- [ ] "Load from Templates" → GET `/communities/templates/` → 커뮤니티 카드 채워짐
- [ ] "+ Add Community" → 빈 커뮤니티 카드 추가
- [ ] "Remove" → 커뮤니티 제거 (최소 1개는 유지)
- [ ] 생성 성공 → `/simulation` 이동
- [ ] 생성 실패 → 빨간 에러 배너

### FLOW-10: 시뮬레이션 복제 (Clone)

```
/simulation → ControlPanel → [Clone] 클릭
  → simulationStore.setCloneConfig({ name, campaign, max_steps, ... })
  → /setup 이동
  → CampaignSetupPage mount 시 cloneConfig 감지
  → 모든 폼 필드 pre-fill
  → cloneConfig 소비 후 null로 초기화
```

**검증 항목:**
- [ ] Clone 클릭 → `/setup` 이동
- [ ] 폼에 이전 시뮬레이션 설정이 pre-fill됨
- [ ] 이름에 "(clone)" 접미사 포함

---

## 4. 시뮬레이션 실행 흐름

### FLOW-11: 시뮬레이션 페이지 진입 (빈 상태)

```
/simulation (simulation === null)
  → ControlPanel 표시
  → 중앙에 "No Active Simulation" + Brain 아이콘
  → [Go to Projects] 버튼 → /projects 이동
```

**검증 항목:**
- [ ] simulation이 null이면 empty state 표시
- [ ] "Go to Projects" → `/projects` 이동

### FLOW-12: 인라인 시뮬레이션 생성

```
/simulation → ControlPanel → [New Simulation] 클릭
  → currentProjectId 확인 (없으면 alert)
  → window.prompt("Simulation name:")
  → POST /api/v1/simulations (직접 API 호출, 페이지 이동 없음)
  → simulationStore.setSimulation(sim)
  → simulationStore.setStatus("configured")
```

**검증 항목:**
- [ ] 프로젝트 미선택 → "Please select a project first" alert
- [ ] 이름 입력 → 시뮬레이션 생성 → 페이지 이동 없이 workspace 활성화
- [ ] 생성 실패 → alert 표시

### FLOW-13: 시뮬레이션 수동 실행 (Step-by-Step)

```
/simulation (status: configured/created)
  → [Play ▶] 클릭
     → POST /api/v1/simulations/:id/start
     → status → "running"
     → Auto-step 루프 시작 (1000/speed ms 간격)
        → POST /api/v1/simulations/:id/step (매 tick마다)
        → appendStep(result)
        → step + 1 >= max_steps → status → "completed"
  → [Pause ⏸] 클릭 (running일 때만)
     → POST /api/v1/simulations/:id/pause
     → status → "paused", auto-step 중단
  → [Step ⏭] 클릭 (수동 한 스텝)
     → POST /api/v1/simulations/:id/step
     → appendStep(result)
  → [Reset ⏹] 클릭
     → POST /api/v1/simulations/:id/stop
     → status → "created"
```

**검증 항목:**
- [ ] Play → status "running" + 자동 스텝 진행
- [ ] Pause → status "paused" + 스텝 중단
- [ ] Step → 한 스텝 실행 후 결과 표시
- [ ] Reset → 초기 상태 복귀
- [ ] Speed 변경(1x/2x/5x/10x) → 스텝 간격 변경 확인

### FLOW-14: Run All (전체 실행)

```
/simulation → [Run All] 클릭
  → POST /api/v1/simulations/:id/run-all
  → 응답: RunAllReport (total_steps, final_adoption_rate, ...)
  → status → "completed"
  → SimulationReportModal 자동 표시
```

**검증 항목:**
- [ ] Run All → 전체 스텝 완료까지 대기
- [ ] 완료 후 Report Modal 자동 열림
- [ ] Running 상태에서는 버튼 비활성화

### FLOW-15: WebSocket 실시간 업데이트

```
SimulationPage mount (simulationId 존재 시)
  → ws://localhost:8000/ws/:simulationId 연결
  → 서버 메시지 수신:
     step_result  → appendStep(data) → 그래프/타임라인/메트릭 업데이트
     emergent_event → appendEmergentEvent(event) → Toast 알림
     status_change → setStatus(status) → UI 상태 전환
  → 연결 끊김:
     → 자동 재연결 (1s, 2s, 4s, 8s, 16s, max 30s)
     → 최대 5회 시도
```

**검증 항목:**
- [ ] WebSocket 연결 성공 → `connected = true`
- [ ] step_result 수신 → 그래프 노드 업데이트
- [ ] emergent_event 수신 → Toast 알림 표시
- [ ] 연결 끊김 → 자동 재연결 시도

### FLOW-16: 시뮬레이션 완료 → 리포트

```
status === 'completed' && steps.length > 0
  → SimulationReportModal 자동 표시
  → 표시 내용: 총 스텝, 최종 adoption rate, sentiment, emergent events
  → [Export JSON] → GET /simulations/:id/export?format=json (다운로드)
  → [Export CSV]  → GET /simulations/:id/export?format=csv (다운로드)
  → [Run Again]   → /setup 이동
  → [Close]       → 모달 닫기
```

**검증 항목:**
- [ ] 시뮬레이션 완료 시 Report Modal 자동 열림
- [ ] Export JSON/CSV → 파일 다운로드
- [ ] Run Again → `/setup` 이동
- [ ] 메트릭 값이 steps 데이터와 일치

### FLOW-17: 키보드 단축키

```
SimulationPage (input/textarea 포커스 아닐 때):
  Space     → Play/Pause 토글
  ArrowRight → Step 한 번
  Escape     → Reset
```

**검증 항목:**
- [ ] Space → 상태에 따라 Play 또는 Pause
- [ ] ArrowRight → Step 실행
- [ ] 입력 필드 포커스 중에는 단축키 무시

---

## 5. 모달 흐름

### FLOW-18: 이벤트 주입 (Inject Event)

```
ControlPanel → [Inject Event] 클릭 → InjectEventModal 열림
  → 폼: Event Type (select), Content (필수), Controversy (slider), Target Communities
  → [Inject] 클릭
     → POST /api/v1/simulations/:id/inject-event
     → 성공: event_id + effective_step 표시
     → 실패: 에러 텍스트
  → 닫기: X / backdrop / Escape → 폼 리셋
```

**검증 항목:**
- [ ] Content 빈칸 → 주입 불가
- [ ] 성공 후 event_id와 effective_step 표시
- [ ] 모달 재열기 → 폼 초기화

### FLOW-19: 리플레이 (Replay)

```
ControlPanel → [Replay] 클릭 → ReplayModal 열림
  → Target Step 슬라이더 (1 ~ currentStep)
  → [Replay] 클릭
     → POST /api/v1/simulations/:id/replay/:step
     → 성공: replay_id + from_step 표시 (새 분기 생성)
  → 닫기: X / backdrop / Escape
```

**검증 항목:**
- [ ] 슬라이더 범위: 1 ~ currentStep
- [ ] 리플레이 성공 → replay_id 표시

### FLOW-20: 몬테카를로 시뮬레이션

```
ControlPanel → [Monte Carlo] 클릭 → MonteCarloModal 열림
  → Config Phase: Runs (10-500), LLM toggle
  → [Start] 클릭
     → POST /api/v1/simulations/:id/monte-carlo
     → Running Phase: 2초 간격 폴링
        → GET /api/v1/simulations/:id/monte-carlo/:jobId
        → 프로그레스 바 (completed_runs / n_runs)
     → Completed Phase: 결과 카드 (viral_probability, reach, community adoption)
     → Failed Phase: 에러 메시지
  → 닫기 → 폴링 취소
```

**검증 항목:**
- [ ] 폴링 중 모달 닫기 → 폴링 정지
- [ ] 완료 → 결과 메트릭 표시
- [ ] 실패 → 에러 메시지 표시

### FLOW-21: 에이전트 개입 (Agent Intervene)

```
/agents/:agentId → [Intervene] 클릭 (status === 'paused'일 때만 활성화)
  → AgentInterveneModal 열림
  → 폼: Type (필수), Scope, Duration, Strength (0-1), Message, Options
  → [Apply Intervention] 클릭
     → PATCH /api/v1/simulations/:simId/agents/:agentId
        modify_sentiment → { emotion: { trust: strength } }
        boost_influence  → { personality: { social_influence: strength } }
        항상 belief = strength * 2 - 1
     → API 실패 → 경고 로그 + 모달 닫기 (로컬 적용)
  → 닫기: X / backdrop / Escape → 폼 리셋
```

**검증 항목:**
- [ ] status !== 'paused' → Intervene 버튼 비활성화
- [ ] Type 미선택 → Apply 불가
- [ ] Strength 범위 밖 → 빨간 테두리
- [ ] Override Tier 토글 → 경고 메시지 표시

---

## 6. 데이터 탐색 흐름

### FLOW-22: 커뮤니티 탐색

```
AppSidebar → Communities → /communities
  → GET /api/v1/simulations/:simId/communities/ (simId 있을 때)
  → 4개 요약 카드 + 커뮤니티 카드 그리드
  → 커뮤니티 카드 클릭 → /communities/:communityId
  → Influencer ID 클릭 → /agents/:agentId
  → [Manage Templates] → /communities/manage
```

**검증 항목:**
- [ ] 시뮬레이션 없으면 mock 데이터 표시
- [ ] 커뮤니티 카드에 adoption rate, sentiment, influencer 표시
- [ ] 카드 클릭 → 해당 커뮤니티 상세 이동

### FLOW-23: 인플루언서 탐색

```
AppSidebar → Influencers → /influencers
  → GET /api/v1/simulations/:simId/agents?limit=200
  → 테이블: Rank, Agent ID, Community, Influence Score, Sentiment, ...
  → 검색 → 실시간 필터 + 페이지 리셋
  → [Filter] → InfluencersFilter 팝오버 (커뮤니티/상태/점수/감정)
  → 행 클릭 → /agents/:agentId
  → 페이지네이션: rows-per-page + 페이지 번호
```

**검증 항목:**
- [ ] 검색어 입력 → 테이블 실시간 필터링
- [ ] 필터 적용 → 필터 배지 카운트 표시
- [ ] 행 클릭 → 에이전트 상세 이동
- [ ] 페이지 이동 → 데이터 갱신

### FLOW-24: 에이전트 상세

```
/agents/:agentId (AgentDetailPage)
  → GET /api/v1/simulations/:simId/agents/:agentId
  → GET /api/v1/simulations/:simId/network
  → 탭:
     Activity (기본) → Sentiment 차트 + Recent Interactions 테이블
     Connections → EgoGraph (force-directed) + Top Connections 목록
     Messages → 메시지 카드 (mock 데이터)
  → [Intervene] → AgentInterveneModal (paused 시에만)
  → Target Agent 클릭 → /agents/:targetId
  → Connection 클릭 → /agents/:connId
```

**검증 항목:**
- [ ] 3개 탭 전환 정상
- [ ] 에이전트 프로필(성격/감정/belief) 표시
- [ ] Connections 탭 → EgoGraph 렌더링
- [ ] Intervene 버튼 → paused 아니면 비활성화

### FLOW-25: 글로벌 메트릭

```
/metrics (GlobalMetricsPage)
  → Store steps 없으면 GET /api/v1/simulations/:simId/steps
  → 4개 요약 카드 + Polarization Trend + Sentiment by Community
  → 3-Tier Cost Optimization 표시
  → [Export JSON/CSV] → GET /simulations/:id/export
```

**검증 항목:**
- [ ] 시뮬레이션 없으면 empty state
- [ ] steps 있으면 차트 데이터 렌더링
- [ ] Polarization 색상: green < 0.3, amber 0.3-0.6, red > 0.6

### FLOW-26: 의견 탐색 흐름

```
/opinions (ScenarioOpinionsPage)
  → Store steps 없으면 GET /api/v1/simulations/:simId/steps
  → 4개 stat 카드 + Community Opinion 카드 그리드
  → [View Community] → /opinions/:communityId

/opinions/:communityId (CommunityOpinionPage)
  → 왼쪽: Opinion Clusters (topic, stance %)
  → 오른쪽: Recent Conversations 리스트
  → 대화 카드 클릭 → /opinions/:communityId/thread/:threadId

/opinions/:communityId/thread/:threadId (ConversationThreadPage)
  → GET /api/v1/simulations/:simId/communities/:communityId/threads/:threadId
  → 메시지 목록: 에이전트 아바타, stance 배지, 내용, reactions
  → 답글은 pl-12 들여쓰기
```

**검증 항목:**
- [ ] 커뮤니티 카드 → 커뮤니티 의견 페이지 이동
- [ ] 대화 카드 → 스레드 페이지 이동
- [ ] API 데이터 → Store 데이터 → Mock 데이터 우선순위로 표시
- [ ] 메시지 stance 배지 색상 (Progressive/Conservative/Neutral)

### FLOW-27: 시나리오 비교

```
/simulation → ControlPanel → Compare 드롭다운 → 시뮬레이션 선택
  → /compare/:otherId
  → GET /api/v1/simulations/:id/compare/:otherId
  → Side-by-side 비교: Adoption Rate, Mean Sentiment, Propagation, Viral Cascades
  → 높은 값 녹색 하이라이트
  → [Back] → navigate(-1)
```

**검증 항목:**
- [ ] Compare 드롭다운에서 현재 시뮬레이션 제외
- [ ] 비교 결과 4개 메트릭 표시
- [ ] 높은 쪽 녹색 표시

### FLOW-28: 분석 대시보드

```
AppSidebar → Analytics → /analytics
  → Store steps 없으면 GET /api/v1/simulations/:simId/steps
  → 요약 카드 (Total Steps, Final Adoption, Final Sentiment, Events)
  → Adoption Rate / Sentiment 시계열 차트
  → Community Adoption 비교 차트 (final step)
  → Emergent Event Timeline
  → Monte Carlo: "No results" placeholder
```

**검증 항목:**
- [ ] 시뮬레이션 없으면 "No active simulation" + "Go to Projects" 버튼
- [ ] 차트에 emergent event 마커 표시
- [ ] 이벤트 타임라인에 아이콘별 구분 (viral/polarization/collapse 등)

---

## 7. 설정 흐름

### FLOW-29: 설정 변경

```
/settings (SettingsPage)
  → 4개 병렬 API 호출:
     GET /api/v1/settings/
     GET /api/v1/settings/ollama-models
     GET /api/v1/settings/platforms
     GET /api/v1/settings/recsys
  → 섹션:
     LLM Provider → Ollama (URL, 모델), Claude (API key, 모델), OpenAI (API key, 모델)
     [Test Connection] → POST /api/v1/settings/test-ollama → 성공/실패 + latency 표시
     Simulation Defaults → SLM/LLM ratio, Tier 3 ratio, Cache TTL
     Platform → platform selector, recsys selector
  → [Save] 클릭
     → PUT /api/v1/settings/
     → 성공: "Saved" 체크 3초
     → 실패: "Save failed" 에러
```

**검증 항목:**
- [ ] 페이지 로드 → 현재 설정값 표시
- [ ] Ollama 모델 드롭다운 → API에서 로드된 모델 목록
- [ ] Test Connection → 성공 시 latency 표시, 실패 시 에러 메시지
- [ ] API key 입력 → 저장 시에만 전송 (빈 값이면 미포함)
- [ ] Save → 성공 알림

---

## 8. 네비게이션 구조

### 사이드바 (AppSidebar)

| 항목 | 경로 | 아이콘 |
|------|------|--------|
| Projects | `/projects` | FolderOpen |
| Simulation | `/simulation` | Brain |
| Communities | `/communities` | Users |
| Influencers | `/influencers` | TrendingUp |
| Global Insights | `/metrics` | BarChart2 |
| Analytics | `/analytics` | LineChart |
| Opinions | `/opinions` | MessageCircle |
| Settings | `/settings` | Settings |

**동작:**
- 확장: 256px / 축소: 60px (아이콘 전용)
- 모바일 (<=768px): 자동 축소
- 축소 시 아이콘에 `aria-label` 표시
- 활성 항목: 배경색 하이라이트
- 하단: 사용자명 + Logout + ThemeToggle

### 레이아웃 분류

| 레이아웃 | 적용 페이지 |
|----------|------------|
| Full-screen (사이드바 없음) | `/simulation`, `/login` |
| SidebarLayout | 나머지 모든 페이지 |

---

## 9. 상태 의존성 맵

### Zustand Store 핵심 상태 흐름

```
[Project 선택]                    [Simulation 생성/로드]
      │                                  │
      ▼                                  ▼
 currentProjectId  ──────────→    simulation (SimulationRun)
 projects[]                       status (SimulationStatus)
 scenarios[]                      steps[] (StepResult[])
                                  emergentEvents[]
                                       │
                    ┌──────────────────┼──────────────────┐
                    ▼                  ▼                  ▼
              GraphPanel         TimelinePanel      MetricsPanel
              (Cytoscape)        (Recharts)         (실시간 지표)
                    │
                    ▼
              selectedAgentId → AgentInspector (right drawer)
```

### 데이터 소스 우선순위

모든 데이터 탐색 페이지는 동일한 패턴:
1. **API 실시간 데이터** (simulation 존재 + API 호출 성공)
2. **Zustand store steps** (이전 스텝에서 누적된 데이터)
3. **Mock 데이터** (시뮬레이션 없거나 API 실패 시)

### 주요 교차 페이지 의존성

| Store 필드 | 설정하는 곳 | 사용하는 곳 |
|-----------|-----------|-----------|
| `simulation` | CampaignSetup, ProjectScenarios, ControlPanel | 모든 데이터 페이지 |
| `steps` | ControlPanel auto-step, WebSocket | GlobalMetrics, Opinions, Analytics, AgentDetail |
| `currentProjectId` | ProjectsList, ControlPanel | ControlPanel (시나리오/시뮬레이션 셀렉터) |
| `cloneConfig` | ControlPanel Clone | CampaignSetupPage (pre-fill) |
| `selectedAgentId` | GraphPanel/CommunityPanel 클릭 | SimulationPage → AgentInspector |
| `theme` | ThemeToggle | 전역 CSS variables |

---

## 10. 알려진 제한사항 / 미구현 항목

| 항목 | 현재 상태 | 영향 |
|------|----------|------|
| WebSocket heartbeat (30s ping) | ✅ 구현됨 | — |
| "Click to retry" 배너 (5회 재연결 실패 후) | ✅ 구현됨 | `retryExhausted` + amber 배너 |
| ProjectScenarios Stop 버튼 | ✅ 구현됨 | `handleStop` + API 호출 |
| ProjectScenarios More(⋯) 버튼 | ✅ 구현됨 | Duplicate/Delete 드롭다운 |
| AgentDetail Messages 탭 | ✅ API 연동됨 | `getMemory` → Messages, Mock fallback |
| ConversationThread reaction 버튼 | ✅ 로컬 토글 | `useReactions` hook |
| ScenarioOpinions "Map vs Faction" 토글 | ✅ 구현됨 | `viewMode` state + FactionMapView |
| CommunityOpinion Sort 드롭다운 | ✅ 구현됨 | `sortMode` + 3가지 정렬 |
| TanStack Query hooks (useSimulationData) | 정의만 존재, 미사용 | 페이지들이 직접 apiClient 호출 |
| Monte Carlo in Analytics | ✅ 구현됨 | API + localStorage fallback |
| `llm.getCalls` API client 메서드 | ✅ 구현됨 | `apiClient.llm.getCalls()` |

---

## Appendix: 전체 User Journey 요약

```
[Login] → /projects → [New Project] → /projects/:id
                         │
                    [New Scenario] → /projects/:id/new-scenario (CampaignSetup)
                         │                        │
                    [Run Scenario]          [Create Simulation]
                         │                        │
                         └────────────────────────┘
                                   │
                              /simulation
                          ┌────────┴────────┐
                     [Play/Pause/Step]    [Modals]
                     [Run All]         Inject/Replay/MC
                          │
                     [Completed] → ReportModal → [Export] / [Run Again]
                          │
              ┌───────────┼───────────┐
         /communities  /influencers  /metrics  /opinions  /analytics
              │           │                       │
         /communities/:id  /agents/:id     /opinions/:cid/thread/:tid
                           │
                    [Intervene] (paused)
```
