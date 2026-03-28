# UI-05 — Global Insight & Metrics SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Global Insight & Metrics (ID: fjP3Z)

---

## 1. Overview

The Global Insight & Metrics screen provides a comprehensive analytics dashboard for the entire simulation. It aggregates polarization trends, sentiment distribution by community, Prophet 3-Tier cost optimization statistics, and cascade analytics. This screen is accessed from the main simulation screen via the "Global Insights" button and serves as the primary reporting view for stakeholders.

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| Nav Bar                                                    [fjP3Z/nav] |
| [<Back to Simulation]   Global Insight & Metrics   [Export Data] button|
+------------------------------------------------------------------------+
| Summary Stats (4 cards, horizontal row)                [fjP3Z/summary] |
| [Total Agents] [Active Cascades] [Polarization] [Simulation Day]      |
+------------------------------------------------------------------------+
| 2-Column Chart Area                                   [fjP3Z/charts]  |
| +-------------------------------+----------------------------------+   |
| | Polarization Trend            | Sentiment by Community           |   |
| | (Bar Chart)                   | (Horizontal Stacked Bar)         |   |
| | [fjP3Z/polarizationChart]     | [fjP3Z/sentimentChart]           |   |
| +-------------------------------+----------------------------------+   |
+------------------------------------------------------------------------+
| 2-Column Bottom                                       [fjP3Z/bottom]  |
| +-------------------------------+----------------------------------+   |
| | Prophet 3-Tier Cost           | Cascade Analytics                |   |
| | Optimization                  |                                  |   |
| | [Tier1] [Tier2] [Tier3]       | [Avg Depth] [Max Width]          |   |
| | [fjP3Z/tierStats]             | [Critical Path] [Decay Rate]     |   |
| |                               | [fjP3Z/cascadeStats]             |   |
| +-------------------------------+----------------------------------+   |
+------------------------------------------------------------------------+
```

---

## 3. Components

### Navigation Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `fjP3Z/nav` | `div` (flex row) | Top navigation bar with back button, title, and export button | `fjP3Z` |
| `fjP3Z/nav/backBtn` | `Button` | "Back to Simulation" button with ChevronLeft icon, variant=ghost | `fjP3Z/nav` |
| `fjP3Z/nav/title` | `h1` | "Global Insight & Metrics" page title, centered | `fjP3Z/nav` |
| `fjP3Z/nav/exportBtn` | `Button` | "Export Data" button with Download icon, variant=outline | `fjP3Z/nav` |

### Summary Stats

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `fjP3Z/summary` | `div` (grid 4-col) | Horizontal row of 4 summary stat cards | `fjP3Z` |
| `fjP3Z/summary/totalAgents` | `Card` | "Total Agents" label, value "6,500", delta "+2% system", icon=Users. Delta badge shows growth since simulation start. | `fjP3Z/summary` |
| `fjP3Z/summary/activeCascades` | `Card` | "Active Cascades" label, value "847", delta "+12 today", icon=Zap. Delta badge shows cascades added today. | `fjP3Z/summary` |
| `fjP3Z/summary/polarization` | `Card` | "Polarization" label, value "0.72", delta "+0.08 from Day 46", icon=Activity. Delta colored red (increasing polarization = warning). | `fjP3Z/summary` |
| `fjP3Z/summary/simDay` | `Card` | "Simulation Day" label, value "Day 47", subtitle "of 365 days", icon=Calendar. Progress bar showing 47/365 completion. | `fjP3Z/summary` |

### Charts Area (2-column)

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `fjP3Z/charts` | `div` (grid 2-col) | 2-column container for main charts | `fjP3Z` |
| `fjP3Z/polarizationChart` | `Card` | "Polarization Trend" card containing bar chart | `fjP3Z/charts` |
| `fjP3Z/polarizationChart/title` | `h3` | "Polarization Trend" heading | `fjP3Z/polarizationChart` |
| `fjP3Z/polarizationChart/chart` | `BarChart` (Recharts) | Vertical bar chart: X-axis=simulation days (sampled or all), Y-axis=polarization index (0-1). Bars colored on gradient (green at low, yellow at mid, red at high). Tooltip on hover shows exact value and day. | `fjP3Z/polarizationChart` |
| `fjP3Z/sentimentChart` | `Card` | "Sentiment by Community" card containing horizontal stacked bar chart | `fjP3Z/charts` |
| `fjP3Z/sentimentChart/title` | `h3` | "Sentiment by Community" heading | `fjP3Z/sentimentChart` |
| `fjP3Z/sentimentChart/chart` | `BarChart` (horizontal stacked, Recharts) | 5 horizontal bars (one per community: Alpha/Beta/Gamma/Delta/Bridge). Each bar is stacked with Positive (green), Neutral (gray), Negative (red) segments. Community labels on Y-axis with colored dots. | `fjP3Z/sentimentChart` |

### Bottom Area (2-column)

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `fjP3Z/bottom` | `div` (grid 2-col) | 2-column container for bottom section | `fjP3Z` |

#### Left: Prophet 3-Tier Cost Optimization

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `fjP3Z/tierStats` | `Card` | "Prophet 3-Tier Cost Optimization" container card | `fjP3Z/bottom` |
| `fjP3Z/tierStats/title` | `h3` | "Prophet 3-Tier Cost Optimization" heading | `fjP3Z/tierStats` |
| `fjP3Z/tierStats/tier1` | `Card` (nested) | Tier 1 stat card: "Tier 1: Mass SLM", agent count "4,800 agents", description "Rule-based + local SLM inference", icon=Cpu, color=blue accent | `fjP3Z/tierStats` |
| `fjP3Z/tierStats/tier2` | `Card` (nested) | Tier 2 stat card: "Tier 2: Semantic", agent count "1,700 agents", description "Heuristic + semantic analysis", icon=Brain, color=yellow accent | `fjP3Z/tierStats` |
| `fjP3Z/tierStats/tier3` | `Card` (nested) | Tier 3 stat card: "Tier 3: Elite LLM", agent count (remaining agents), description "Full LLM reasoning (Claude/GPT)", icon=Sparkles, color=purple accent | `fjP3Z/tierStats` |
| `fjP3Z/tierStats/costBar` | `div` | Visual cost distribution bar: 3-segment horizontal bar showing tier proportions, color-coded (blue/yellow/purple) | `fjP3Z/tierStats` |

#### Right: Cascade Analytics

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `fjP3Z/cascadeStats` | `Card` | "Cascade Analytics" container card | `fjP3Z/bottom` |
| `fjP3Z/cascadeStats/title` | `h3` | "Cascade Analytics" heading | `fjP3Z/cascadeStats` |
| `fjP3Z/cascadeStats/avgDepth` | `Card` (nested) | "Avg Cascade Depth" stat card: numeric value, icon=GitBranch, description of average propagation depth across all cascades | `fjP3Z/cascadeStats` |
| `fjP3Z/cascadeStats/maxWidth` | `Card` (nested) | "Max Cascade Width" stat card: numeric value, icon=GitMerge, widest cascade breadth at any single step | `fjP3Z/cascadeStats` |
| `fjP3Z/cascadeStats/criticalPath` | `Card` (nested) | "Critical Path" stat card: numeric value or agent chain, icon=Route, longest single cascade chain path | `fjP3Z/cascadeStats` |
| `fjP3Z/cascadeStats/decayRate` | `Card` (nested) | "Decay Rate" stat card: numeric value (e.g., "0.12/step"), icon=TrendingDown, average cascade decay rate per step | `fjP3Z/cascadeStats` |

---

## 4. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `#f8fafc` / `#0f172a` (dark) | Page background |
| `--bg-card` | `#ffffff` / `#1e293b` (dark) | Card backgrounds |
| `--community-alpha` | `#3b82f6` | Alpha sentiment bar segment label |
| `--community-beta` | `#22c55e` | Beta sentiment bar segment label |
| `--community-gamma` | `#f97316` | Gamma sentiment bar segment label |
| `--community-delta` | `#a855f7` | Delta sentiment bar segment label |
| `--community-bridge` | `#ef4444` | Bridge sentiment bar segment label |
| `--sentiment-positive` | `#22c55e` | Positive segment in stacked bars |
| `--sentiment-neutral` | `#94a3b8` | Neutral segment in stacked bars |
| `--sentiment-negative` | `#ef4444` | Negative segment in stacked bars |
| `--polarization-low` | `#22c55e` | Polarization bar color when value < 0.3 |
| `--polarization-mid` | `#eab308` | Polarization bar color when value 0.3-0.6 |
| `--polarization-high` | `#ef4444` | Polarization bar color when value > 0.6 |
| `--tier1-color` | `#3b82f6` | Tier 1 (Mass SLM) accent color |
| `--tier2-color` | `#eab308` | Tier 2 (Semantic) accent color |
| `--tier3-color` | `#a855f7` | Tier 3 (Elite LLM) accent color |
| `--delta-positive` | `#22c55e` | Positive delta badge (good change) |
| `--delta-negative` | `#ef4444` | Negative delta badge (concerning change) |
| `--delta-neutral` | `#94a3b8` | Neutral delta badge |
| `--cascade-depth` | `#3b82f6` | Cascade depth stat accent |
| `--cascade-width` | `#22c55e` | Cascade width stat accent |
| `--cascade-path` | `#f97316` | Critical path stat accent |
| `--cascade-decay` | `#ef4444` | Decay rate stat accent |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Page title | Inter / system | 20px | 700 |
| Stat card value | Inter / system | 28px | 700 |
| Stat card label | Inter / system | 12px | 400 |
| Stat card delta | Inter / system | 11px | 500 |
| Section heading (h3) | Inter / system | 16px | 600 |
| Tier card title | Inter / system | 14px | 600 |
| Tier card agent count | Inter / system | 20px | 700 |
| Tier card description | Inter / system | 12px | 400, opacity 0.7 |
| Cascade stat value | Inter / system | 24px | 700 |
| Cascade stat label | Inter / system | 12px | 400 |
| Chart axis labels | Inter / system | 11px | 400 |
| Chart tooltip | Inter / system | 12px | 400 |
| Export button text | Inter / system | 13px | 500 |

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--page-padding` | `24px` | Page outer padding |
| `--stat-card-gap` | `16px` | Gap between summary stat cards |
| `--chart-grid-gap` | `24px` | Gap between chart columns |
| `--bottom-grid-gap` | `24px` | Gap between bottom section columns |
| `--tier-card-gap` | `12px` | Gap between tier stat cards |
| `--cascade-card-gap` | `12px` | Gap between cascade stat cards |
| `--section-gap` | `24px` | Vertical gap between major sections |
| `--chart-height` | `300px` | Chart container height |
| `--card-padding` | `16px` | Card inner padding |

---

## 5. Interaction Behavior

| Action | Trigger | Effect |
|--------|---------|--------|
| Back to simulation | Click "Back to Simulation" button | Navigates back to main simulation screen (UI-01). |
| Export data | Click "Export Data" button | Opens dropdown: "Export as CSV", "Export as JSON", "Export as PDF". Downloads selected format containing all visible metrics data. |
| Polarization chart hover | Hover on a bar in polarization trend | Tooltip shows: "Day {n}: Polarization Index {value}" with exact numeric value. |
| Polarization chart click | Click on a bar | Seeks simulation to that day (if supported), or highlights that day's data across all charts. |
| Sentiment chart hover | Hover on a stacked bar segment | Tooltip shows: "{Community} - Positive: {n}%, Neutral: {n}%, Negative: {n}%" |
| Sentiment chart click | Click on a community bar | Navigates to Communities Detail (UI-02) filtered to that community. |
| Tier card hover | Hover on a tier stat card | Card elevates with subtle shadow. Shows additional detail tooltip: "Cost per step: ${amount}" |
| Tier card click | Click on a tier stat card | Expands inline to show detailed agent breakdown: list of agent IDs in that tier, cost per agent. |
| Cascade stat hover | Hover on cascade metric card | Tooltip shows trend: "+/- {delta} from previous day" |
| Delta badge meaning | -- | Green arrow-up = positive growth. Red arrow-up on polarization = warning (polarization increasing is bad). Context-sensitive coloring. |
| Simulation day progress | Auto-update | Progress bar fills proportionally (47/365). Updates on each step via WebSocket. |
| Real-time updates | WebSocket push | All stat values, chart data, and tier distributions update live on each simulation step. Charts animate new data points. |
| Export in progress | Export initiated | Button shows spinner. Toast notification on completion: "Data exported successfully". |

---

## 6. Data Binding (Backend API)

| Component | API Endpoint | Method | Payload / Response |
|-----------|-------------|--------|-------------------|
| Total agents | `GET /simulations/{id}` | GET | `{ total_agents, current_step, total_steps }` |
| Active cascades | `GET /simulations/{id}/steps/{step}/metrics` | GET | `{ active_cascades, cascades_today }` |
| Polarization | `GET /simulations/{id}/steps/{step}/metrics` | GET | `{ polarization_index, polarization_delta }` |
| Simulation day | `GET /simulations/{id}` | GET | `{ current_step, total_steps }` |
| Polarization trend | `GET /simulations/{id}/steps` | GET | `[{ step, polarization_index }]` -- all steps for trend chart |
| Sentiment by community | `GET /simulations/{id}/communities` | GET | `[{ id, name, color, sentiment: { positive, neutral, negative } }]` |
| Tier 1 stats | `GET /simulations/{id}/llm/stats` | GET | `{ tier1: { agent_count, cost_per_step } }` |
| Tier 2 stats | `GET /simulations/{id}/llm/stats` | GET | `{ tier2: { agent_count, cost_per_step } }` |
| Tier 3 stats | `GET /simulations/{id}/llm/stats` | GET | `{ tier3: { agent_count, cost_per_step } }` |
| LLM impact | `GET /simulations/{id}/llm/impact` | GET | `{ total_cost, cost_savings, tier_distribution }` |
| Cascade analytics | `GET /simulations/{id}/steps/{step}/metrics` | GET | `{ avg_cascade_depth, max_cascade_width, critical_path, decay_rate }` |
| Export data | `GET /simulations/{id}/export?format={csv|json|pdf}` | GET | Binary download of simulation data |
| Real-time updates | `WS /simulations/{id}/ws` | WebSocket | Global metric updates per step |

---

## 7. Pencil Node Reference

| Node ID | Element | Section |
|---------|---------|---------|
| `fjP3Z` | Root frame (1440x900) | -- |
| `fjP3Z/nav` | Navigation bar (back + title + export) | Top |
| `fjP3Z/summary` | Summary stat cards row (4 cards) | Top section |
| `fjP3Z/summary/totalAgents` | Total Agents stat card | Summary |
| `fjP3Z/summary/activeCascades` | Active Cascades stat card | Summary |
| `fjP3Z/summary/polarization` | Polarization stat card | Summary |
| `fjP3Z/summary/simDay` | Simulation Day stat card | Summary |
| `fjP3Z/charts` | 2-column chart area | Middle section |
| `fjP3Z/polarizationChart` | Polarization Trend bar chart | Charts left |
| `fjP3Z/sentimentChart` | Sentiment by Community stacked bar chart | Charts right |
| `fjP3Z/bottom` | 2-column bottom section | Bottom section |
| `fjP3Z/tierStats` | Prophet 3-Tier Cost Optimization | Bottom left |
| `fjP3Z/tierStats/tier1` | Tier 1: Mass SLM card | Tier stats |
| `fjP3Z/tierStats/tier2` | Tier 2: Semantic card | Tier stats |
| `fjP3Z/tierStats/tier3` | Tier 3: Elite LLM card | Tier stats |
| `fjP3Z/cascadeStats` | Cascade Analytics | Bottom right |
| `fjP3Z/cascadeStats/avgDepth` | Avg Cascade Depth card | Cascade stats |
| `fjP3Z/cascadeStats/maxWidth` | Max Cascade Width card | Cascade stats |
| `fjP3Z/cascadeStats/criticalPath` | Critical Path card | Cascade stats |
| `fjP3Z/cascadeStats/decayRate` | Decay Rate card | Cascade stats |
