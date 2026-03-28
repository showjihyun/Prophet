# UI-08 — Influencers with Pagination SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Influencers with Pagination (ID: iodBY)

---

## 1. Overview

The Influencers with Pagination screen is an updated version of UI-03 (Top Influencers). It retains the same core layout — summary stats, search/filter bar, data table, and influence distribution sidebar — but adds a dedicated pagination bar at the bottom with row count display, rows-per-page selector, and numbered page navigation. The summary stats are updated to reflect a larger dataset (120 influencers).

This SPEC extends UI-03. Only the differences and additions are described in detail; for the base layout refer to `docs/spec/ui/UI_03_TOP_INFLUENCERS.md`.

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| Nav Bar                                                    [iodBY/nav] |
| [Logo] MCASP Prophet Engine   Home > Top Influencers                   |
+------------------------------------------------------------------------+
| Summary Stats (4 cards, horizontal row)               [iodBY/summary] |
| [Total: 120] [Avg Score: 72.4] [Active: 98] [Bridges: 23]            |
+------------------------------------------------------------------------+
| +------------------------------------------------------+----------+   |
| | Search + Filter Bar                    [iodBY/bar]   |          |   |
| +------------------------------------------------------+          |   |
| | Data Table (10 rows visible)          [iodBY/table]  | Right    |   |
| | Rank | Agent ID | Community | Score | Sentiment |    | Sidebar  |   |
| |  1   | #4201    | Alpha     | 96.8  | Positive  |    |          |   |
| |  2   | #3847    | Beta      | 94.2  | Positive  |    | Influence|   |
| | ...  | ...      | ...       | ...   | ...       |    | Distrib. |   |
| | 10   | #2156    | Gamma     | 81.3  | Neutral   |    | Chart    |   |
| +------------------------------------------------------+[iodBY/   |   |
| | Pagination Bar                   [iodBY/pagination]  | sidebar] |   |
| | Showing 1-10 of 120   Rows/page: [10v]  1 2 3...10 >|          |   |
| +------------------------------------------------------+----------+   |
+------------------------------------------------------------------------+
```

---

## 3. Components

### Navigation Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `iodBY/nav` | `div` (flex row) | Top navigation bar with logo and breadcrumb | `iodBY` |
| `iodBY/nav/logo` | `div` (flex row) | Brain icon + "MCASP Prophet Engine" text | `iodBY/nav` |
| `iodBY/nav/breadcrumb` | `Breadcrumb` | "Home > Top Influencers" with clickable segments | `iodBY/nav` |

### Summary Stats (Updated Values)

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `iodBY/summary` | `div` (grid 4-col) | Horizontal row of 4 summary stat cards | `iodBY` |
| `iodBY/summary/totalInfluencers` | `Card` | "Total Influencers" label, value "120", icon=Crown | `iodBY/summary` |
| `iodBY/summary/avgScore` | `Card` | "Avg Score" label, value "72.4", icon=BarChart3 | `iodBY/summary` |
| `iodBY/summary/activeInfluencers` | `Card` | "Active Influencers" label, value "98", icon=Users | `iodBY/summary` |
| `iodBY/summary/crossBridges` | `Card` | "Cross-Community Bridges" label, value "23", icon=GitBranch | `iodBY/summary` |

### Search + Filter Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `iodBY/bar` | `div` (flex row) | Search and filter controls container | `iodBY` |
| `iodBY/bar/search` | `Input` | Search input, placeholder "Search agents...", icon=Search, debounce 300ms | `iodBY/bar` |
| `iodBY/bar/filterBtn` | `Button` | "Filter" button with Filter icon, opens filter popover (UI-09) | `iodBY/bar` |

### Data Table

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `iodBY/table` | `Table` (shadcn DataTable) | Main influencer data table, sortable columns, 10 rows per page default | `iodBY` |
| `iodBY/table/colRank` | `TableColumn` | "#" -- Rank number, auto-generated, right-aligned | `iodBY/table` |
| `iodBY/table/colAgentId` | `TableColumn` | "Agent ID" -- Agent identifier, clickable link to UI-04 | `iodBY/table` |
| `iodBY/table/colCommunity` | `TableColumn` | "Community" -- Community name with colored badge (dot + label) | `iodBY/table` |
| `iodBY/table/colScore` | `TableColumn` | "Influence Score" -- Numeric score + horizontal progress bar (0-100 scale) | `iodBY/table` |
| `iodBY/table/colSentiment` | `TableColumn` | "Sentiment" -- Sentiment badge: Positive (green), Neutral (gray), Negative (red) | `iodBY/table` |
| `iodBY/table/colChains` | `TableColumn` | "Chains" -- Number of cascade chains this agent participates in | `iodBY/table` |
| `iodBY/table/colConnections` | `TableColumn` | "Connections" -- Number of direct social connections | `iodBY/table` |
| `iodBY/table/colStatus` | `TableColumn` | "Status" -- Badge: "Active" (green) or "Idle" (gray) | `iodBY/table` |

### Pagination Bar (New in UI-08)

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `iodBY/pagination` | `div` (flex row) | Pagination bar, border-top, padding 12px 16px, space-between alignment | `iodBY` |
| `iodBY/pagination/showing` | `span` | "Showing 1-10 of 120 influencers" text, muted-foreground | `iodBY/pagination` |
| `iodBY/pagination/rowsPerPage` | `div` (flex row) | "Rows per page:" label + Select dropdown with options: 10, 25, 50 (default: 10) | `iodBY/pagination` |
| `iodBY/pagination/rowsSelect` | `Select` | Rows per page dropdown, width 72px, options: 10/25/50 | `iodBY/pagination/rowsPerPage` |
| `iodBY/pagination/pages` | `div` (flex row) | Page number buttons group | `iodBY/pagination` |
| `iodBY/pagination/pagePrev` | `Button` | Previous page button, variant=ghost, icon=ChevronLeft, disabled on page 1 | `iodBY/pagination/pages` |
| `iodBY/pagination/pageNum` | `Button` (repeated) | Page number buttons (1, 2, 3, ..., 10), variant=ghost, active page gets variant=outline with ring | `iodBY/pagination/pages` |
| `iodBY/pagination/pageEllipsis` | `span` | "..." ellipsis between non-adjacent page numbers | `iodBY/pagination/pages` |
| `iodBY/pagination/pageNext` | `Button` | Next page button, variant=ghost, icon=ChevronRight, disabled on last page | `iodBY/pagination/pages` |

### Right Sidebar -- Influence Distribution

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `iodBY/sidebar` | `Card` | Right sidebar card, fixed width 280px | `iodBY` |
| `iodBY/sidebar/title` | `h3` | "Influence Distribution" heading | `iodBY/sidebar` |
| `iodBY/sidebar/chart` | `BarChart` (horizontal, Recharts) | Horizontal bar chart: 5 bars, one per community, community-colored | `iodBY/sidebar` |

---

## 4. Design Tokens

### Colors

Inherits all color tokens from UI-03. Additional tokens:

| Token | Value | Usage |
|-------|-------|-------|
| `--pagination-bg` | `var(--card)` | Pagination bar background |
| `--pagination-border` | `var(--border)` | Pagination bar top border |
| `--page-active-bg` | `var(--primary)` | Active page number button background |
| `--page-active-text` | `var(--primary-foreground)` | Active page number text |
| `--page-hover-bg` | `var(--accent)` | Hovered page number background |
| `--pagination-disabled` | `var(--muted-foreground)` | Disabled prev/next button color |
| `--community-alpha` | `#3b82f6` | Alpha badge and bar |
| `--community-beta` | `#22c55e` | Beta badge and bar |
| `--community-gamma` | `#f97316` | Gamma badge and bar |
| `--community-delta` | `#a855f7` | Delta badge and bar |
| `--community-bridge` | `#ef4444` | Bridge badge and bar |
| `--status-active` | `#22c55e` | "Active" status badge |
| `--status-idle` | `#94a3b8` | "Idle" status badge |
| `--sentiment-positive` | `#22c55e` | Positive sentiment badge |
| `--sentiment-neutral` | `#94a3b8` | Neutral sentiment badge |
| `--sentiment-negative` | `#ef4444` | Negative sentiment badge |
| `--score-bar-bg` | `#e2e8f0` / `#334155` (dark) | Influence score progress bar track |
| `--score-bar-fill` | `#3b82f6` | Influence score progress bar fill |

