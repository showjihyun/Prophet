# DESIGN.md — Prophet UI Design System

이 문서는 Prophet (MCASP) 프로젝트의 UI 디자인 전체를 총괄하는 마스터 문서입니다.
Pencil (.pen) 파일의 디자인 시스템과 5개 화면 SPEC을 연결하며, 구현 시 참조해야 할 모든 디자인 규칙을 정의합니다.

---

## 1. Design Source

| 항목 | 값 |
|------|-----|
| **디자인 도구** | Pencil (pencil.dev) |
| **파일** | `pencil-shadcn.pen` |
| **MCP 연결** | `.mcp.json` → pencil stdio server |
| **디자인 시스템 프레임** | `MzSDs` (shadcn: design system components) |
| **UI 컴포넌트 라이브러리** | shadcn/ui (Tailwind CSS 기반) |
| **아이콘** | Lucide Icons |
| **폰트** | Geist (body) + Instrument Serif (display) + Geist Mono (code) |

---

## 2. 화면 구성 (Screen Map)

```
  ┌─────────────────────────────────────┐
  │   UI_06: Projects List              │
  │   (프로젝트 관리 - 1440x900)          │
  │   Frame: 2Efo9                      │
  └─────────┬───────────────────────────┘
            │ Open project
  ┌─────────▼───────────────────────────┐
  │   UI_07: Project Scenarios          │
  │   (시나리오 관리 - 1440x900)          │
  │   Frame: d4eOq                      │
  └─────────┬───────────────────────────┘
            │ Run scenario / Results
  ┌─────────▼───────────────────────────┐
  │   UI_01: AI Social World Engine     │
  │   (메인 시뮬레이션 - 1440x900)        │
  │   Frame: FuHqi                      │
  └─────────┬───────────────────────────┘
            │
┌───────────┼───────────────┐
│           │               │
▼           ▼               ▼
┌──────────────┐ ┌─────────────────┐ ┌───────────────┐
│  UI_02:      │ │  UI_08:         │ │  UI_05:       │
│ Communities  │ │ Influencers     │ │ Global Metrics│
│  Detail      │ │ (w/ Pagination) │ │               │
│  LRkh8       │ │  iodBY          │ │  fjP3Z        │
└──────┬───────┘ └──────┬──────────┘ └───────────────┘
       │                │
       ▼                │ Filter btn
┌─────────────┐  ┌──────▼──────────┐
│  UI_04:     │  │  UI_09:         │
│ Agent Detail│  │ Filter Popover  │
│  pkFYA      │  │  9fgvc          │
└──┬──────┬───┘  └─────────────────┘
   │      │
   │      ▼ Intervene btn
   │  ┌──────────────────┐
   │  │  UI_10:          │
   │  │ Agent Intervene  │
   │  │  Modal (XLwVu)   │
   │  └──────────────────┘
   │
   ▼ Connections tab
┌─────────────────┐
│  UI_11:         │
│ Agent Connections│
│  Tab (vJLFD)    │
└─────────────────┘
```

### 화면-SPEC 매핑

