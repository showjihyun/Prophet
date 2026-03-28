# UI-03 — Top Influencers SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Top Influencers (ID: V99cE)

---

## 1. Overview

The Top Influencers screen displays a ranked table of the most influential agents across all communities in the current simulation. It provides filtering, sorting, and a visual distribution chart to help users identify key opinion leaders and understand influence distribution patterns. Users can drill down into individual agent profiles from this screen.

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| Nav Bar                                                    [V99cE/nav] |
| [Logo] MCASP Prophet Engine   Home > Top Influencers                   |
+------------------------------------------------------------------------+
| Summary Stats (4 cards, horizontal row)                [V99cE/summary] |
| [Influencers Tracked] [Avg Influence] [Top Community] [Active Cascades]|
+------------------------------------------------------------------------+
| +------------------------------------------------------+----------+   |
| | Search + Filter Bar                     [V99cE/bar]  |          |   |
| +------------------------------------------------------+          |   |
| | Data Table                             [V99cE/table] | Right    |   |
| | Rank | Agent ID | Community | Score | Sentiment |    | Sidebar  |   |
| | ...  | ...      | ...       | ...   | ...       |    |          |   |
| | ...  | ...      | ...       | ...   | ...       |    | Influence|   |
| | ...  | ...      | ...       | ...   | ...       |    | Distrib. |   |
| |                                                      | Chart    |   |
| |                                                      |[V99cE/   |   |
| |                                                      | sidebar] |   |
| +------------------------------------------------------+----------+   |
+------------------------------------------------------------------------+
```

---

## 3. Components

### Navigation Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `V99cE/nav` | `div` (flex row) | Top navigation bar with logo and breadcrumb | `V99cE` |
| `V99cE/nav/logo` | `div` (flex row) | Brain icon + "MCASP Prophet Engine" text | `V99cE/nav` |
| `V99cE/nav/breadcrumb` | `Breadcrumb` | "Home > Top Influencers" with clickable segments | `V99cE/nav` |

### Summary Stats

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `V99cE/summary` | `div` (grid 4-col) | Horizontal row of 4 summary stat cards | `V99cE` |
| `V99cE/summary/tracked` | `Card` | "Influencers Tracked" label, value "342", icon=Crown | `V99cE/summary` |
| `V99cE/summary/avgScore` | `Card` | "Avg Influence Score" label, value "74.3", icon=BarChart3 | `V99cE/summary` |
| `V99cE/summary/topCommunity` | `Card` | "Top Community" label, value "Alpha" with blue dot, icon=Users | `V99cE/summary` |
| `V99cE/summary/activeCascades` | `Card` | "Active Cascades" label, value "89", icon=Zap | `V99cE/summary` |

### Search + Filter Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `V99cE/bar` | `div` (flex row) | Search and filter controls container | `V99cE` |
| `V99cE/bar/search` | `Input` | Search input, placeholder "Search agents...", icon=Search, debounce 300ms | `V99cE/bar` |
| `V99cE/bar/filterBtn` | `Button` | "Filter" button with Filter icon, opens filter popover | `V99cE/bar` |
| `V99cE/bar/filterPopover` | `Popover` | Filter options: Community (multi-select checkboxes), Status (Active/Idle), Influence range (slider) | `V99cE/bar` |

### Data Table

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `V99cE/table` | `Table` (shadcn DataTable) | Main influencer data table, sortable columns, paginated | `V99cE` |
| `V99cE/table/colRank` | `TableColumn` | "#" -- Rank number, auto-generated, right-aligned | `V99cE/table` |
| `V99cE/table/colAgentId` | `TableColumn` | "Agent ID" -- Agent identifier, clickable link to UI-04 | `V99cE/table` |
| `V99cE/table/colCommunity` | `TableColumn` | "Community" -- Community name with colored badge (dot + label) | `V99cE/table` |
| `V99cE/table/colScore` | `TableColumn` | "Influence Score" -- Numeric score + horizontal progress bar (0-100 scale) | `V99cE/table` |
| `V99cE/table/colSentiment` | `TableColumn` | "Sentiment" -- Sentiment badge: Positive (green), Neutral (gray), Negative (red) | `V99cE/table` |
| `V99cE/table/colChains` | `TableColumn` | "Chains" -- Number of cascade chains this agent participates in | `V99cE/table` |
| `V99cE/table/colConnections` | `TableColumn` | "Connections" -- Number of direct social connections | `V99cE/table` |
| `V99cE/table/colStatus` | `TableColumn` | "Status" -- Badge: "Active" (green) or "Idle" (gray) | `V99cE/table` |
| `V99cE/table/pagination` | `Pagination` | Bottom pagination: page numbers, prev/next, rows per page selector (10/25/50) | `V99cE/table` |

### Right Sidebar -- Influence Distribution

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `V99cE/sidebar` | `Card` | Right sidebar card, fixed width 280px | `V99cE` |
| `V99cE/sidebar/title` | `h3` | "Influence Distribution" heading | `V99cE/sidebar` |
| `V99cE/sidebar/chart` | `BarChart` (horizontal, Recharts) | Horizontal bar chart: 5 bars, one per community (Alpha/Beta/Gamma/Delta/Bridge), community-colored, shows aggregate influence scores | `V99cE/sidebar` |
| `V99cE/sidebar/barAlpha` | Bar | Alpha community bar, color=#3b82f6 | `V99cE/sidebar/chart` |
| `V99cE/sidebar/barBeta` | Bar | Beta community bar, color=#22c55e | `V99cE/sidebar/chart` |
| `V99cE/sidebar/barGamma` | Bar | Gamma community bar, color=#f97316 | `V99cE/sidebar/chart` |
| `V99cE/sidebar/barDelta` | Bar | Delta community bar, color=#a855f7 | `V99cE/sidebar/chart` |
| `V99cE/sidebar/barBridge` | Bar | Bridge community bar, color=#ef4444 | `V99cE/sidebar/chart` |

---

## 4. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--community-alpha` | `#3b82f6` | Alpha badge and bar |
| `--community-beta` | `#22c55e` | Beta badge and bar |
| `--community-gamma` | `#f97316` | Gamma badge and bar |
| `--community-delta` | `#a855f7` | Delta badge and bar |
| `--community-bridge` | `#ef4444` | Bridge badge and bar |
| `--bg-page` | `#f8fafc` / `#0f172a` (dark) | Page background |
| `--bg-card` | `#ffffff` / `#1e293b` (dark) | Card / table backgrounds |
| `--status-active` | `#22c55e` | "Active" status badge background |
| `--status-idle` | `#94a3b8` | "Idle" status badge background |
| `--sentiment-positive` | `#22c55e` | Positive sentiment badge |
| `--sentiment-neutral` | `#94a3b8` | Neutral sentiment badge |
| `--sentiment-negative` | `#ef4444` | Negative sentiment badge |
| `--score-bar-bg` | `#e2e8f0` / `#334155` (dark) | Influence score progress bar track |
| `--score-bar-fill` | `#3b82f6` | Influence score progress bar fill |
| `--table-row-hover` | `#f1f5f9` / `#1e293b` (dark) | Table row hover highlight |
| `--table-border` | `#e2e8f0` / `#334155` (dark) | Table cell borders |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Stat card value | Geist (tabular-nums) | 28px | 700 |
| Stat card label | Geist | 12px | 400 |
| Table header | Geist | 13px | 600 |
| Table body cell | Geist | 13px | 400 |
| Rank number | Geist (tabular-nums) | 13px | 600 |
| Agent ID link | Geist | 13px | 500 |
| Sidebar title | Geist | 14px | 600 |
| Chart axis labels | Geist | 11px | 400 |

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--page-padding` | `24px` | Page outer padding |
| `--stat-card-gap` | `16px` | Gap between summary stat cards |
| `--table-row-height` | `48px` | Table row height |
| `--sidebar-width` | `280px` | Right sidebar width |
| `--table-sidebar-gap` | `24px` | Gap between table and sidebar |
| `--search-bar-height` | `40px` | Search input height |

---

## 5. Interaction Behavior

| Action | Trigger | Effect |
|--------|---------|--------|
| Sort by column | Click table column header | Toggles sort direction (asc/desc). Default sort: influence score descending. Visual arrow indicator in header. |
| Search agents | Type in search input | Filters table rows in real-time (debounce 300ms). Matches against agent ID and community name. |
| Filter open | Click "Filter" button | Opens popover with filter controls: community multi-select, status toggle, influence range slider. |
| Filter apply | Change any filter control | Table filters immediately (no apply button needed). Active filter count shown as badge on Filter button. |
| Agent ID click | Click agent ID in table row | Navigates to Agent Detail screen (UI-04) for that agent. |
| Row hover | Hover on table row | Row background highlights. Cursor changes to pointer if clickable. |
| Pagination | Click page number or prev/next | Loads the requested page of results. Current page highlighted. |
| Rows per page | Select from dropdown (10/25/50) | Changes number of visible rows, resets to page 1. |
| Sidebar bar hover | Hover on a bar in distribution chart | Tooltip shows: "{Community}: {count} influencers, avg score {score}" |
| Sidebar bar click | Click on a bar | Filters the table to show only agents from that community. |
| Breadcrumb "Home" | Click "Home" in breadcrumb | Navigates back to main simulation screen (UI-01). |
| Real-time updates | WebSocket push | Influence scores and statuses update live. Table re-sorts if score changes affect order. |

---

## 6. Data Binding (Backend API)

| Component | API Endpoint | Method | Payload / Response |
|-----------|-------------|--------|-------------------|
| Summary - tracked | `GET /simulations/{id}/agents?sort=influence_score` | GET | Count of agents with influence_score > threshold |
| Summary - avg score | `GET /simulations/{id}/agents?sort=influence_score` | GET | Computed avg from response data |
| Summary - top community | `GET /simulations/{id}/communities` | GET | Community with highest avg influence |
| Summary - active cascades | `GET /simulations/{id}/steps/{step}/metrics` | GET | `{ active_cascades }` |
| Data table | `GET /simulations/{id}/agents?sort=influence_score&page={p}&limit={n}` | GET | `{ items: [{ id, community, influence_score, sentiment, cascade_chains, connections, status }], total, page, pages }` |
| Search/filter | `GET /simulations/{id}/agents?search={q}&community={c}&status={s}&min_score={min}&max_score={max}` | GET | Filtered agent list |
| Influence distribution | `GET /simulations/{id}/communities` | GET | `[{ id, name, color, influence_stats: { total, avg, count } }]` |
| Real-time updates | `WS /simulations/{id}/ws` | WebSocket | Agent score updates per step |

---

## 7. Pencil Node Reference

| Node ID | Element | Section |
|---------|---------|---------|
| `V99cE` | Root frame (1440x900) | -- |
| `V99cE/nav` | Navigation bar | Top |
| `V99cE/summary` | Summary stat cards row | Top section |
| `V99cE/bar` | Search + Filter bar | Above table |
| `V99cE/table` | Influencer data table | Main content |
| `V99cE/sidebar` | Influence Distribution chart | Right sidebar |