### Typography

Inherits all typography from UI-03. Additional:

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Pagination "Showing" text | Inter / system | 13px | 400 |
| Pagination "Rows per page" label | Inter / system | 13px | 400 |
| Page number buttons | Inter / system | 13px | 500 |

### Spacing

Inherits all spacing from UI-03. Additional:

| Token | Value | Usage |
|-------|-------|-------|
| `--pagination-height` | `52px` | Pagination bar height |
| `--pagination-padding` | `12px 16px` | Pagination bar inner padding |
| `--page-btn-size` | `32px` | Page number button width/height |
| `--page-btn-gap` | `4px` | Gap between page number buttons |

---

## 5. Interaction Behavior

Inherits all interactions from UI-03. Additional/modified behaviors:

| Action | Trigger | Effect |
|--------|---------|--------|
| Page navigation | Click page number button | Fetches page N of results from API. Table content updates with fade transition. "Showing X-Y of Z" updates. Active page button highlights. Scroll to table top. |
| Next page | Click ">" button | Advances to next page. Disabled (grayed, no pointer) when on last page. |
| Previous page | Click "<" button | Goes to previous page. Disabled when on page 1. |
| Rows per page | Select from dropdown (10/25/50) | Changes page size. Resets to page 1. Re-fetches data. "Showing" text and total pages recalculate. |
| Ellipsis display | Automatic when > 7 pages | Shows: 1 2 3 ... 8 9 10 pattern. Always shows first page, last page, and 2 pages around current. |
| Filter button | Click "Filter" button | Opens Filter Popover (UI-09) as a floating panel anchored to filter button. |
| Sort by column | Click table column header | Toggles sort direction (asc/desc). Resets to page 1. Default sort: influence score descending. |
| Search agents | Type in search input | Filters results, resets to page 1, updates total count and pagination. Debounce 300ms. |
| Agent ID click | Click agent ID in table row | Navigates to Agent Detail screen (UI-04). |
| Row hover | Hover on table row | Row background highlights with cursor pointer. |
| Sidebar bar click | Click on a community bar | Filters table to that community, resets to page 1. |
| Real-time updates | WebSocket push | Scores update live. If score changes affect sort order on current page, table re-sorts. |

