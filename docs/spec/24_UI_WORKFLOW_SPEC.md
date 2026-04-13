# 24_UI_WORKFLOW_SPEC.md — 6-Stage UI Workflow Components

> Version: 0.1.0
> Created: 2026-04-11
> Status: APPROVED
> SPEC-GATE retroactive coverage for components added during the UX audit round.

---

## 1. Overview

Prophet's user journey consists of 6 stages (Generate → Inject → Simulate → Detect →
Visualize → Decide), but up to previous rounds the UI expressed this workflow
only **implicitly**. Users had to infer directly from the screen what each stage was,
where to start, and what had completed.

This SPEC defines the contracts for 6 new UI components to **explicitly visualize**
the 6-stage workflow.

### 1.1 Motivation

| Stage | Previous UX Problem | Introduced Component |
|------|------------|--------------|
| All stages | Progress/next action unclear | **WorkflowStepper** |
| 1. Generate | Required fields/minimum path unclear | **FormProgressBanner** |
| 2/3. Inject/Simulate | (existing ControlPanel maintained) | — |
| 4. Detect | Toast evaporates after 5s, no history | **EmergentEventsPanel** (+ TimelinePanel markers) |
| 5. Visualize | No legend, zoom tier opaque | **GraphLegend**, **ZoomTierBadge** |
| 6. Decide | No entry point for Compare/MC/Export | **DecidePanel** |

### 1.2 SPEC-GATE Compliance

This document was written to **retroactively** satisfy the SPEC-GATE rules from CLAUDE.md.
Ideally this SPEC should have existed before writing code, but the UX improvement work
proceeded without SPEC-first. **All future UI components must add a section to this SPEC before implementation.**

---

## 2. Component Contracts

### 2.1 WorkflowStepper

**File**: `frontend/src/components/layout/WorkflowStepper.tsx`
**Util**: `frontend/src/components/layout/workflowStepperUtils.ts`

6-stage progress indicator. Fixed at the top of SimulationPage.

#### 2.1.1 Stage States (WF-01)

```ts
type StageState = "pending" | "active" | "completed";

interface WorkflowStage {
  id: "generate" | "inject" | "simulate" | "detect" | "visualize" | "decide";
  label: string;
  description: string;
  state: StageState;
}
```

#### 2.1.2 Pure Derivation (WF-02)

`deriveWorkflowStages(input)` determines the state of 6 stages from simulation status + emergent count + steps count. Pure function — no side effects.

| Condition | Generate | Inject | Simulate | Detect | Visualize | Decide |
|------|----------|--------|----------|--------|-----------|--------|
| No simulation | **active** | pending | pending | pending | pending | pending |
| `configured` | completed | **active** | pending | pending | pending | pending |
| `running` + steps > 0 | completed | completed | **active** | pending | **active** | pending |
| `running` + emergent > 0 | completed | completed | **active** | **active** | **active** | pending |
| `paused` | completed | **active** | **active** | (event) | **active** | pending |
| `completed` / `failed` | completed | completed | completed | (event) | completed | **active** |

#### 2.1.3 Acceptance Criteria (WF-AC-01 ~ WF-AC-07)

| ID | Criterion | Test |
|----|------|--------|
| WF-AC-01 | Generate = active, rest = pending when no simulation | `test_highlights_generate` |
| WF-AC-02 | Inject active, Generate completed in `configured` state | `test_marks_generate_completed` |
| WF-AC-03 | Simulate + Visualize active when `running` + steps > 0 | `test_marks_simulate_visualize` |
| WF-AC-04 | Detect active when `emergentCount > 0` | `test_activates_detect` |
| WF-AC-05 | Both Inject + Simulate active when `paused` | `test_paused_dual_active` |
| WF-AC-06 | Decide active, rest completed when `completed` | `test_terminal_decide_active` |
| WF-AC-07 | `failed` also activates Decide same as `completed` | `test_failed_decide_active` |

Test file: `frontend/src/__tests__/WorkflowStepper.test.tsx` (9 tests)

---

### 2.2 EmergentEventsPanel

**File**: `frontend/src/components/emergent/EmergentEventsPanel.tsx`
**Util**: `frontend/src/components/emergent/emergentEventsUtils.ts`

Permanent record panel for Step 4 "Detect". The only UI where users can review event history even after toasts have evaporated.

#### 2.2.1 Event Types (EE-01)

5 emergent event types:
- `viral_cascade` — rapid message spread
- `polarization` — group polarization
- `echo_chamber` — opinion self-reinforcement
- `collapse` — sudden drop in adoption rate
- `slow_adoption` — expected diffusion failure

