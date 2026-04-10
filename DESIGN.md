# DESIGN.md — Prophet UI Design System

This document is the master reference for the Prophet (MCASP) project's UI design.
It ties the Pencil (.pen) design system together with the five screen SPECs and
defines every design rule that must be honored during implementation.

---

## 1. Design Source

| Item | Value |
|------|-------|
| **Design tool** | Pencil (pencil.dev) |
| **File** | `pencil-shadcn.pen` |
| **MCP connection** | `.mcp.json` → pencil stdio server |
| **Design system frame** | `MzSDs` (shadcn: design system components) |
| **UI component library** | shadcn/ui (Tailwind CSS based) |
| **Icons** | Lucide Icons |
| **Fonts** | Geist (body) + Instrument Serif (display) + Geist Mono (code) |

---

## 2. Screen Map

```
  ┌─────────────────────────────────────┐
  │   UI_06: Projects List              │
  │   (Project management — 1440x900)   │
  │   Frame: 2Efo9                      │
  └─────────┬───────────────────────────┘
            │ Open project
  ┌─────────▼───────────────────────────┐
  │   UI_07: Project Scenarios          │
  │   (Scenario management — 1440x900)  │
  │   Frame: d4eOq                      │
  └─────────┬───────────────────────────┘
            │ Run scenario / Results
  ┌─────────▼───────────────────────────┐
  │   UI_01: AI Social World Engine     │
  │   (Main simulation — 1440x900)      │
  │   Frame: FuHqi                      │
  │                                     │
  │   [Empty State when no simulation]  │
  │   ControlPanel "New Simulation" btn ├──────────────┐
  │   or empty state CTA                │              │
  └─────────┬───────────────────────────┘              │
            │                                          ▼
┌───────────┼───────────────┐               ┌────────────────────┐
│           │               │               │  Campaign Setup    │
▼           ▼               ▼               │  (/setup)          │
┌──────────────┐ ┌─────────────────┐ ┌───────────────┐ └────────────────────┘
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

> **Note:** `/setup` (Campaign Setup) is NOT a sidebar navigation item.
> It is only accessible from:
> 1. SimulationPage empty state "Create New Simulation" CTA (when no simulation is loaded)
> 2. ControlPanel "New Simulation" button (visible only when `simulation === null`)
> 3. Direct URL navigation


### Screen ↔ SPEC Mapping

| Screen | SPEC | Pencil Frame | Size | Description |
|--------|------|-------------|------|-------------|
| Main simulation | `docs/spec/ui/UI_01_SIMULATION_MAIN.md` | `FuHqi` | 1440x900 | Control Bar + Graph Engine + Metrics + Timeline |
| Community detail | `docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md` | `LRkh8` | 1440x900 | Five community cards + connection matrix |
| Influencers list | `docs/spec/ui/UI_03_TOP_INFLUENCERS.md` | `V99cE` | 1440x900 | Data table + distribution chart |
| Agent detail | `docs/spec/ui/UI_04_AGENT_DETAIL.md` | `pkFYA` | 1440x900 | Profile + activity chart + interactions |
| Global metrics | `docs/spec/ui/UI_05_GLOBAL_METRICS.md` | `fjP3Z` | 1440x900 | Polarization + Sentiment + 3-Tier Cost |
| Projects list | `docs/spec/ui/UI_06_PROJECTS_LIST.md` | `2Efo9` | 1440x900 | Project dashboard + card grid |
| Project scenarios | `docs/spec/ui/UI_07_PROJECT_SCENARIOS.md` | `d4eOq` | 1440x900 | Scenario management + run/stop |
| Influencers (paginated) | `docs/spec/ui/UI_08_INFLUENCERS_PAGINATION.md` | `iodBY` | 1440x900 | UI-03 extended with a pagination bar |
| Influencer filter | `docs/spec/ui/UI_09_INFLUENCERS_FILTER.md` | `9fgvc` | 600x700 | Filter popover (community / status / score) |
| Agent intervene | `docs/spec/ui/UI_10_AGENT_INTERVENE.md` | `XLwVu` | 560x700 | Intervention modal (message injection / emotion change) |
| Agent connections | `docs/spec/ui/UI_11_AGENT_CONNECTIONS.md` | `vJLFD` | 1440x900 | Ego network graph + connections list |

---

## 3. Design Tokens (CSS Variables)

shadcn/ui design tokens extracted from the Pencil file. Three theme axes are supported.

### Theme Axes

| Axis | Options |
|------|---------|
| **Mode** | Light, Dark |
| **Base** | Neutral, Gray, Stone, Zinc, Slate |
| **Accent** | Default, Red, Rose, Orange, Green, Blue, Yellow, Violet |

### Core Colors (Light/Dark)

| Token | Light | Dark | Use |
|-------|-------|------|-----|
| `--background` | `#fafafa` | `#0a0a0a` | Page background |
| `--foreground` | `#0a0a0a` | `#fafafa` | Default text |
| `--card` | `#fafafa` | `#171717` | Card background |
| `--card-foreground` | `#0a0a0a` | `#fafafa` | Card text |
| `--primary` | `#171717` | `#e5e5e5` | Primary buttons, emphasis |
| `--primary-foreground` | `#fafafa` | `#171717` | Primary button text |
| `--secondary` | `#f5f5f5` | `#262626` | Secondary background |
| `--secondary-foreground` | `#171717` | `#fafafa` | Secondary text |
| `--muted` | `#f5f5f5` | `#262626` | Inactive background |
| `--muted-foreground` | `#737373` | `#a3a3a3` | Inactive text |
| `--accent` | `#f5f5f5` | `#262626` | Accent background |
| `--accent-foreground` | `#171717` | `#fafafa` | Accent text |
| `--destructive` | `#e7000b` | `#ff666699` | Delete / danger |
| `--border` | `#e5e5e5` | `#ffffff1a` | Borders |
| `--input` | `#e5e5e5` | `#ffffff1a` | Input field borders |
| `--ring` | `#a3a3a3` | `#737373` | Focus ring |
| `--popover` | `#fafafa` | `#171717` | Popover background |

