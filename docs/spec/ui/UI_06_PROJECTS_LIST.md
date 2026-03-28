# UI-06 — Projects List SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Projects List (ID: 2Efo9)

---

## 1. Overview

The Projects List screen is the top-level project management dashboard of Prophet MCASP. It serves as the landing page after login, displaying all simulation projects the user has created or has access to. Each project card shows key metadata including scenario count, total agents, last run date, and status. Users can create new projects or open existing ones to manage their scenarios.

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| +---------+----------------------------------------------------------+ |
| | Sidebar | Main Content                               [CwLyz]      | |
| | 256px   |                                                          | |
| | [SvySF] | Header Row                                              | |
| |         | "Projects" title + description                           | |
| | [Nav]   | [+ New Project] button          [Avatar]                | |
| | Projects|                                                          | |
| | Simulat.|----------------------------------------------------------| |
| | Global  | Project Cards Grid                        [Zlbn9]        | |
| | Insights|                                                          | |
| | Settings| +------------------------------------------------------+| |
| |         | | Project Card 1                                       || |
| |         | | Name (link) + Description                            || |
| |         | | Scenarios: 4 | Agents: 10K | Last Run | Status Badge || |
| |         | | [Open] button                                        || |
| |         | +------------------------------------------------------+| |
| |         | | Project Card 2                                       || |
| |         | | ...                                                  || |
| |         | +------------------------------------------------------+| |
| |         | | Project Card N                                       || |
| |         | | ...                                                  || |
| |         | +------------------------------------------------------+| |
| +---------+----------------------------------------------------------+ |
+------------------------------------------------------------------------+
```

---

## 3. Components

### App Sidebar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `SvySF` | `Sidebar` (flex col) | App sidebar container, width 256px, border-right, bg=card | `2Efo9` |
| `SvySF/logo` | `div` (flex row) | Logo group: brain icon + "MCASP Prophet" text | `SvySF` |
| `SvySF/navProjects` | `div` (flex row) | Navigation item: FolderOpen icon + "Projects" label, active state (highlighted bg) | `SvySF` |
| `SvySF/navSimulation` | `div` (flex row) | Navigation item: Play icon + "Simulation" label | `SvySF` |
| `SvySF/navGlobalInsights` | `div` (flex row) | Navigation item: BarChart3 icon + "Global Insights" label | `SvySF` |
| `SvySF/navSettings` | `div` (flex row) | Navigation item: Settings icon + "Settings" label | `SvySF` |

### Main Content

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `CwLyz` | `div` (flex col) | Main content area, padding 32px, flex=1 | `2Efo9` |
| `CwLyz/header` | `div` (flex row) | Header row: title group (left) + actions (right), space-between | `CwLyz` |
| `CwLyz/header/title` | `h1` | "Projects" page title | `CwLyz/header` |
| `CwLyz/header/description` | `p` | Descriptive subtitle text, muted-foreground | `CwLyz/header` |
| `CwLyz/header/newProjectBtn` | `Button` | "+ New Project" button, variant=default (primary), icon=Plus | `CwLyz/header` |
| `CwLyz/header/avatar` | `Avatar` | Current user avatar, top-right | `CwLyz/header` |

### Project Cards Grid

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `Zlbn9` | `div` (flex col) | Vertical list of project cards, gap 16px | `CwLyz` |
| `Zlbn9/card` | `Card` (repeated) | Individual project card, border, padding 20px, hover shadow | `Zlbn9` |
| `Zlbn9/card/name` | `a` (link) | Project name, font-semibold, clickable link to project detail (UI-07) | `Zlbn9/card` |
| `Zlbn9/card/description` | `p` | Project description text, muted-foreground, line-clamp-2 | `Zlbn9/card` |
| `Zlbn9/card/metadata` | `div` (flex row) | Metadata row: scenario count, total agents, last run date, status badge | `Zlbn9/card` |
| `Zlbn9/card/metaScenarios` | `span` | "Scenarios: {n}" with Layers icon | `Zlbn9/card/metadata` |
| `Zlbn9/card/metaAgents` | `span` | "Total Agents: {n}" with Users icon | `Zlbn9/card/metadata` |
| `Zlbn9/card/metaLastRun` | `span` | "Last Run: {date}" with Clock icon | `Zlbn9/card/metadata` |
| `Zlbn9/card/statusBadge` | `Badge` | Status badge: "Active" (green), "Draft" (gray), "In-progress" (blue) | `Zlbn9/card/metadata` |
| `Zlbn9/card/openBtn` | `Button` | "Open" button, variant=outline | `Zlbn9/card` |

---

## 4. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `var(--background)` | Page background |
| `--bg-sidebar` | `var(--card)` | Sidebar background |
| `--bg-card` | `var(--card)` | Project card background |
| `--sidebar-active-bg` | `var(--accent)` | Active navigation item background |
| `--sidebar-active-text` | `var(--accent-foreground)` | Active navigation item text |
| `--sidebar-muted-text` | `var(--muted-foreground)` | Inactive navigation item text |
| `--status-active` | `#22c55e` | "Active" status badge |
| `--status-draft` | `#94a3b8` | "Draft" status badge |
| `--status-in-progress` | `#3b82f6` | "In-progress" status badge |
| `--card-hover-shadow` | `0 2px 8px rgba(0,0,0,0.08)` | Card hover elevation |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page title | Inter / system | 24px | 700 |
| Page description | Inter / system | 14px | 400 |
| Project name | Inter / system | 16px | 600 |
| Project description | Inter / system | 14px | 400 |
| Metadata labels | Inter / system | 12px | 400 |
| Status badge text | Inter / system | 12px | 500 |
| Sidebar nav item | Inter / system | 14px | 500 |
| Sidebar logo text | Inter / system | 16px | 700 |

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--sidebar-width` | `256px` | Left sidebar width |
| `--main-padding` | `32px` | Main content padding |
| `--card-padding` | `20px` | Project card inner padding |
| `--card-gap` | `16px` | Gap between project cards |
| `--metadata-gap` | `16px` | Gap between metadata items |
| `--header-gap` | `8px` | Gap between title and description |
| `--sidebar-item-height` | `40px` | Navigation item height |
| `--sidebar-item-padding` | `12px 16px` | Navigation item padding |

---

## 5. Interaction Behavior

| Action | Trigger | Effect |
|--------|---------|--------|
| New project | Click "+ New Project" button | Opens create project dialog/navigates to project creation form. POST /projects on submit. |
| Open project | Click "Open" button or project name link | Navigates to Project Scenarios screen (UI-07) for that project. |
| Card hover | Hover on project card | Card elevates with subtle shadow transition. |
| Sidebar navigation | Click sidebar nav item | Navigates to corresponding screen. Active item gets highlighted background. |
| Status badge | Read-only | Displays project status: Active (green), Draft (gray), In-progress (blue). |
| Page load | On mount | Fetches project list from GET /projects. Shows loading skeletons while fetching. |
| Empty state | No projects exist | Shows empty state illustration with "Create your first project" CTA. |

---

## 6. Data Binding (Backend API)

| Component | API Endpoint | Method | Payload / Response |
|-----------|-------------|--------|-------------------|
| Project list | `GET /projects` | GET | `{ items: [{ id, name, description, scenario_count, total_agents, last_run, status }], total }` |
| Create project | `POST /projects` | POST | `{ name, description }` -> `{ id, name, description, status: "Draft" }` |
| Project card data | `GET /projects` | GET | Each item maps to one project card |

---

## 7. Pencil Node Reference

| Node ID | Element | Section |
|---------|---------|---------|
| `2Efo9` | Root frame (1440x900) | -- |
| `SvySF` | App Sidebar (256px) | Left |
| `CwLyz` | Main Content area | Right |
| `Zlbn9` | Project Cards Grid | Main content |