---

## 6. Data Binding (Backend API)

| Component | API Endpoint | Method | Payload / Response |
|-----------|-------------|--------|-------------------|
| Summary - total | `GET /simulations/{id}/agents?sort=influence_score` | GET | Count of influencers (120) |
| Summary - avg score | `GET /simulations/{id}/agents?sort=influence_score` | GET | Computed avg (72.4) |
| Summary - active | `GET /simulations/{id}/agents?status=active` | GET | Count of active influencers (98) |
| Summary - bridges | `GET /simulations/{id}/agents?community=bridge` | GET | Count of cross-community bridges (23) |
| Data table (paginated) | `GET /simulations/{id}/agents?sort=influence_score&page={p}&limit={n}` | GET | `{ items: [{ id, community, influence_score, sentiment, cascade_chains, connections, status }], total: 120, page, pages, limit }` |
| Search/filter | `GET /simulations/{id}/agents?search={q}&community={c}&status={s}&min_score={min}&max_score={max}&page=1&limit={n}` | GET | Filtered + paginated agent list |
| Influence distribution | `GET /simulations/{id}/communities` | GET | `[{ id, name, color, influence_stats: { total, avg, count } }]` |
| Real-time updates | `WS /simulations/{id}/ws` | WebSocket | Agent score updates per step |

---

## 7. Pencil Node Reference

| Node ID | Element | Section |
|---------|---------|---------|
| `iodBY` | Root frame (1440x900) | -- |
| `iodBY/nav` | Navigation bar | Top |
| `iodBY/summary` | Summary stat cards row (updated values) | Top section |
| `iodBY/bar` | Search + Filter bar | Above table |
| `iodBY/table` | Influencer data table (10 rows default) | Main content |
| `iodBY/pagination` | Pagination bar (new) | Below table |
| `iodBY/sidebar` | Influence Distribution chart | Right sidebar |