| 화면 | SPEC 문서 | Pencil Frame | 크기 | 설명 |
|------|----------|-------------|------|------|
| 메인 시뮬레이션 | `docs/spec/ui/UI_01_SIMULATION_MAIN.md` | `FuHqi` | 1440x900 | Control Bar + Graph Engine + Metrics + Timeline |
| 커뮤니티 상세 | `docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md` | `LRkh8` | 1440x900 | 5 커뮤니티 카드 + 연결 매트릭스 |
| 인플루언서 목록 | `docs/spec/ui/UI_03_TOP_INFLUENCERS.md` | `V99cE` | 1440x900 | 데이터 테이블 + 분포 차트 |
| 에이전트 상세 | `docs/spec/ui/UI_04_AGENT_DETAIL.md` | `pkFYA` | 1440x900 | 프로필 + 활동 차트 + 인터랙션 |
| 글로벌 메트릭 | `docs/spec/ui/UI_05_GLOBAL_METRICS.md` | `fjP3Z` | 1440x900 | Polarization + Sentiment + 3-Tier Cost |
| 프로젝트 목록 | `docs/spec/ui/UI_06_PROJECTS_LIST.md` | `2Efo9` | 1440x900 | 프로젝트 대시보드 + 카드 그리드 |
| 프로젝트 시나리오 | `docs/spec/ui/UI_07_PROJECT_SCENARIOS.md` | `d4eOq` | 1440x900 | 시나리오 관리 + 실행/중지 |
| 인플루언서 (페이지네이션) | `docs/spec/ui/UI_08_INFLUENCERS_PAGINATION.md` | `iodBY` | 1440x900 | UI-03 확장 + 페이지네이션 바 |
| 인플루언서 필터 | `docs/spec/ui/UI_09_INFLUENCERS_FILTER.md` | `9fgvc` | 600x700 | 필터 팝오버 (커뮤니티/상태/점수) |
| 에이전트 개입 | `docs/spec/ui/UI_10_AGENT_INTERVENE.md` | `XLwVu` | 560x700 | 개입 모달 (메시지 주입/감정 변경) |
| 에이전트 커넥션 | `docs/spec/ui/UI_11_AGENT_CONNECTIONS.md` | `vJLFD` | 1440x900 | Ego 네트워크 그래프 + 커넥션 목록 |

---

## 3. Design Tokens (CSS Variables)

Pencil 파일에서 추출한 shadcn/ui 디자인 토큰. 3개 테마 축 지원.

### Theme Axes

| 축 | 옵션 |
|-----|------|
| **Mode** | Light, Dark |
| **Base** | Neutral, Gray, Stone, Zinc, Slate |
| **Accent** | Default, Red, Rose, Orange, Green, Blue, Yellow, Violet |

### Core Colors (Light/Dark)

| Token | Light | Dark | 용도 |
|-------|-------|------|------|
| `--background` | `#fafafa` | `#0a0a0a` | 페이지 배경 |
| `--foreground` | `#0a0a0a` | `#fafafa` | 기본 텍스트 |
| `--card` | `#fafafa` | `#171717` | 카드 배경 |
| `--card-foreground` | `#0a0a0a` | `#fafafa` | 카드 텍스트 |
| `--primary` | `#171717` | `#e5e5e5` | 주요 버튼, 강조 |
| `--primary-foreground` | `#fafafa` | `#171717` | 주요 버튼 텍스트 |
| `--secondary` | `#f5f5f5` | `#262626` | 보조 배경 |
| `--secondary-foreground` | `#171717` | `#fafafa` | 보조 텍스트 |
| `--muted` | `#f5f5f5` | `#262626` | 비활성 배경 |
| `--muted-foreground` | `#737373` | `#a3a3a3` | 비활성 텍스트 |
| `--accent` | `#f5f5f5` | `#262626` | 강조 배경 |
| `--accent-foreground` | `#171717` | `#fafafa` | 강조 텍스트 |
| `--destructive` | `#e7000b` | `#ff666999` | 삭제/위험 |
| `--border` | `#e5e5e5` | `#ffffff1a` | 테두리 |
| `--input` | `#e5e5e5` | `#ffffff1a` | 입력 필드 테두리 |
| `--ring` | `#a3a3a3` | `#737373` | 포커스 링 |
| `--popover` | `#fafafa` | `#171717` | 팝오버 배경 |

### Community Colors (고정, 테마 불변)

| 커뮤니티 | 색상 | Hex |
|---------|------|-----|
| Alpha | Blue | `#3b82f6` |
| Beta | Green | `#22c55e` |
| Gamma | Orange | `#f97316` |
| Delta | Purple | `#a855f7` |
| Bridge | Red | `#ef4444` |

### Semantic Colors