### Community Colors (fixed, theme-invariant)

| Community | Color | Hex |
|-----------|-------|-----|
| Alpha | Blue | `#3b82f6` |
| Beta | Green | `#22c55e` |
| Gamma | Orange | `#f97316` |
| Delta | Purple | `#a855f7` |
| Bridge | Red | `#ef4444` |

### Semantic Colors

| Use | Color | Hex |
|-----|-------|-----|
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
| `--space-1` | 4px | Tight gaps (icon + text) |
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

| Element | Corner Radius | Border |
|---------|--------------|--------|
| Card | 8px | 1px `--border` |
| Button | 6px | — |
| Badge | 16px (pill) | — |
| Avatar | 9999px (circle) | — |
| Input field | 6px | 1px `--input` |
| Popup/Modal | 8px | 1px `--border` |

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

87 reusable components extracted from the Pencil design system frame (`MzSDs`).

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

The social graph engine in the center of the main screen follows its own visual rules.

### Canvas

| Property | Value |
|----------|-------|
| Background | Radial gradient: `#0f172a` → `#020617` (center: 45%, 45%) |
| Rendering | WebGL (Cytoscape.js or Sigma.js) |
| Target FPS | 60fps @ 6,500 nodes |

### Agent Nodes

| Type | Size | Effect |
|------|------|--------|
| Regular Agent | 5px circle | Community color, no glow |
| Influencer | 10px circle | Glow shadow (blur: 8-12, spread: 1-2, community color) |
| Bridge Node | 7px circle | Red glow (blur: 10, `#ef444480`) |
| Selected Node | 20px ring | White stroke 1.5px + green glow (blur: 16, `#22c55e40`) |
| Scatter (distant) | 3px circle | Community color at 10-30% opacity |

### Edges

| Type | Stroke | Color |
|------|--------|-------|
| Intra-community | 0.5px | Community color, 15% opacity |
| Inter-community | 1px | `#ffffff08` to `#ffffff10` |
| Bridge edge | 1px | `#ef444420` |
| Cascade path | 2px | Community color, 40-50% (animated) |

### Cluster Backgrounds

Each community draws a translucent ellipse to mark its visual footprint:
- Fill: community color at 8% opacity (e.g., `#22c55e08`)
- Stroke: community color at 20% opacity, 1px

### Overlays (absolute positioned)

| Element | Position | Background |
|---------|----------|------------|
| Title ("AI Social World") | top-left (24, 20) | transparent |
| Zoom controls (+/-/max) | top-right (848, 20) | `#262626` + border `#404040` |
| Network Legend | bottom-left (24, 520) | `#0f172aCC` + border `#ffffff10` |
| Cascade Badge | bottom-left (24, 584) | `#22c55e15` + border `#22c55e30` |
| Node Detail Popup | near selected node | `#0f172aEE` + border `#ffffff15` |
| Status Overlay (FPS/nodes/edges) | bottom-right (730, 580) | `#0f172aCC` + border `#ffffff10` |

---

## 6. Navigation Flow

