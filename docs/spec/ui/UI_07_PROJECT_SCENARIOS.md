# UI-07 — Project Scenarios SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Project Scenarios (ID: d4eOq)

---

## 1. Overview

The Project Scenarios screen is the detail view for a single project. It displays the project header with metadata, and a list of scenario cards within the project. Users can create new scenarios, run/stop existing ones, view results, and manage scenario lifecycle. This screen is reached by opening a project from the Projects List (UI-06).

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| +---------+----------------------------------------------------------+ |
| | Sidebar | Main Content                                             | |
| | 256px   |                                                          | |
| | [SvySF] | Breadcrumb: Projects > Korea Election 2026 Simulation    | |
| |         |                                                          | |
| | [Nav]   | Project Header                                          | |
| | Projects| "Korea Election 2026 Simulation" + description            | |
| | Simulat.| [Settings] ghost btn        [+ New Scenario] primary btn | |
| | Global  |                                                          | |
| | Insights| Project Info Bar                          [tiaJz]        | |
| | Settings| Status:Active | Scenarios:4 | Agents:10K | Created | Run| |
| |         |                                                          | |
| |         | "Scenarios" section title                                | |
| |         |                                                          | |
| |         | Scenario Cards                            [xKdnD]        | |
| |         | +------------------------------------------------------+| |
| |         | | Scenario 1: name + status + description              || |
| |         | | Agents: 2500 | Tier 1: 2000 | Tier 2: 400 | Tier 3: 100|
| |         | | Run time: 2h 15m    [Results] [Run/Stop] [More ...]  || |
| |         | +------------------------------------------------------+| |
| |         | | Scenario 2 ...                                       || |
| |         | +------------------------------------------------------+| |
| |         | | Scenario N ...                                       || |
| |         | +------------------------------------------------------+| |
| +---------+----------------------------------------------------------+ |
+------------------------------------------------------------------------+
```

---

## 3. Components

### App Sidebar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `SvySF` | `Sidebar` (flex col) | App sidebar container, width 256px, border-right, bg=card (shared with UI-06) | `d4eOq` |
| `SvySF/logo` | `div` (flex row) | Logo group: brain icon + "MCASP Prophet" text | `SvySF` |
| `SvySF/navProjects` | `div` (flex row) | Navigation item: FolderOpen icon + "Projects" label, active state | `SvySF` |
| `SvySF/navSimulation` | `div` (flex row) | Navigation item: Play icon + "Simulation" label | `SvySF` |
| `SvySF/navGlobalInsights` | `div` (flex row) | Navigation item: BarChart3 icon + "Global Insights" label | `SvySF` |
| `SvySF/navSettings` | `div` (flex row) | Navigation item: Settings icon + "Settings" label | `SvySF` |

### Main Content Header

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `d4eOq/breadcrumb` | `Breadcrumb` | "Projects > Korea Election 2026 Simulation" with clickable "Projects" link back to UI-06 | `d4eOq` |
| `d4eOq/header` | `div` (flex row) | Project header: title group (left) + action buttons (right), space-between | `d4eOq` |
| `d4eOq/header/title` | `h1` | Project name heading (e.g., "Korea Election 2026 Simulation") | `d4eOq/header` |
| `d4eOq/header/description` | `p` | Project description text, muted-foreground | `d4eOq/header` |
| `d4eOq/header/settingsBtn` | `Button` | "Settings" button, variant=ghost, icon=Settings | `d4eOq/header` |
| `d4eOq/header/newScenarioBtn` | `Button` | "+ New Scenario" button, variant=default (primary), icon=Plus | `d4eOq/header` |

### Project Info Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `tiaJz` | `div` (flex row) | Project info bar, horizontal row of metadata items with dividers, bg=muted, rounded, padding 12px 20px | `d4eOq` |
| `tiaJz/status` | `Badge` | Project status badge: "Active" (green) | `tiaJz` |
| `tiaJz/scenarios` | `div` | "Scenarios" label + count value "4", font-semibold | `tiaJz` |
| `tiaJz/agents` | `div` | "Total Agents" label + count value "10,000", font-semibold | `tiaJz` |
| `tiaJz/created` | `div` | "Created" label + date value (e.g., "Mar 15, 2026") | `tiaJz` |
| `tiaJz/lastRun` | `div` | "Last Run" label + date value (e.g., "Mar 27, 2026") | `tiaJz` |

### Scenario Cards

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `xKdnD` | `div` (flex col) | Vertical list of scenario cards, gap 16px | `d4eOq` |
| `xKdnD/sectionTitle` | `h2` | "Scenarios" section heading | `d4eOq` |
| `xKdnD/card` | `Card` (repeated) | Individual scenario card, border, padding 20px | `xKdnD` |
| `xKdnD/card/header` | `div` (flex row) | Card header: scenario name + status badge, space-between | `xKdnD/card` |
| `xKdnD/card/name` | `h3` | Scenario name, font-semibold | `xKdnD/card/header` |
| `xKdnD/card/statusBadge` | `Badge` | Scenario status: "Completed" (green), "Running" (blue, animated), "Draft" (gray) | `xKdnD/card/header` |
| `xKdnD/card/description` | `p` | Scenario description text, muted-foreground | `xKdnD/card` |
| `xKdnD/card/metadata` | `div` (flex row) | Metadata row: agent count, tier distribution, run time | `xKdnD/card` |
| `xKdnD/card/metaAgents` | `span` | "Agents: {n}" with Users icon | `xKdnD/card/metadata` |
| `xKdnD/card/metaTier1` | `span` | "Tier 1: {n}" count label | `xKdnD/card/metadata` |
| `xKdnD/card/metaTier2` | `span` | "Tier 2: {n}" count label | `xKdnD/card/metadata` |
| `xKdnD/card/metaTier3` | `span` | "Tier 3: {n}" count label | `xKdnD/card/metadata` |
| `xKdnD/card/metaRunTime` | `span` | "Run time: {duration}" with Clock icon | `xKdnD/card/metadata` |
| `xKdnD/card/actions` | `div` (flex row) | Action buttons row, right-aligned | `xKdnD/card` |
| `xKdnD/card/resultsBtn` | `Button` | "Results" button, variant=outline, visible when status=Completed | `xKdnD/card/actions` |
| `xKdnD/card/runBtn` | `Button` | "Run" button, variant=default (primary), icon=Play. Becomes "Stop" (destructive, icon=Square) when Running | `xKdnD/card/actions` |
| `xKdnD/card/moreBtn` | `Button` | "More" dropdown button, variant=ghost, icon=MoreHorizontal. Opens dropdown: Edit, Duplicate, Delete | `xKdnD/card/actions` |

---

## 4. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `var(--background)` | Page background |
| `--bg-sidebar` | `var(--card)` | Sidebar background |
| `--bg-card` | `var(--card)` | Scenario card background |
| `--bg-info-bar` | `var(--muted)` | Project info bar background |
| `--status-active` | `#22c55e` | "Active" / "Completed" status badge |
| `--status-running` | `#3b82f6` | "Running" status badge |
| `--status-draft` | `#94a3b8` | "Draft" status badge |
| `--status-running-pulse` | `#3b82f680` | Running badge pulsing animation |
| `--destructive` | `var(--destructive)` | Stop button color |
| `--tier-1` | `#94a3b8` | Tier 1 indicator |
| `--tier-2` | `#f59e0b` | Tier 2 indicator |
| `--tier-3` | `#a855f7` | Tier 3 indicator |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page title | Inter / system | 24px | 700 |
| Page description | Inter / system | 14px | 400 |
| Section heading | Inter / system | 18px | 600 |
| Scenario name | Inter / system | 16px | 600 |
| Scenario description | Inter / system | 14px | 400 |
| Metadata labels | Inter / system | 12px | 400 |
| Metadata values | Inter / system | 12px | 600 |
| Info bar labels | Inter / system | 12px | 400 |
| Info bar values | Inter / system | 14px | 600 |
| Breadcrumb text | Inter / system | 14px | 400 |

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--sidebar-width` | `256px` | Left sidebar width |
| `--main-padding` | `32px` | Main content padding |
| `--card-padding` | `20px` | Scenario card inner padding |
| `--card-gap` | `16px` | Gap between scenario cards |
| `--info-bar-padding` | `12px 20px` | Info bar inner padding |
| `--info-bar-gap` | `24px` | Gap between info bar items |
| `--header-bottom-margin` | `24px` | Space below project header |
| `--section-title-margin` | `16px` | Space below "Scenarios" title |

---

## 5. Interaction Behavior

| Action | Trigger | Effect |
|--------|---------|--------|
| Navigate back | Click "Projects" in breadcrumb | Returns to Projects List (UI-06). |
| New scenario | Click "+ New Scenario" button | Opens scenario creation dialog/form. POST /projects/{id}/scenarios on submit. |
| Project settings | Click "Settings" ghost button | Opens project settings dialog/page for editing project name, description, configuration. |
| Run scenario | Click "Run" button on a Draft/Completed scenario | POST /projects/{id}/scenarios/{scenarioId}/run. Button changes to "Stop" (red). Status badge transitions to "Running" with pulse animation. |
| Stop scenario | Click "Stop" button on a Running scenario | POST /projects/{id}/scenarios/{scenarioId}/stop. Confirmation dialog shown first. Status reverts. Button changes back to "Run". |
| View results | Click "Results" button on a Completed scenario | Navigates to simulation results view (UI-01 in replay mode) for that scenario. |
| More dropdown | Click "More" button | Opens dropdown menu with: Edit, Duplicate, Delete options. |
| Delete scenario | Click "Delete" from More dropdown | Confirmation dialog. DELETE /projects/{id}/scenarios/{scenarioId}. Card removed with fade-out animation. |
| Duplicate scenario | Click "Duplicate" from More dropdown | POST /projects/{id}/scenarios/{scenarioId}/duplicate. New card appears with "Draft" status. |
| Page load | On mount | Fetches project detail + scenarios from API. Shows loading skeletons while fetching. |
| Real-time status | WebSocket push | Running scenario status updates in real-time. Run time counter ticks while running. |

---

## 6. Data Binding (Backend API)

| Component | API Endpoint | Method | Payload / Response |
|-----------|-------------|--------|-------------------|
| Project detail | `GET /projects/{id}` | GET | `{ id, name, description, status, scenario_count, total_agents, created_at, last_run }` |
| Scenario list | `GET /projects/{id}/scenarios` | GET | `{ items: [{ id, name, description, status, agent_count, tier_distribution: { tier1, tier2, tier3 }, run_time, created_at }], total }` |
| Create scenario | `POST /projects/{id}/scenarios` | POST | `{ name, description, config }` -> `{ id, name, status: "Draft" }` |
| Run scenario | `POST /projects/{id}/scenarios/{scenarioId}/run` | POST | `{}` -> `{ success, simulation_id }` |
| Stop scenario | `POST /projects/{id}/scenarios/{scenarioId}/stop` | POST | `{}` -> `{ success }` |
| Delete scenario | `DELETE /projects/{id}/scenarios/{scenarioId}` | DELETE | `{}` -> `{ success }` |
| Duplicate scenario | `POST /projects/{id}/scenarios/{scenarioId}/duplicate` | POST | `{}` -> `{ id, name, status: "Draft" }` |
| Real-time updates | `WS /projects/{id}/ws` | WebSocket | Scenario status and run time updates |

---

## 7. Pencil Node Reference

| Node ID | Element | Section |
|---------|---------|---------|
| `d4eOq` | Root frame (1440x900) | -- |
| `SvySF` | App Sidebar (256px, shared) | Left |
| `tiaJz` | Project Info Bar | Header area |
| `xKdnD` | Scenario Cards list | Main content |