| 용도 | 색상 | Hex |
|------|------|-----|
| Positive sentiment | Green | `#22c55e` |
| Neutral sentiment | Gray | `#94a3b8` |
| Negative sentiment | Red | `#ef4444` |
| Warning / Polarization | Amber | `#f59e0b` |
| Info / WebGL status | Blue | `#3b82f6` |

### Typography

**Font Stack:**
| Role | Font | Fallback | Weight Range |
|------|------|----------|-------------|
| Display/Headings | Instrument Serif | Georgia, serif | 400-700 |
| Body/UI | Geist | system-ui, -apple-system, sans-serif | 400-700 |
| Data/Tables | Geist (tabular-nums) | system-ui, monospace | 400-600 |
| Code/Mono | Geist Mono | JetBrains Mono, monospace | 400 |

**Type Scale:**
| Level | Font | Size | Weight | Line Height | Use |
|-------|------|------|--------|-------------|-----|
| Display | Instrument Serif | 32px | 400 | 1.2 | Hero titles, page headers |
| Heading 1 | Instrument Serif | 24px | 400 | 1.3 | Section titles |
| Heading 2 | Geist | 18px | 600 | 1.4 | Panel headers |
| Heading 3 | Geist | 16px | 600 | 1.4 | Card titles |
| Body | Geist | 14px | 400 | 1.5 | Default text |
| Body Small | Geist | 13px | 400 | 1.5 | Secondary text |
| Label | Geist | 12px | 500 | 1.4 | Form labels, metadata |
| Caption | Geist | 11px | 400 | 1.4 | Timestamps, helper text |
| Micro | Geist | 10px | 500 | 1.3 | Badges, status indicators |
| KPI Number | Geist | 28px | 700 | 1.1 | Large stat values |

### Spacing Scale

Base unit: 4px. All spacing uses this scale.

| Token | Value | Use |
|-------|-------|-----|
| `--space-1` | 4px | Tight gaps (icon+text) |
| `--space-2` | 8px | List item padding, small gaps |
| `--space-3` | 12px | Card internal gaps |
| `--space-4` | 16px | Panel padding, section gaps |
| `--space-5` | 20px | Card padding |
| `--space-6` | 24px | Panel padding (large) |
| `--space-8` | 32px | Page padding |
| `--space-10` | 40px | Section spacing |
| `--space-12` | 48px | Large section spacing |
| `--space-16` | 64px | Page-level spacing |

### Borders & Radius

| 요소 | Corner Radius | Border |
|------|--------------|--------|
| 카드 | 8px | 1px `--border` |
| 버튼 | 6px | — |
| 뱃지 | 16px (pill) | — |
| 아바타 | 9999px (circle) | — |
| 입력 필드 | 6px | 1px `--input` |
| 팝업/모달 | 8px | 1px `--border` |

### Elevation (Shadows)