Each type is mapped to `EVENT_TYPE_META` with icon + color + description.

#### 2.2.2 Pure Helpers (EE-02)

- `severityToWidth(severity)` — clamp to `[0, 1]` then percentage string
- `filterAndSortEvents(events, filter)` — sort by step descending + type filter

#### 2.2.3 Acceptance Criteria (EE-AC-01 ~ EE-AC-06)

| ID | Criterion | Test |
|----|------|--------|
| EE-AC-01 | Empty state + guidance text when 0 events | `test_empty_state` |
| EE-AC-02 | Event list sorted by step descending | `test_sorts_by_step_desc` |
| EE-AC-03 | Only shows matching type when filter button clicked | `test_filters_by_type` |
| EE-AC-04 | severity bar has ARIA progressbar attribute | `test_severity_aria` |
| EE-AC-05 | `severity > 1` clamp → 100% width | `test_clamps_severity` |
| EE-AC-06 | `N detected` count badge in header | `test_header_count` |

Test file: `frontend/src/__tests__/EmergentEventsPanel.test.tsx` (11 tests)

#### 2.2.4 Timeline Marker Integration (EE-03)

`TimelinePanel.tsx` overlays emergent events within the most recent 100-step window as **vertical amber markers**. Each marker:
- Absolutely positioned with `leftPct` calculated from the corresponding step position
- `title` attribute displays "event type · Step N"
- Selectable in tests via `data-testid="timeline-event-marker-{step}"`

Duplicate events at the same step show only the first as a marker (color stability).

#### 2.2.5 Layout & Dimensions (EE-04)

> **Revision history**: 2026-04-13 — resolved issue of panel being too narrow (280px) and zone 3 too low (240px), showing only ~3 rows simultaneously.

| Item | Previous | Current | Location |
|------|------|------|------|
| Bottom area height | 240px | **300px** | `--bottom-area-height` (`index.css`) |
| Panel width | 280px (inline) | **360px** | `--emergent-panel-width` (`index.css`) |
| Breakpoint (display start) | `lg` (1024px+) | **`md` (768px+)** | `SimulationPage.tsx` |
| Row vertical padding | `py-2` | **`py-2.5`** | `EmergentEventsPanel.tsx` `EventRow` |
| Event label font | `text-xs` (12px) | **`text-sm` (14px)** | same |
| Description font | `text-[11px]` + `truncate` | **`text-xs` (12px) + `line-clamp-2`** | same |
| Step / severity font | `text-[10px]` | **`text-[11px]`** | same |
| Severity bar thickness | `h-1` (4px) | **`h-1.5` (6px)** | same |

Visible row count: 3 → **approximately 6** (228px available height ÷ ~38px row).

Acceptance criteria:

| ID | Criterion | Note |
|----|------|------|
| EE-AC-07 | `--emergent-panel-width` token defined in `index.css` | inline magic-number prohibited |
| EE-AC-08 | Panel container in `SimulationPage` displayed from `md:flex` (≥768px) | regression to `lg:flex` prohibited |
| EE-AC-09 | Description text exposed up to 2 lines via `line-clamp-2` | regression to `truncate` causes important context loss |

Existing EE-AC-01 ~ EE-AC-06 (filter / sort / severity / count badge) remain
valid, and since this revision only changes visual representation, the 11 unit tests pass unchanged.

---

### 2.3 DecidePanel

**File**: `frontend/src/components/decide/DecidePanel.tsx`

Integrated entry point for Step 6 "Decide". Opens as a modal with 3 tabs.

#### 2.3.1 Tabs (DP-01)

| Tab | Function | Backend Endpoint |
|-----|------|------------------|
| Compare | Select another simulation → navigate to `/simulation/:id/compare/:other` | `GET /simulations` (list) |
| Monte Carlo | N-runs slider (5~50) + run button | `POST /simulations/:id/run-all` (temporary; full MC is follow-up) |
| Export | Select JSON/CSV format → trigger download | `GET /simulations/:id/export?format=...` |

#### 2.3.2 Data Flow (DP-02)

Component consumes **hooks only** — direct `apiClient` import prohibited.

```ts
import {
  useSimulations,         // Compare tab drop-down data
  useRunAllSimulation,    // MC tab mutation
  useExportSimulation,    // Export tab trigger
} from "../../api/queries";
```

This contract is automatically verified in `ArchitectureInvariants.test.ts#1`.

#### 2.3.3 Acceptance Criteria (DP-AC-01 ~ DP-AC-06)

