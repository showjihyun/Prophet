# UI-02 — Communities Detail SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Communities Detail (ID: LRkh8)

---

## 1. Overview

The Communities Detail screen provides a comprehensive overview of all communities in the current simulation. It displays aggregate statistics, per-community health cards with sentiment, emotion distribution, and key influencers, as well as an inter-community connection matrix. This screen is accessed from the main simulation screen via the community panel or navigation breadcrumb.

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| Nav Bar                                                    [LRkh8/nav] |
| [Logo] MCASP Prophet Engine   Home > Communities Overview              |
+------------------------------------------------------------------------+
| Summary Stats (4 cards, horizontal row)                [LRkh8/summary] |
| [Total Communities] [Total Agents] [Active Interactions] [Avg Sent.]   |
+------------------------------------------------------------------------+
| Community Cards Grid (2-3 columns, responsive)          [LRkh8/grid]  |
| +-------------------+ +-------------------+ +-------------------+      |
| | Alpha Community   | | Beta Community    | | Gamma Community   |      |
| | 1,500 agents      | | 1,200 agents      | | 1,100 agents      |      |
| | sentiment bar     | | sentiment bar     | | sentiment bar     |      |
| | key influencers   | | key influencers   | | key influencers   |      |
| | emotion dist.     | | emotion dist.     | | emotion dist.     |      |
| +-------------------+ +-------------------+ +-------------------+      |
| +-------------------+ +-------------------+                            |
| | Delta Community   | | Bridge Community  |                            |
| +-------------------+ +-------------------+                            |
+------------------------------------------------------------------------+
| Community Connections Matrix                           [LRkh8/matrix] |
| 5x5 grid showing inter-community relationship strength with dots      |
+------------------------------------------------------------------------+
```

---

## 3. Components

### Navigation Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `LRkh8/nav` | `div` (flex row) | Top navigation bar with logo and breadcrumb | `LRkh8` |
| `LRkh8/nav/logo` | `div` (flex row) | Brain icon + "MCASP Prophet Engine" text | `LRkh8/nav` |
| `LRkh8/nav/breadcrumb` | `Breadcrumb` | "Home > Communities Overview" with clickable segments | `LRkh8/nav` |

### Summary Stats

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `LRkh8/summary` | `div` (grid 4-col) | Horizontal row of 4 summary stat cards | `LRkh8` |
| `LRkh8/summary/totalCommunities` | `Card` | "Total Communities" label, value "5", icon=Users | `LRkh8/summary` |
| `LRkh8/summary/totalAgents` | `Card` | "Total Agents" label, value "6,500", icon=UserPlus | `LRkh8/summary` |
| `LRkh8/summary/activeInteractions` | `Card` | "Active Interactions" label, value "24,891", icon=MessageCircle | `LRkh8/summary` |
| `LRkh8/summary/avgSentiment` | `Card` | "Avg Sentiment" label, value "+0.72", icon=TrendingUp, color=green | `LRkh8/summary` |

### Community Cards Grid

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `LRkh8/grid` | `div` (grid, responsive) | Grid container for community cards, gap=16px | `LRkh8` |
| `LRkh8/grid/alpha` | `Card` | Alpha community card (blue accent) | `LRkh8/grid` |
| `LRkh8/grid/alpha/header` | `div` (flex row) | Community name "Alpha" + agent count badge "1,500" | `LRkh8/grid/alpha` |
| `LRkh8/grid/alpha/sentiment` | `div` | Sentiment bar: horizontal bar showing positive/neutral/negative ratio | `LRkh8/grid/alpha` |
| `LRkh8/grid/alpha/influencers` | `div` | Key influencers: top 3 agent IDs with influence scores | `LRkh8/grid/alpha` |
| `LRkh8/grid/alpha/emotions` | `div` | Emotion distribution: stacked horizontal bar (interest/trust/skepticism/excitement) | `LRkh8/grid/alpha` |
| `LRkh8/grid/alpha/status` | `Badge` | Activity status label: "High" / "Medium" / "Low" / "Very High" | `LRkh8/grid/alpha` |
| `LRkh8/grid/beta` | `Card` | Beta community card (green accent) -- same internal structure as alpha | `LRkh8/grid` |
| `LRkh8/grid/gamma` | `Card` | Gamma community card (orange accent) -- same internal structure as alpha | `LRkh8/grid` |
| `LRkh8/grid/delta` | `Card` | Delta community card (purple accent) -- same internal structure as alpha | `LRkh8/grid` |
| `LRkh8/grid/bridge` | `Card` | Bridge community card (red accent) -- same internal structure as alpha | `LRkh8/grid` |

### Community Connections Matrix

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `LRkh8/matrix` | `Card` | "Community Connections" container card | `LRkh8` |
| `LRkh8/matrix/title` | `h3` | "Community Connections" heading | `LRkh8/matrix` |
| `LRkh8/matrix/grid` | `div` (grid 6x6) | 5x5 matrix with header row/column, showing relationship dots | `LRkh8/matrix` |
| `LRkh8/matrix/dot` | `div` (circle) | Colored dot indicating connection strength: size and color vary by strength (small/gray=weak, large/colored=strong) | `LRkh8/matrix/grid` |

---

## 4. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--community-alpha` | `#3b82f6` | Alpha card accent, matrix dot |
| `--community-beta` | `#22c55e` | Beta card accent, matrix dot |
| `--community-gamma` | `#f97316` | Gamma card accent, matrix dot |
| `--community-delta` | `#a855f7` | Delta card accent, matrix dot |
| `--community-bridge` | `#ef4444` | Bridge card accent, matrix dot |
| `--bg-card` | `#ffffff` / `#1e293b` (dark) | Card backgrounds |
| `--bg-page` | `#f8fafc` / `#0f172a` (dark) | Page background |
| `--status-high` | `#22c55e` | "High" activity badge |
| `--status-medium` | `#eab308` | "Medium" activity badge |
| `--status-low` | `#94a3b8` | "Low" activity badge |
| `--status-veryhigh` | `#ef4444` | "Very High" activity badge |
| `--emotion-interest` | `#3b82f6` | Interest emotion bar segment |
| `--emotion-trust` | `#22c55e` | Trust emotion bar segment |
| `--emotion-skepticism` | `#f97316` | Skepticism emotion bar segment |
| `--emotion-excitement` | `#a855f7` | Excitement emotion bar segment |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page title (breadcrumb active) | Inter / system | 16px | 600 |
| Stat card value | Inter / system | 28px | 700 |
| Stat card label | Inter / system | 12px | 400 |
| Community card name | Inter / system | 16px | 600 |
| Agent count badge | Inter / system | 12px | 500 |
| Influencer name | Inter / system | 13px | 400 |
| Matrix header labels | Inter / system | 12px | 500 |

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--page-padding` | `24px` | Page outer padding |
| `--card-padding` | `16px` | Card inner padding |
| `--grid-gap` | `16px` | Gap between community cards |
| `--stat-card-gap` | `16px` | Gap between summary stat cards |
| `--matrix-cell-size` | `48px` | Matrix grid cell dimensions |

---

## 5. Interaction Behavior

| Action | Trigger | Effect |
|--------|---------|--------|
| Community card click | Click on a community card | Navigates to filtered view of that community on main simulation screen (UI-01), graph highlights that cluster |
| Community card hover | Hover on a community card | Card elevates with shadow. Border accent color intensifies. |
| Influencer click | Click on influencer agent ID within a card | Navigates to Agent Detail screen (UI-04) for that agent |
| Matrix dot hover | Hover on a connection dot in the matrix | Tooltip shows: "Alpha <-> Beta: 342 connections, strength 0.78" |
| Matrix dot click | Click on a connection dot | Highlights the inter-community edges on the main graph (if navigated back to UI-01) |
| Breadcrumb "Home" click | Click "Home" in breadcrumb | Navigates back to main simulation screen (UI-01) |
| Summary card hover | Hover on a stat card | Subtle scale animation (1.02x) |
| Status badge meaning | -- | "Very High" = sentiment > 0.8, "High" = 0.5-0.8, "Medium" = 0.2-0.5, "Low" = < 0.2 |
| Real-time updates | WebSocket push | Agent counts, sentiment bars, and interaction counts update in real-time with smooth transitions |

---

## 6. Data Binding (Backend API)

| Component | API Endpoint | Method | Payload / Response |
|-----------|-------------|--------|-------------------|
| Summary stats | `GET /simulations/{id}/communities` | GET | Aggregated from community list: count, total agents, total interactions |
| Summary avg sentiment | `GET /simulations/{id}/steps/{step}/metrics` | GET | `{ avg_sentiment }` |
| Community cards | `GET /simulations/{id}/communities` | GET | `[{ id, name, color, agent_count, avg_sentiment, emotion_distribution, activity_level, key_influencers: [{ agent_id, influence_score }] }]` |
| Active interactions | `GET /simulations/{id}/network/metrics` | GET | `{ total_interactions, inter_community_edges }` |
| Connection matrix | `GET /simulations/{id}/network/metrics` | GET | `{ community_connections: [{ source, target, edge_count, strength }] }` |
| Real-time updates | `WS /simulations/{id}/ws` | WebSocket | Community-level metric updates per step |

---

## 7. Pencil Node Reference

| Node ID | Element | Section |
|---------|---------|---------|
| `LRkh8` | Root frame (1440x900) | -- |
| `LRkh8/nav` | Navigation bar | Top |
| `LRkh8/summary` | Summary stat cards row | Top section |
| `LRkh8/grid` | Community cards grid | Middle section |
| `LRkh8/grid/alpha` | Alpha community card | Grid |
| `LRkh8/grid/beta` | Beta community card | Grid |
| `LRkh8/grid/gamma` | Gamma community card | Grid |
| `LRkh8/grid/delta` | Delta community card | Grid |
| `LRkh8/grid/bridge` | Bridge community card | Grid |
| `LRkh8/matrix` | Community Connections matrix | Bottom section |