| Level | Shadow | Use |
|-------|--------|-----|
| `--shadow-xs` | `0 1px 2px rgba(0,0,0,0.3)` | Buttons, badges |
| `--shadow-sm` | `0 1px 3px rgba(0,0,0,0.4), 0 1px 2px rgba(0,0,0,0.3)` | Cards, panels |
| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.3)` | Dropdowns, popovers |
| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.4), 0 4px 6px rgba(0,0,0,0.3)` | Modals, dialogs |
| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.4), 0 8px 10px rgba(0,0,0,0.3)` | Floating panels |

Note: Dark mode shadows use higher opacity because dark surfaces need more contrast for depth perception.

### Interaction States

| State | Transform | Use |
|-------|-----------|-----|
| `hover` | `background: var(--accent)` | Clickable elements |
| `active` | `opacity: 0.8, scale(0.98)` | Press feedback |
| `focus-visible` | `outline: 2px solid var(--ring); outline-offset: 2px` | Keyboard focus |
| `disabled` | `opacity: 0.5; pointer-events: none` | Inactive elements |

---

## 4. Reusable Components (shadcn Design System)

Pencil 디자인 시스템 프레임(`MzSDs`)에서 추출한 87개 재사용 컴포넌트.

### Buttons

| Component | ID | Variants |
|-----------|----|----------|
| Button/Default | `VSnC2` | Primary fill, icon+label |
| Button/Large/Default | `C3KOZ` | Primary fill, larger padding |
| Button/Secondary | `e8v1X` | Secondary fill |
| Button/Destructive | `YKnjc` | Destructive fill |
| Button/Outline | `C10zH` | Border only, shadow |
| Button/Ghost | `3f2VW` | No fill, no border |
| Icon Button/* | `urnwK`, `PbuYK`, `EsgLk`, `hXOUF`, `Sx6Z0` | Icon-only variants |

### Form Controls

| Component | ID | State |
|-----------|----|-------|
| Input Group/Default | `1415a` | Empty |
| Input Group/Filled | `uHFal` | With value |
| Input/Default | `fEUdI` | No label |
| Select Group/Default | `w5c1O` | Dropdown |
| Textarea Group/Default | `BjRan` | Multi-line |
| Checkbox/Checked | `ovuDP` | Checked state |
| Switch/Checked | `c8fiq` | Toggle on |
| Radio/Selected | `LbK20` | Selected |

### Data Display

| Component | ID |
|-----------|----|
| Badge/Default | `UjXug` |
| Badge/Secondary | `WuUMk` |
| Badge/Destructive | `YvyLD` |
| Badge/Outline | `3IiAS` |
| Avatar/Text | `DpPVg` |
| Avatar/Image | `HWTb9` |
| Progress | `hahxH` |
| Tooltip | `lxrnE` |

### Layout

| Component | ID |
|-----------|----|
| Card | `pcGlv` |
| Card Action | `PiMGI` |
| Card Plain | `fpgbn` |
| Dialog | `OtykB` |
| Modal/Left | `oVUJY` |
| Modal/Center | `X6bmd` |
| Modal/Icon | `TfbzN` |
| Tabs | `PbofX` |
| Tab Item/Active | `coMmv` |
| Dropdown | `cTN8T` |
| Sidebar | `PV1ln` |
| Pagination | `U5noB` |

### Table

| Component | ID |
|-----------|----|
| Data Table | `shadcnDataTable` |
| Table | `bG7YL` |
| Table Row | `LoAux` |
| Table Cell | `FulCp` |
| Table Column Header | `w3NML` |
| Data Table Header | `KOEkG` |
| Data Table Footer | `RXiR9` |

---

## 5. Graph Engine Visual Spec (AI Social World)

메인 화면 중앙의 소셜 그래프 엔진은 별도의 시각 규칙을 따릅니다.

### Canvas

| 속성 | 값 |
|------|-----|
| 배경 | Radial gradient: `#0f172a` → `#020617` (center: 45%, 45%) |
| 렌더링 | WebGL (Cytoscape.js 또는 Sigma.js) |
| 대상 FPS | 60fps @ 6,500 nodes |

### Agent Nodes

| 유형 | 크기 | Effect |
|------|------|--------|
| 일반 Agent | 5px circle | 커뮤니티 색상, no glow |
| Influencer | 10px circle | glow shadow (blur: 8-12, spread: 1-2, 커뮤니티 색상) |
| Bridge Node | 7px circle | red glow (blur: 10, `#ef444480`) |
| Selected Node | 20px ring | white stroke 1.5px + green glow (blur: 16, `#22c55e40`) |
| Scatter (distant) | 3px circle | 커뮤니티 색상 10-30% opacity |

### Edges

| 유형 | Stroke | 색상 |
|------|--------|------|
| Intra-community | 0.5px | 커뮤니티 색상 15% opacity |
| Inter-community | 1px | `#ffffff08` to `#ffffff10` |
| Bridge edge | 1px | `#ef444420` |
| Cascade path | 2px | 커뮤니티 색상 40-50% (animated) |

### Cluster Backgrounds