| ID | Criterion | Test |
|----|------|--------|
| DP-AC-01 | All 3 tabs render | `test_renders_all_tabs` |
| DP-AC-02 | Default tab is Compare | `test_defaults_to_compare` |
| DP-AC-03 | Slider + Run button displayed when switching to Monte Carlo tab | `test_switches_to_mc` |
| DP-AC-04 | Triggered with that format when CSV selected in Export tab | `test_export_csv` |
| DP-AC-05 | Export default is JSON | `test_export_default_json` |
| DP-AC-06 | Compare submit is disabled until another sim is selected | `test_compare_disabled_until_select` |
| DP-AC-07 | Compare submit → navigate to `/simulation/:simulationId/compare/:otherId` route (route must be registered in App.tsx) | `test_compare_navigates_to_both_id_route` |
| DP-AC-08 | Legacy route `/compare/:otherId` also maintained (bookmark/share link compatibility) | `test_legacy_compare_route_still_resolves` |

Test file: `frontend/src/__tests__/DecidePanel.test.tsx` (7+ tests)

#### 2.3.4 Route Contract (DP-03) — added 2026-04-13

ComparisonPage supports both entry paths:

| URL | simulationId Source | Purpose |
|-----|------------------|------|
| `/simulation/:simulationId/compare/:otherId` | **URL params** (recommended, shareable) | Navigation from DecidePanel → Compare tab |
| `/compare/:otherId` | Zustand `simulation` store (fallback) | Existing bookmarks / old link compatibility |

Implementation: first try `simulationId` via `useParams` → if not found, fall back to active simulation ID from store. If both missing, show "No active simulation" error banner.

**Issue history (2026-04-13)**: Previously App.tsx only registered `/compare/:otherId`, causing DecidePanel's "Compare →" button to **silently fail** (URL did not change, only modal closed). This was a regression where the route defined in SPEC 2.3.1 did not match the registered route.

---

### 2.4 GraphLegend

**File**: `frontend/src/components/graph/GraphLegend.tsx`

Color guide overlay for the 3D graph. Fixed at bottom-left, collapsible/expandable.

#### 2.4.1 Sections (GL-01)

1. **Communities** — 5 communities from `COMMUNITIES` constant + color swatches
2. **Node state** — Adopted (green glow) / Dimmed / Default
3. **Edges** — Intra-community / Inter-community / Bridge

#### 2.4.2 Acceptance Criteria (GL-AC-01 ~ GL-AC-03)

| ID | Criterion | Test |
|----|------|--------|
| GL-AC-01 | All communities displayed in legend | `test_renders_communities` |
| GL-AC-02 | Content area hidden + `aria-expanded=false` when toggle clicked | `test_collapses` |
| GL-AC-03 | Re-expands on second click | `test_reopens` |

Test file: `frontend/src/__tests__/GraphLegendZoomBadge.test.tsx` (3 legend tests)

---

### 2.5 ZoomTierBadge

**File**: `frontend/src/components/graph/ZoomTierBadge.tsx`

Real-time LOD (Level-of-Detail) tier display. Fixed at top-right.

#### 2.5.1 Tiers (ZT-01)

| Tier | Label | Particle Density (TIER_LIMITS) |
|------|--------|---------------------------|
| `closeup` | "Close-up" | 50 |
| `midrange` | "Mid-range" | 30 |
| `overview` | "Overview" | 5 |

Tier is calculated in `GraphPanel`'s `propagationAnimEnabled` effect and passed as a prop. This SPEC's component is **pure display** — it does not own tier change logic.

#### 2.5.2 Acceptance Criteria (ZT-AC-01 ~ ZT-AC-04)

| ID | Criterion | Test |
|----|------|--------|
| ZT-AC-01 | "Close-up" label displayed in `closeup` tier | `test_closeup_label` |
| ZT-AC-02 | "Mid-range" label in `midrange` tier | `test_midrange_label` |
| ZT-AC-03 | "Overview" label in `overview` tier | `test_overview_label` |
| ZT-AC-04 | `data-tier` attribute immediately reflects tier prop change | `test_data_tier_updates` |

Test file: `frontend/src/__tests__/GraphLegendZoomBadge.test.tsx` (4 badge tests)

---

### 2.6 FormProgressBanner

**File**: `frontend/src/components/campaign/FormProgressBanner.tsx`

Required field progress + Quick Start toggle for CampaignSetupPage.

#### 2.6.1 Required Fields (FP-01)

