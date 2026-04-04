# UI-01 — AI Social World Engine (Main Simulation Screen) SPEC
Version: 0.2.0 | Status: REVIEW
Source: pencil-shadcn.pen > Frame: AI Social World Engine (ID: FuHqi)

---

## 1. Overview

The main simulation screen is the primary workspace of Prophet MCASP. It provides a real-time view of the running simulation, combining a force-directed social graph visualization with community management, live metrics, diffusion timeline, and conversation feeds. This is the screen users spend most of their time on during a simulation run.

The screen is divided into 4 horizontal zones stacked vertically:
1. **Simulation Control Bar** (top) -- global controls and simulation state
2. **Middle Content** (center) -- community panel, graph engine, metrics panel
3. **Timeline + Diffusion Wave** (bottom-upper) -- temporal navigation and diffusion visualization
4. **Conversations / Expert Agent** (bottom-lower) -- AI analysis and live agent conversations

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| Zone 1: Simulation Control Bar (56px)                      [FuHqi/ib0Jy]|
| [Logo] Status | [Global Insights] [Scenario v] [1x 2x 5x 10x] | [>||] |
+------------------------------------------------------------------------+
| Zone 2: Middle Content (fill)                              [FuHqi/nhMlv]|
| +----------+--------------------------------------+-----------+         |
| | Left     | Center                               | Right     |         |
| | Community| AI Social World Graph Engine          | Real-Time |         |
| | Panel    | (dark bg, force-directed graph)       | Metrics   |         |
| | 260px    | [KrXVA]                               | 280px     |         |
| | [S24t3]  |                                       | [MuKxh]   |         |
| |          | [legend] [cascade badge] [status]     |           |         |
| +----------+--------------------------------------+-----------+         |
+------------------------------------------------------------------------+
| Zone 3: Bottom Area (220px)                                [FuHqi/hXlH6]|
| +------------------------------------------------------------------+   |
| | Timeline + Diffusion Wave (120px)                    [oLh4Q]     |   |
| | [>|>] Day 47/365              [||||||||||||||||||||||||] 5x Speed |   |
| +------------------------------------------------------------------+   |
| +-----------------------------+------------------------------------+   |
| | Expert Agent Analysis       | Live Conversation Feed   [AoCh3]  |   |
| | [brain] Analyzing...        | [msg1] [msg2] [msg3]              |   |
| +-----------------------------+------------------------------------+   |
+------------------------------------------------------------------------+
```

### 2.1 Empty State (No Active Simulation)

When no simulation is loaded, the page shows:
- ControlPanel (top bar) with "New Simulation" button visible
- Centered empty state: icon + title + description + "Create New Simulation" CTA
- CTA navigates to /projects (project selection is required before creating a simulation)
- /setup is NOT a separate sidebar menu item — it is only accessible from:
  1. SimulationPage empty state CTA
  2. ControlPanel "New Simulation" button (when simulation is null)
  3. Direct URL navigation
- **Note:** Alternatively, the inline New Simulation flow in ControlPanel creates a simulation without page navigation

---

## 3. Components

### Zone 1: Simulation Control Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `ib0Jy` | `div` (flex row) | Top control bar container, height 56px, border-bottom | `FuHqi` |
| `ib0Jy/logo` | `div` (flex row) | Logo group: brain icon + "MCASP Prophet Engine" text | `ib0Jy` |
| `ib0Jy/status` | `Badge` | Status badge: "Running . Day 47/365", variant=outline, green dot indicator | `ib0Jy` |
| `ib0Jy/globalInsights` | `Button` | "Global Insights" button, variant=default (primary), navigates to UI-05 | `ib0Jy` |
| `ib0Jy/scenarioSelect` | `Select` | Scenario dropdown, default value "Default", options from simulation config | `ib0Jy` |
| `ib0Jy/speedGroup` | `div` (flex row) | Speed control group: 4 ghost buttons | `ib0Jy` |
| `ib0Jy/speed1x` | `Button` | "1x" speed, variant=ghost, active state when selected | `ib0Jy/speedGroup` |
| `ib0Jy/speed2x` | `Button` | "2x" speed, variant=ghost | `ib0Jy/speedGroup` |
| `ib0Jy/speed5x` | `Button` | "5x" speed, variant=ghost | `ib0Jy/speedGroup` |
| `ib0Jy/speed10x` | `Button` | "10x" speed, variant=ghost | `ib0Jy/speedGroup` |
| `ib0Jy/playBtn` | `Button` | Play/Resume simulation, icon=Play | `ib0Jy` |
| `ib0Jy/pauseBtn` | `Button` | Pause simulation, icon=Pause | `ib0Jy` |
| `ib0Jy/stepBtn` | `Button` | Step forward one tick, icon=SkipForward | `ib0Jy` |
| `ib0Jy/resetBtn` | `Button` | Reset simulation to Day 0, icon=RotateCcw | `ib0Jy` |
| `ib0Jy/replayBtn` | `Button` | Replay from beginning, icon=Rewind | `ib0Jy` |
| `ib0Jy/settingsBtn` | `Button` | Open settings modal, icon=Settings, variant=ghost | `ib0Jy` |
| `ib0Jy/avatar` | `Avatar` | Current user avatar, top-right corner | `ib0Jy` |
| `ib0Jy/loadPrev` | `Button` | "Load Previous" dropdown with search — loads previously saved simulations | `ib0Jy` |
| `ib0Jy/compare` | `Button` | "Compare" dropdown — select another simulation for side-by-side comparison (navigates to /compare/:id) | `ib0Jy` |
| `ib0Jy/clone` | `Button` | "Clone" — copies current simulation config to setup page for re-run | `ib0Jy` |
| `ib0Jy/injectEvent` | `Button` | "Inject Event" — opens InjectEventModal for mid-simulation event injection | `ib0Jy` |
| `ib0Jy/monteCarlo` | `Button` | "Monte Carlo" — opens MonteCarloModal for multi-run analysis | `ib0Jy` |
| `ib0Jy/engineControl` | `Button` | "Engine Control" — toggles EngineControlPanel dropdown for SLM/LLM ratio adjustment | `ib0Jy` |
| `ib0Jy/llmDashboard` | `Button` | "LLM Dashboard" toggle — shows/hides collapsible LLM stats overlay at bottom | `ib0Jy` |
| `ib0Jy/runAll` | `Button` | "Run All" — runs all remaining steps to completion, shows report on finish | `ib0Jy` |

### Zone 2: Left -- Community Panel

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `S24t3` | `div` (flex col) | Community panel container, width 260px, border-right, bg=card | `nhMlv` |
| `S24t3/search` | `Input` | Search/filter input, placeholder "Filter communities...", icon=Search | `S24t3` |
| `S24t3/title` | `div` (flex row) | "Communities" heading + count badge "5" | `S24t3` |
| `S24t3/list` | `div` (flex col) | Scrollable list of community items | `S24t3` |
| `S24t3/itemAlpha` | `div` (flex row) | Community Alpha: blue dot, name, agent count, sentiment indicator | `S24t3/list` |
| `S24t3/itemBeta` | `div` (flex row) | Community Beta: green dot, name, agent count, sentiment indicator | `S24t3/list` |
| `S24t3/itemGamma` | `div` (flex row) | Community Gamma: orange dot, name, agent count, sentiment indicator | `S24t3/list` |
| `S24t3/itemDelta` | `div` (flex row) | Community Delta: purple dot, name, agent count, sentiment indicator | `S24t3/list` |
| `S24t3/itemBridge` | `div` (flex row) | Community Bridge: red dot, name, agent count, sentiment indicator | `S24t3/list` |
| `S24t3/total` | `div` | "Total: 6,500 Agents" summary row, font-medium, border-top | `S24t3` |

### Zone 2: Center -- AI Social World Graph Engine

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `KrXVA` | `div` (relative) | Graph engine container, dark bg with radial gradient, flex=1 | `nhMlv` |
| `KrXVA/titleOverlay` | `div` (absolute, top-left) | Title: "AI Social World" + subtitle "MiroFish Engine -- 6,500 Active Agents . Force-Directed Graph" | `KrXVA` |
| `KrXVA/zoomControls` | `div` (absolute, top-right) | Zoom controls: +/- buttons and maximize/fullscreen button | `KrXVA` |
| `KrXVA/canvas` | `canvas` / Cytoscape.js | WebGL-rendered force-directed graph canvas, fills parent | `KrXVA` |
| `KrXVA/clusterAlpha` | (virtual) | Alpha community cluster ellipse, blue agent dots | `KrXVA/canvas` |
| `KrXVA/clusterBeta` | (virtual) | Beta community cluster ellipse, green agent dots | `KrXVA/canvas` |
| `KrXVA/clusterGamma` | (virtual) | Gamma community cluster ellipse, orange agent dots | `KrXVA/canvas` |
| `KrXVA/clusterDelta` | (virtual) | Delta community cluster ellipse, purple agent dots | `KrXVA/canvas` |
| `KrXVA/clusterBridge` | (virtual) | Bridge community cluster, red agent dots | `KrXVA/canvas` |
| `tTv8e` | `Card` (absolute, follows cursor) | Node detail popup on hover: agent name, influence, sentiment, connections, cascades, last message | `KrXVA` |
| `xUIlT` | `div` (absolute, bottom-left) | Network legend: 5 community colors + agent counts, semi-transparent bg | `KrXVA` |
| `cmbzK` | `Badge` (absolute) | Cascade badge: "Cascade #47 Active", green glow effect | `KrXVA` |
| `o4TMY` | `div` (absolute, bottom-right) | Status overlay: "60 FPS . 6,500 nodes . 18,420 edges . WebGL" | `KrXVA` |

### Zone 2: Right -- Metrics Panel

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `MuKxh` | `div` (flex col) | Metrics panel container, width 280px, border-left, bg=card | `nhMlv` |
| `MuKxh/title` | `div` (flex row) | "Real-Time Metrics" heading + LIVE badge (red pulsing dot) | `MuKxh` |
| `MuKxh/activeAgents` | `Card` | Active Agents: 5,847 / 6,500 with progress bar (value/max) | `MuKxh` |
| `MuKxh/sentiment` | `Card` | Sentiment Distribution: 3 horizontal bars (Positive=green, Neutral=gray, Negative=red) | `MuKxh` |
| `MuKxh/polarization` | `Card` | Polarization Index: 0.72, gradient bar (green->yellow->red), indicator dot positioned at value | `MuKxh` |
| `MuKxh/cascadeStats` | `div` (grid 2-col) | Cascade Stats: Depth card (value: 12) and Width card (value: 847) | `MuKxh` |
| `MuKxh/topInfluencers` | `Card` | Top Influencers: ranked list with agent IDs, community color dots, and influence scores | `MuKxh` |

### Zone 3: Timeline + Diffusion Wave

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `oLh4Q` | `div` (flex row) | Timeline container, height 120px, border-top | `hXlH6` |
| `oLh4Q/controls` | `div` (flex row) | Left: Play button + Step button + "Day 47 of 365" label | `oLh4Q` |
| `oLh4Q/chart` | `BarChart` (Recharts) | 24-bar diffusion wave chart, color-coded bars by community | `oLh4Q` |
| `oLh4Q/label` | `div` | "Diffusion Wave Timeline" label | `oLh4Q` |
| `oLh4Q/speedBadge` | `Badge` | "5x Speed" badge, variant=secondary | `oLh4Q` |

### Zone 3: Conversations / Expert Agent

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `AoCh3` | `div` (flex row) | Conversations container, fills remaining height | `hXlH6` |
| `AoCh3/expertAgent` | `Card` | Expert Agent Analysis: brain icon, "Analyzing" badge (yellow), analysis text block | `AoCh3` |
| `AoCh3/conversationFeed` | `div` (flex col) | "Live Conversation Feed" title + scrollable list of conversation cards | `AoCh3` |
| `AoCh3/convCard1` | `Card` | Conversation card 1: agent avatar, message text, sentiment badge, timestamp | `AoCh3/conversationFeed` |
| `AoCh3/convCard2` | `Card` | Conversation card 2: agent avatar, message text, sentiment badge, timestamp | `AoCh3/conversationFeed` |
| `AoCh3/convCard3` | `Card` | Conversation card 3: agent avatar, message text, sentiment badge, timestamp | `AoCh3/conversationFeed` |

---

## 4. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-primary` | `#0f172a` | Graph engine background (dark center) |
| `--bg-gradient-end` | `#020617` | Radial gradient outer edge |
| `--bg-card` | `#ffffff` / `#1e293b` (dark) | Panel backgrounds (community, metrics) |
| `--community-alpha` | `#3b82f6` | Alpha community (blue) |
| `--community-beta` | `#22c55e` | Beta community (green) |
| `--community-gamma` | `#f97316` | Gamma community (orange) |
| `--community-delta` | `#a855f7` | Delta community (purple) |
| `--community-bridge` | `#ef4444` | Bridge community (red) |
| `--edge-default` | `#ffffff08` | Inter-community edge (very faint white) |
| `--edge-hover` | `#ffffff10` | Inter-community edge on hover |
| `--cascade-stroke` | per-community color | Cascade path stroke, 2px width |
| `--sentiment-positive` | `#22c55e` | Positive sentiment indicator |
| `--sentiment-neutral` | `#94a3b8` | Neutral sentiment indicator |
| `--sentiment-negative` | `#ef4444` | Negative sentiment indicator |
| `--live-badge` | `#ef4444` | LIVE indicator pulsing dot |
| `--cascade-glow` | `#22c55e` with `box-shadow` | Cascade badge active glow |
| `--polarization-gradient` | `linear-gradient(to right, #22c55e, #eab308, #ef4444)` | Polarization bar gradient |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Logo text | Geist | 16px | 700 (bold) |
| Panel titles | Geist | 14px | 600 (semibold) |
| Metric values | Geist (tabular-nums) | 24px | 700 (bold) |
| Metric labels | Geist | 12px | 400 (regular) |
| Community names | Geist | 13px | 500 (medium) |
| Agent count text | Geist | 12px | 400 (regular) |
| Status overlay text | Geist Mono | 11px | 400 (regular) |
| Graph title overlay | Instrument Serif | 18px | 700 (bold) |
| Graph subtitle | Geist | 12px | 400 (regular), opacity 0.6 |

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--control-bar-height` | `56px` | Zone 1 height |
| `--community-panel-width` | `260px` | Left panel width |
| `--metrics-panel-width` | `280px` | Right panel width |
| `--bottom-area-height` | `220px` | Zone 3 height |
| `--timeline-height` | `120px` | Timeline sub-zone height |
| `--panel-padding` | `16px` | Inner padding for all panels |
| `--card-gap` | `12px` | Gap between metric cards |
| `--community-item-height` | `48px` | Each community list item height |
| `--node-size-normal` | `5px` | Normal agent dot radius |
| `--node-size-influencer` | `10px` | Influencer dot radius with glow shadow |

---

## 5. Interaction Behavior

### Simulation Controls

| Action | Trigger | Effect |
|--------|---------|--------|
| Play | Click `playBtn` | Starts/resumes simulation step loop. Button toggles to Pause. Status badge updates to "Running". |
| Pause | Click `pauseBtn` | Pauses simulation. Status badge updates to "Paused". |
| Step | Click `stepBtn` | Advances simulation by exactly 1 step (day). Timeline indicator moves forward by 1. |
| Reset | Click `resetBtn` | Shows confirmation dialog ('Reset simulation? This cannot be undone.'). On confirm: POST /simulations/{id}/stop, status → 'created'. All metrics reset. |
| Replay | Click `replayBtn` | Replays from Day 0 at current speed setting, re-animating the graph and metrics. |
| Speed change | Click speed button (1x/2x/5x/10x) | Changes simulation tick interval. Active button gets highlighted state. |
| Scenario change | Select from `scenarioSelect` | Loads different scenario config. May trigger simulation reset with confirmation. |
| Run All | Click `runAllBtn` | POST /simulations/{id}/run-all. Runs all remaining steps. On completion: SimulationReportModal auto-opens. |
| Clone | Click `cloneBtn` | Copies simulation config to store.cloneConfig, navigates to /setup for re-run with pre-filled form. |
| Load Previous | Click `loadPrevBtn` | Opens searchable dropdown of past simulations. Click to load: GET /simulations/{id} + GET /simulations/{id}/steps. |
| Compare | Click `compareBtn` | Opens dropdown of other simulations. Click to navigate to /compare/:otherId. |

### Graph Interactions

| Action | Trigger | Effect |
|--------|---------|--------|
| Node hover | Mouse hover on agent dot | Shows `tTv8e` popup with agent details (name, influence, sentiment, connections, cascades, last message). Popup follows cursor offset. |
| Node click | Click on agent dot | Navigates to Agent Detail screen (UI-04) for that agent. |
| Community cluster hover | Mouse hover on cluster region | Highlights all nodes in that community, dims others. |
| Zoom in/out | Click +/- buttons or mouse wheel | Zooms graph canvas. Zoom level shown in status overlay. |
| Fullscreen | Click maximize button | Expands graph to full viewport, hides side panels. Press Escape or click again to restore. |
| Pan | Click-drag on empty canvas area | Pans the graph viewport. |
| Cascade path highlight | Active cascade detected | Cascade paths render as thicker colored lines (2px stroke) connecting affected nodes. `cmbzK` badge shows cascade number. |

### Community Panel

| Action | Trigger | Effect |
|--------|---------|--------|
| Filter | Type in `S24t3/search` | Filters community list in real-time. Graph dims non-matching communities. |
| Community click | Click community item | Highlights that community cluster in graph. Scrolls metrics to show community-specific data. |
| Community hover | Hover community item | Temporarily highlights community cluster with glow effect. |

### Metrics Panel

| Action | Trigger | Effect |
|--------|---------|--------|
| Influencer click | Click agent in Top Influencers list | Navigates to Agent Detail screen (UI-04). |
| Auto-update | WebSocket push on each step | All metric values animate to new values with transition. Progress bars smooth-fill. |

### Timeline

| Action | Trigger | Effect |
|--------|---------|--------|
| Bar hover | Hover on diffusion wave bar | Tooltip shows day number and diffusion count per community. |
| Bar click | Click on diffusion wave bar | Seeks simulation to that day (replay mode). |
| Scrub | Drag along timeline | Scrubs through simulation history, graph updates in real-time. |

### Conversations

| Action | Trigger | Effect |
|--------|---------|--------|
| New message | WebSocket push | New conversation card prepended to feed with slide-in animation. Old cards shift down. Max 20 visible. |
| Card click | Click conversation card | Navigates to Agent Detail (UI-04) for the speaking agent. |
| Expert update | Step completion | Expert agent analysis text updates with fade transition. "Analyzing" badge pulses during computation. |

### 5.5 Keyboard Shortcuts

#### Keyboard Shortcuts (ControlPanel)

Active when no input/textarea is focused:

| Key | Action |
|-----|--------|
| `Space` | Toggle Play/Pause |
| `ArrowRight` | Step forward one tick |
| `Escape` | Reset simulation (with confirmation) |

### 5.6 Overlay Components

#### Overlay Components

These components render as overlays/drawers within the SimulationPage:

| Component | Trigger | Position | Description |
|-----------|---------|----------|-------------|
| AgentInspector | Graph node click | Right drawer (360px) | Full agent detail + edit panel (when paused) |
| SimulationReportModal | status === 'completed' | Center modal | Auto-shown on completion. Export JSON/CSV, Run Again. |
| LLMDashboard | LLM Dashboard toggle | Bottom overlay | Provider stats, call counts, cache hit rate |
| InjectEventModal | Inject Event button | Center modal | Event type, content, controversy, target communities |
| ReplayModal | Replay button | Center modal | Target step slider |
| MonteCarloModal | Monte Carlo button | Center modal | Config → Running (polling) → Completed (results) |
| EngineControlPanel | Engine Control button | Dropdown below button | SLM/LLM ratio slider + 4 impact indicators |

---

## 6. Data Binding (Backend API)

| Component | API Endpoint | Method | Payload / Response |
|-----------|-------------|--------|-------------------|
| Status badge | `GET /simulations/{id}` | GET | `{ status, current_step, total_steps }` |
| Community list | `GET /simulations/{id}/communities` | GET | `[{ id, name, color, agent_count, avg_sentiment }]` |
| Graph data | `WS /simulations/{id}/ws` | WebSocket | `{ nodes: [...], edges: [...], cascades: [...] }` per step |
| Active agents | `GET /simulations/{id}/steps/{step}/metrics` | GET | `{ active_agents, total_agents }` |
| Sentiment distribution | `GET /simulations/{id}/steps/{step}/metrics` | GET | `{ sentiment: { positive, neutral, negative } }` |
| Polarization | `GET /simulations/{id}/steps/{step}/metrics` | GET | `{ polarization_index }` |
| Cascade stats | `GET /simulations/{id}/steps/{step}/metrics` | GET | `{ cascade_depth, cascade_width }` |
| Top influencers | `GET /simulations/{id}/agents?sort=influence_score&limit=10` | GET | `[{ id, name, community, influence_score }]` |
| Diffusion wave | `GET /simulations/{id}/steps` | GET | `[{ step, diffusion_counts_by_community }]` |
| Conversation feed | `WS /simulations/{id}/ws` | WebSocket | `{ conversations: [{ agent_id, message, sentiment, timestamp }] }` |
| Expert analysis | `WS /simulations/{id}/ws` | WebSocket | `{ expert_analysis: { text, status } }` |
| Simulation control | `POST /simulations/{id}/control` | POST | `{ action: "play"|"pause"|"step"|"reset"|"replay", speed: number }` |
| Scenario select | `GET /simulations/{id}/scenarios` | GET | `[{ id, name, description }]` |
| Node detail popup | `GET /simulations/{id}/agents/{agentId}` | GET | `{ name, influence, sentiment, connections, cascades, last_message }` |

---

## 7. Pencil Node Reference

All node IDs for auto-sync tracking with the Pencil design file:

| Node ID | Element | Zone |
|---------|---------|------|
| `FuHqi` | Root frame (1440x900) | -- |
| `ib0Jy` | Simulation Control Bar | Zone 1 |
| `nhMlv` | Middle Content container | Zone 2 |
| `S24t3` | Community Panel (left) | Zone 2 |
| `KrXVA` | AI Social World Graph Engine (center) | Zone 2 |
| `tTv8e` | Node detail popup (hover card) | Zone 2 (graph overlay) |
| `xUIlT` | Network legend (bottom-left of graph) | Zone 2 (graph overlay) |
| `cmbzK` | Cascade badge ("Cascade #47 Active") | Zone 2 (graph overlay) |
| `o4TMY` | Status overlay (FPS / nodes / edges / WebGL) | Zone 2 (graph overlay) |
| `MuKxh` | Real-Time Metrics Panel (right) | Zone 2 |
| `hXlH6` | Bottom Area container | Zone 3 |
| `oLh4Q` | Timeline + Diffusion Wave | Zone 3 |
| `AoCh3` | Conversations / Expert Agent | Zone 3 |