각 커뮤니티는 반투명 ellipse로 시각적 영역 표시:
- Fill: 커뮤니티 색상 8% opacity (e.g., `#22c55e08`)
- Stroke: 커뮤니티 색상 20% opacity, 1px

### Overlays (absolute positioned)

| 요소 | 위치 | 배경 |
|------|------|------|
| Title ("AI Social World") | top-left (24, 20) | transparent |
| Zoom controls (+/-/max) | top-right (848, 20) | `#262626` + border `#404040` |
| Network Legend | bottom-left (24, 520) | `#0f172aCC` + border `#ffffff10` |
| Cascade Badge | bottom-left (24, 584) | `#22c55e15` + border `#22c55e30` |
| Node Detail Popup | near selected node | `#0f172aEE` + border `#ffffff15` |
| Status Overlay (FPS/nodes/edges) | bottom-right (730, 580) | `#0f172aCC` + border `#ffffff10` |

---

## 6. Navigation Flow

```
메인 시뮬레이션 (UI_01)
  ├── Control Bar → "Global Insights" 버튼 → Global Metrics (UI_05)
  ├── Community Panel → 커뮤니티 클릭 → Communities Detail (UI_02)
  ├── Metrics Panel → "Top Influencers" 클릭 → Top Influencers (UI_03)
  ├── Graph Engine → Agent 노드 클릭 → Agent Detail (UI_04)
  └── Timeline → 재생/일시정지/스텝 컨트롤

Communities Detail (UI_02)
  └── 커뮤니티 카드 → Agent 클릭 → Agent Detail (UI_04)

Top Influencers (UI_03)
  └── 테이블 행 클릭 → Agent Detail (UI_04)

Agent Detail (UI_04)
  └── "Back" → 이전 화면
  └── "Intervene" → 개입 모달

Global Metrics (UI_05)
  └── "Back to Simulation" → 메인 시뮬레이션 (UI_01)
  └── "Export Data" → CSV/JSON 다운로드
```

---

## 7. Responsive Breakpoints

| Breakpoint | 폭 | 동작 |
|-----------|------|------|
| Desktop (기본) | 1440px | 전체 레이아웃 |
| Laptop | 1280px | Metrics Panel 축소 (240px) |
| Tablet | 1024px | Community Panel 접기 (아이콘만) |
| Mobile | 768px 이하 | 지원하지 않음 (최소 1024px 권장) |

---

## 8. Accessibility

| 항목 | 규칙 |
|------|------|
| 색상 대비 | WCAG 2.1 AA 이상 (4.5:1 텍스트, 3:1 아이콘) |
| 그래프 색맹 대응 | 커뮤니티 구분은 색상 + 형태(크기/패턴) 병용 |
| 키보드 네비게이션 | Tab으로 Control Bar 버튼 순회 가능 |
| 스크린 리더 | `aria-label` 필수 (그래프 영역은 summary 텍스트 제공) |
| 모션 감소 | `prefers-reduced-motion` 미디어 쿼리로 glow/pulse 비활성화 |

---

## 9. Pencil → Code 동기화 워크플로우

### 자동 감지 (Hook 설정 완료)

```
Pencil에서 디자인 수정
    │
    ▼  mcp__pencil__batch_design 호출
PostToolUse Hook 발동
    │
    ▼  "Pencil design changed" 알림
Claude가 해당 Frame 읽기 (batch_get + get_screenshot)
    │
    ▼
docs/spec/ui/UI_XX_*.md 업데이트
    │
    ▼  SPEC 변경 감지 Hook
테스트 코드 생성/갱신 알림
```

### 수동 동기화 명령

```
1. Pencil에서 수정
2. Claude에게: "UI_01 SPEC 업데이트해줘"
3. Claude: batch_get(FuHqi) + get_screenshot(FuHqi) → SPEC 갱신
```

---

## 10. 구현 기술 매핑