```
Main simulation (UI_01)
  ├── Control Bar → "Global Insights" button → Global Metrics (UI_05)
  ├── Community Panel → click community → Communities Detail (UI_02)
  ├── Metrics Panel → "Top Influencers" → Top Influencers (UI_03)
  ├── Graph Engine → click agent node → Agent Detail (UI_04)
  └── Timeline → play/pause/step controls

Communities Detail (UI_02)
  └── Community card → click agent → Agent Detail (UI_04)

Top Influencers (UI_03)
  └── Table row click → Agent Detail (UI_04)

Agent Detail (UI_04)
  └── "Back" → previous screen
  └── "Intervene" → intervention modal

Global Metrics (UI_05)
  └── "Back to Simulation" → Main simulation (UI_01)
  └── "Export Data" → CSV/JSON download
```

---

## 7. Responsive Breakpoints

| Breakpoint | Width | Behavior |
|------------|-------|----------|
| Desktop (default) | 1440px | Full layout |
| Laptop | 1280px | Metrics Panel shrinks to 240px |
| Tablet | 1024px | Community Panel collapses (icons only) |
| Mobile | ≤ 768px | Not supported (minimum 1024px recommended) |

---

## 8. Accessibility

| Item | Rule |
|------|------|
| Color contrast | WCAG 2.1 AA or better (4.5:1 text, 3:1 icons) |
| Color-blind friendly graph | Community distinction uses color AND shape (size/pattern) |
| Keyboard navigation | Tab cycles through Control Bar buttons |
| Screen reader | `aria-label` mandatory (the graph area also exposes a summary text) |
| Reduced motion | `prefers-reduced-motion` media query disables glow/pulse animations |

---

## 9. Pencil → Code Sync Workflow

### Automatic detection (Hook configured)

```
Designer edits Pencil
    │
    ▼  mcp__pencil__batch_design call
PostToolUse Hook fires
    │
    ▼  "Pencil design changed" notification
Claude reads the affected Frame (batch_get + get_screenshot)
    │
    ▼
docs/spec/ui/UI_XX_*.md updated
    │
    ▼  SPEC change detection Hook
Test scaffold regeneration prompt
```

### Manual sync command

```
1. Edit in Pencil
2. Tell Claude: "Update UI_01 SPEC"
3. Claude: batch_get(FuHqi) + get_screenshot(FuHqi) → refresh SPEC
```

---

## 10. Implementation Tech Mapping

| Design element | Implementation tech | Location |
|----------------|--------------------|----|
| shadcn components | shadcn/ui + Tailwind CSS | `frontend/src/components/ui/` |
| Graph engine | Cytoscape.js (WebGL renderer) | `frontend/src/components/graph/` |
| Charts/Timeline | Recharts | `frontend/src/components/timeline/` |
| State management | Zustand | `frontend/src/store/` |
| Real-time updates | WebSocket | `frontend/src/hooks/useSimulationSocket.ts` |
| Design tokens | CSS Variables (Tailwind config) | `frontend/src/index.css` |
| Routing | React Router v6 | `frontend/src/App.tsx` |

### React Component ↔ Pencil Frame Mapping

| React component | Pencil Frame | UI SPEC |
|----------------|-------------|---------|
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

## 11. SPEC Document Index

| Document | Type | Path |
|----------|------|------|
| **DESIGN.md** (this file) | Design master | `DESIGN.md` |
| UI_01 Simulation Main | Screen SPEC | `docs/spec/ui/UI_01_SIMULATION_MAIN.md` |
| UI_02 Communities Detail | Screen SPEC | `docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md` |
| UI_03 Top Influencers | Screen SPEC | `docs/spec/ui/UI_03_TOP_INFLUENCERS.md` |
| UI_04 Agent Detail | Screen SPEC | `docs/spec/ui/UI_04_AGENT_DETAIL.md` |
| UI_05 Global Metrics | Screen SPEC | `docs/spec/ui/UI_05_GLOBAL_METRICS.md` |
| UI_06 Projects List | Screen SPEC | `docs/spec/ui/UI_06_PROJECTS_LIST.md` |
| UI_07 Project Scenarios | Screen SPEC | `docs/spec/ui/UI_07_PROJECT_SCENARIOS.md` |
| UI_08 Influencers Pagination | Screen SPEC | `docs/spec/ui/UI_08_INFLUENCERS_PAGINATION.md` |
| UI_09 Influencers Filter | Screen SPEC | `docs/spec/ui/UI_09_INFLUENCERS_FILTER.md` |
| UI_10 Agent Intervene | Screen SPEC | `docs/spec/ui/UI_10_AGENT_INTERVENE.md` |
| UI_11 Agent Connections | Screen SPEC | `docs/spec/ui/UI_11_AGENT_CONNECTIONS.md` |
| Frontend SPEC | Tech SPEC | `docs/spec/07_FRONTEND_SPEC.md` |
| API SPEC | Data contract | `docs/spec/06_API_SPEC.md` |