4 required fields specified by CampaignSetupPage:
1. Project (`selectedProjectId` non-empty)
2. Campaign name (`name.trim().length > 0`)
3. Message (`message.trim().length > 0`)
4. Channel (`channels.size > 0`)

#### 2.6.2 Quick Start Mode (FP-02)

When Quick Start toggle is ON, the following sections are **hidden**:
- CampaignAttributesSection
- CommunityConfigurationSection
- AdvancedSettingsSection

Users can submit immediately after filling in only the 4 required fields.

#### 2.6.3 Progress Bar (FP-03)

- Width `= completed / total * 100%`
- `role="progressbar"` + `aria-valuenow/min/max`
- On completion (`completed === total`) emerald check + "All required fields completed"

#### 2.6.4 Acceptance Criteria (FP-AC-01 ~ FP-AC-06)

| ID | Criterion | Test |
|----|------|--------|
| FP-AC-01 | 0 fields filled: "0 / N required fields" | `test_zero_state` |
| FP-AC-02 | Missing field list displayed, filled fields excluded | `test_missing_list` |
| FP-AC-03 | At 100%, `form-progress-complete` shown + missing list hidden | `test_complete_state` |
| FP-AC-04 | toggle callback called when Quick Start button clicked | `test_quick_start_toggle` |
| FP-AC-05 | `aria-pressed=true` when Quick Start = true | `test_aria_pressed` |
| FP-AC-06 | `aria-valuenow` shows accurate percentage | `test_aria_valuenow` |

Test file: `frontend/src/__tests__/FormProgressBanner.test.tsx` (6 tests)

---

## 3. Architectural Constraints

### 3.1 Pure Helper Separation (UW-CON-01)

Component files (`*.tsx`) must **export only components**. Pure utilities /
constants / types are separated into sibling files (`*Utils.ts`).

| Component | Utils File |
|---------|----------|
| `WorkflowStepper.tsx` | `workflowStepperUtils.ts` |
| `EmergentEventsPanel.tsx` | `emergentEventsUtils.ts` |
| `GraphPanel.tsx` | `propagationAnimationUtils.ts` (existing) |

Verification: `ArchitectureInvariants.test.ts` **#8** (component files export only components).

### 3.2 a11y Requirements (UW-CON-02)

All new components must have the following a11y attributes:

- `role="progressbar"` — FormProgressBanner, EmergentEventsPanel severity bar
- `role="dialog" aria-modal="true"` — DecidePanel
- `aria-expanded` — GraphLegend toggle
- `aria-pressed` — DecidePanel tab, Quick Start button, filter pills
- `aria-label` — all overlay sections
- `data-testid` — all interactive elements

### 3.3 SIM_STATUS Import Discipline (UW-CON-03)

Components must not hardcode domain status literals (`"running"`, `"completed"`, etc.).
Import and use `SIM_STATUS`, `TERMINAL_SIM_STATUSES`, `STARTABLE_SIM_STATUSES` from `@/config/constants`.

Verification: `ArchitectureInvariants.test.ts` **#5**.

### 3.4 API Layer Gate (UW-CON-04)

Components do not runtime-import `apiClient`. Use only TanStack Query
hooks (`api/queries.ts`). If the needed mutation/query does not exist,
add the hook first, then consume it in the component.

Verification: `ArchitectureInvariants.test.ts` **#1**, **#2**.

---

## 4. SPEC-to-Test Traceability

| Component | Test File | Test Count |
|---------|-----------|-----------|
| WorkflowStepper | `WorkflowStepper.test.tsx` | 9 |
| EmergentEventsPanel | `EmergentEventsPanel.test.tsx` | 11 |
| DecidePanel | `DecidePanel.test.tsx` | 6 |
| GraphLegend + ZoomTierBadge | `GraphLegendZoomBadge.test.tsx` | 7 |
| FormProgressBanner | `FormProgressBanner.test.tsx` | 6 |
| Architectural invariants | `ArchitectureInvariants.test.ts` | 8 |
| **Total** | | **47** |

---

## 5. Change Log

| Version | Date | Changes |
|---------|------|---------|
| 0.1.0 | 2026-04-11 | Initial retroactive SPEC for 6 UI components + architectural invariants |

---

## 6. Follow-ups

1. Remove community hex hardcoding in existing components (ArchitectureInvariants `COMMUNITY_HEX_BASELINE` ratchet)
2. Migrate `components/control/hooks/*` to TanStack Query hooks (`COMPONENTS_APICLIENT_BASELINE` ratchet)
3. Full Monte Carlo sweep backend endpoint (`POST /simulations/:id/monte-carlo`) — DecidePanel currently falls back to `run-all`