| 디자인 요소 | 구현 기술 | 위치 |
|-----------|----------|------|
| shadcn 컴포넌트 | shadcn/ui + Tailwind CSS | `frontend/src/components/ui/` |
| 그래프 엔진 | Cytoscape.js (WebGL renderer) | `frontend/src/components/graph/` |
| 차트/타임라인 | Recharts | `frontend/src/components/timeline/` |
| 상태 관리 | Zustand | `frontend/src/store/` |
| 실시간 업데이트 | WebSocket | `frontend/src/hooks/useSimulationSocket.ts` |
| 디자인 토큰 | CSS Variables (Tailwind config) | `frontend/src/index.css` |
| 라우팅 | React Router v6 | `frontend/src/App.tsx` |

### React 컴포넌트 → Pencil Frame 매핑

| React 컴포넌트 | Pencil Frame | UI SPEC |
|---------------|-------------|---------|
| `SimulationPage.tsx` | `FuHqi` | UI_01 |
| `GraphPanel.tsx` | `KrXVA` | UI_01 §Graph Engine |
| `ControlPanel.tsx` | `ib0Jy` | UI_01 §Control Bar |
| `TimelinePanel.tsx` | `oLh4Q` | UI_01 §Timeline |
| `CommunityPanel.tsx` | `S24t3` | UI_01 §Community Panel |
| `MetricsPanel.tsx` | `MuKxh` | UI_01 §Metrics Panel |
| `CommunitiesDetailPage.tsx` | `LRkh8` | UI_02 |
| `TopInfluencersPage.tsx` | `V99cE` | UI_03 |
| `AgentDetailPage.tsx` | `pkFYA` | UI_04 |
| `GlobalMetricsPage.tsx` | `fjP3Z` | UI_05 |
| `ProjectsListPage.tsx` | `2Efo9` | UI_06 |
| `ProjectScenariosPage.tsx` | `d4eOq` | UI_07 |
| `TopInfluencersPaginatedPage.tsx` | `iodBY` | UI_08 |
| `InfluencersFilterPopover.tsx` | `9fgvc` | UI_09 |
| `AgentInterveneModal.tsx` | `XLwVu` | UI_10 |
| `AgentConnectionsTab.tsx` | `vJLFD` | UI_11 |

---

## 11. SPEC 문서 인덱스

| 문서 | 유형 | 경로 |
|------|------|------|
| **DESIGN.md** (이 파일) | 디자인 마스터 | `DESIGN.md` |
| UI_01 Simulation Main | 화면 SPEC | `docs/spec/ui/UI_01_SIMULATION_MAIN.md` |
| UI_02 Communities Detail | 화면 SPEC | `docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md` |
| UI_03 Top Influencers | 화면 SPEC | `docs/spec/ui/UI_03_TOP_INFLUENCERS.md` |
| UI_04 Agent Detail | 화면 SPEC | `docs/spec/ui/UI_04_AGENT_DETAIL.md` |
| UI_05 Global Metrics | 화면 SPEC | `docs/spec/ui/UI_05_GLOBAL_METRICS.md` |
| UI_06 Projects List | 화면 SPEC | `docs/spec/ui/UI_06_PROJECTS_LIST.md` |
| UI_07 Project Scenarios | 화면 SPEC | `docs/spec/ui/UI_07_PROJECT_SCENARIOS.md` |
| UI_08 Influencers Pagination | 화면 SPEC | `docs/spec/ui/UI_08_INFLUENCERS_PAGINATION.md` |
| UI_09 Influencers Filter | 화면 SPEC | `docs/spec/ui/UI_09_INFLUENCERS_FILTER.md` |
| UI_10 Agent Intervene | 화면 SPEC | `docs/spec/ui/UI_10_AGENT_INTERVENE.md` |
| UI_11 Agent Connections | 화면 SPEC | `docs/spec/ui/UI_11_AGENT_CONNECTIONS.md` |
| Frontend SPEC | 기술 SPEC | `docs/spec/07_FRONTEND_SPEC.md` |
| API SPEC | 데이터 계약 | `docs/spec/06_API_SPEC.md` |
