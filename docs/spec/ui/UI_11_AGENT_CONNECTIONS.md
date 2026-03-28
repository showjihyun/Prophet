# UI-11 — Agent Connections Tab SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Agent Connections Tab (ID: vJLFD)

---

## 1. Overview

The Agent Connections Tab screen shows the Agent Detail page (UI-04) with the "Connections" tab active. It replaces the Activity tab content with an ego-network graph visualization and a ranked list of the agent's direct connections. The ego-network graph uses the same dark-background WebGL rendering style as the main AI Social World graph (UI-01), centered on the selected agent with surrounding connected nodes colored by community. A right sidebar within the right panel displays a searchable, ranked list of top connections with trust and influence scores.

This SPEC extends UI-04. The left panel (agent profile) is identical; only the right panel content under the "Connections" tab is specified here. For the base layout, refer to `docs/spec/ui/UI_04_AGENT_DETAIL.md`.

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| Nav Bar                                                    [vJLFD/nav] |
| [<Back] Simulation > Community > Agent #3847       [Intervene] button  |
+------------------------------------------------------------------------+
| +-------------------+----------------------------------------------+   |
| | Left Panel (360px)| Right Panel (fill)               [vJLFD/right]| |
| | [vJLFD/left]      |                                              |   |
| |                   | Tab Bar: [Activity] [*Connections*] [Messages]|   |
| | [Avatar Circle]   | [vJLFD/tabs]                                 |   |
| | Agent #3847       +----------------------------------------------+   |
| | Community: Alpha  | +-------------------------------------+-----+   |
| |                   | | Ego Network Graph    [vJLFD/ego]    |Top  |   |
| | Quick Stats:      | | "Ego Network Graph"                |Conns|   |
| |  Influence: 98.2  | | "247 connections found"             |     |   |
| |  Connections: 247 | | [zoom][fit][filter] toolbar         |     |   |
| |  Subscribers: 12  | |                                     |     |   |
| |  Trust: 0.87      | |  ╭─── dark graph canvas ───╮        |[top |   |
| |                   | |  │  ○   ○                  │        |conns|   |
| | Personality Traits| |  │    ○  ●(center)  ○      │        |list]|   |
| |  Openness   ===== | |  │  ○    ○  ○   ○         │        |     |   |
| |  Skepticism ===   | |  │    ○      ○             │        |     |   |
| |  Adaptability ====| |  ╰────────────────────────╯        |     |   |
| |  Advocacy   ======| |                                     |     |   |
| |  Trust/Safety ====| +-------------------------------------+-----+   |
| |                   |                                              |   |
| | Memory Summary    |                                              |   |
| | [text card]       |                                              |   |
| +-------------------+----------------------------------------------+   |
+------------------------------------------------------------------------+
```

---

## 3. Components

### Navigation Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `vJLFD/nav` | `div` (flex row) | Top navigation bar with back button, breadcrumb, and action button (identical to UI-04) | `vJLFD` |
| `vJLFD/nav/backBtn` | `Button` | "Back" button with ChevronLeft icon, returns to previous screen | `vJLFD/nav` |
| `vJLFD/nav/breadcrumb` | `Breadcrumb` | "Simulation > Community > Agent #3847" with clickable segments | `vJLFD/nav` |
| `vJLFD/nav/interveneBtn` | `Button` | "Intervene" button, variant=default (primary), opens intervention modal (UI-10) | `vJLFD/nav` |

### Left Panel -- Agent Profile (identical to UI-04)

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `vJLFD/left` | `div` (flex col) | Left profile panel, width 360px, border-right (same structure as pkFYA/left) | `vJLFD` |
| `vJLFD/left/avatar` | `Avatar` (large) | Circle avatar, 80px diameter, community-colored border ring | `vJLFD/left` |
| `vJLFD/left/agentId` | `h2` | "Agent #3847" heading | `vJLFD/left` |
| `vJLFD/left/communityBadge` | `Badge` | Community name badge with color dot | `vJLFD/left` |
| `vJLFD/left/quickStats` | `div` (grid 2-col) | Quick Stats: Influence, Connections, Subscribers, Trust | `vJLFD/left` |
| `vJLFD/left/personalityTraits` | `div` (flex col) | Personality Traits: 5 progress bars (Openness, Skepticism, Adaptability, Advocacy, Trust/Safety) | `vJLFD/left` |
| `vJLFD/left/memorySummary` | `Card` | Memory Summary card with text content | `vJLFD/left` |

### Right Panel -- Connections Tab Content

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `vJLFD/right` | `div` (flex col) | Right content panel, flex=1 | `vJLFD` |
| `vJLFD/tabs` | `Tabs` | Tab bar with 3 tabs: "Activity", "Connections" (active), "Messages" | `vJLFD/right` |
| `vJLFD/tabs/activity` | `TabsTrigger` | "Activity" tab | `vJLFD/tabs` |
| `vJLFD/tabs/connections` | `TabsTrigger` | "Connections" tab (active state, underline indicator) | `vJLFD/tabs` |
| `vJLFD/tabs/messages` | `TabsTrigger` | "Messages" tab | `vJLFD/tabs` |

#### Ego Network Graph Area

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `vJLFD/ego` | `div` (flex row) | Ego network container, fills right panel below tabs, split into graph area + connections sidebar | `vJLFD/right` |
| `vJLFD/ego/graphSection` | `div` (flex col) | Graph section container, flex=1 | `vJLFD/ego` |
| `vJLFD/ego/graphHeader` | `div` (flex row) | Graph header: title + count + toolbar, space-between | `vJLFD/ego/graphSection` |
| `vJLFD/ego/graphTitle` | `h3` | "Ego Network Graph" heading | `vJLFD/ego/graphHeader` |
| `vJLFD/ego/graphCount` | `span` | "247 connections found" subtitle, muted-foreground | `vJLFD/ego/graphHeader` |
| `vJLFD/ego/toolbar` | `div` (flex row) | Graph toolbar: zoom, fit, filter icon buttons | `vJLFD/ego/graphHeader` |
| `vJLFD/ego/toolbarZoomIn` | `Button` | Zoom in button, variant=ghost, icon=ZoomIn | `vJLFD/ego/toolbar` |
| `vJLFD/ego/toolbarZoomOut` | `Button` | Zoom out button, variant=ghost, icon=ZoomOut | `vJLFD/ego/toolbar` |
| `vJLFD/ego/toolbarFit` | `Button` | Fit to view button, variant=ghost, icon=Maximize2 | `vJLFD/ego/toolbar` |
| `vJLFD/ego/toolbarFilter` | `Button` | Filter by community button, variant=ghost, icon=Filter | `vJLFD/ego/toolbar` |
| `vJLFD/ego/canvas` | `div` (relative) | Dark graph canvas area, bg=radial-gradient same as UI-01 graph engine, rounded-lg, border | `vJLFD/ego/graphSection` |

##### Ego Network Graph Nodes (virtual, rendered via Cytoscape.js)

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `vJLFD/ego/centerNode` | (virtual) | Center node: this agent, ~20px diameter, blue with glow effect (box-shadow blur 16px), white stroke 1.5px | `vJLFD/ego/canvas` |
| `vJLFD/ego/connectedNodes` | (virtual, repeated) | Connected agent nodes, 6-10px diameter, colored by community (Alpha=blue, Beta=green, Gamma=orange, Delta=purple, Bridge=red) | `vJLFD/ego/canvas` |
| `vJLFD/ego/edges` | (virtual, repeated) | Edges between center node and connected nodes, stroke 0.5-1px, opacity based on trust weight (higher trust = more opaque) | `vJLFD/ego/canvas` |

#### Top Connections Sidebar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `vJLFD/ego/connSidebar` | `div` (flex col) | Top connections sidebar, width 280px, border-left, bg=card, padding 16px | `vJLFD/ego` |
| `vJLFD/ego/connSidebar/title` | `h3` | "Top Connections" heading, font-semibold | `vJLFD/ego/connSidebar` |
| `vJLFD/ego/connSidebar/search` | `Input` | Search input, placeholder "Search connections...", icon=Search | `vJLFD/ego/connSidebar` |
| `vJLFD/ego/connSidebar/list` | `div` (flex col) | Scrollable list of connection items, gap 8px | `vJLFD/ego/connSidebar` |
| `vJLFD/ego/connItem` | `div` (flex row, repeated) | Individual connection item: avatar + info + scores, padding 8px, hover highlight, rounded | `vJLFD/ego/connSidebar/list` |
| `vJLFD/ego/connItem/avatar` | `Avatar` (small) | 32px agent avatar circle, community-colored | `vJLFD/ego/connItem` |
| `vJLFD/ego/connItem/info` | `div` (flex col) | Agent name + community badge, flex=1 | `vJLFD/ego/connItem` |
| `vJLFD/ego/connItem/name` | `span` | Agent name/ID, font-medium | `vJLFD/ego/connItem/info` |
| `vJLFD/ego/connItem/communityBadge` | `Badge` | Community badge (small), variant=secondary, with community color dot | `vJLFD/ego/connItem/info` |
| `vJLFD/ego/connItem/scores` | `div` (flex col) | Trust score + Influence score, right-aligned | `vJLFD/ego/connItem` |
| `vJLFD/ego/connItem/trustScore` | `span` | "Trust: {value}" label + value, font-mono, small | `vJLFD/ego/connItem/scores` |
| `vJLFD/ego/connItem/influenceScore` | `span` | "Influence: {value}" label + value, font-mono, small | `vJLFD/ego/connItem/scores` |

---

## 4. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--bg-page` | `#f8fafc` / `#0f172a` (dark) | Page background |
| `--bg-card` | `#ffffff` / `#1e293b` (dark) | Card and sidebar backgrounds |
| `--bg-graph` | radial-gradient: `#0f172a` -> `#020617` | Ego graph canvas background (matches UI-01) |
| `--community-alpha` | `#3b82f6` | Alpha community nodes and badges |
| `--community-beta` | `#22c55e` | Beta community nodes and badges |
| `--community-gamma` | `#f97316` | Gamma community nodes and badges |
| `--community-delta` | `#a855f7` | Delta community nodes and badges |
| `--community-bridge` | `#ef4444` | Bridge community nodes and badges |
| `--center-node-glow` | `#3b82f640` | Center node glow effect (blue 25% opacity) |
| `--center-node-stroke` | `#ffffff` | Center node white stroke |
| `--edge-default` | `#ffffff15` | Default edge color (faint white) |
| `--edge-strong` | `#ffffff40` | High-trust edge color (brighter white) |
| `--edge-weak` | `#ffffff08` | Low-trust edge color (very faint) |
| `--conn-item-hover` | `var(--accent)` | Connection list item hover background |
| `--score-text` | `var(--muted-foreground)` | Score label text color |
| `--score-value` | `var(--foreground)` | Score value text color |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Graph title | Instrument Serif | 16px | 600 |
| Connection count | Geist | 13px | 400 |
| Connection item name | Geist | 14px | 500 |
| Community badge text | Geist | 11px | 500 |
| Trust/Influence score label | Geist | 11px | 400 |
| Trust/Influence score value | Geist Mono | 12px | 500 |
| Search placeholder | Geist | 13px | 400 |
| Tab trigger | Geist | 14px | 500 |

Inherits additional typography from UI-04 for left panel elements.

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--left-panel-width` | `360px` | Left profile panel width |
| `--conn-sidebar-width` | `280px` | Top connections sidebar width |
| `--graph-padding` | `16px` | Graph section inner padding |
| `--graph-canvas-radius` | `8px` | Graph canvas border radius |
| `--conn-sidebar-padding` | `16px` | Connections sidebar inner padding |
| `--conn-item-padding` | `8px` | Connection item inner padding |
| `--conn-item-gap` | `8px` | Gap between connection list items |
| `--conn-avatar-size` | `32px` | Connection item avatar size |
| `--center-node-size` | `20px` | Center agent node diameter |
| `--connected-node-min` | `6px` | Minimum connected node diameter |
| `--connected-node-max` | `10px` | Maximum connected node diameter (influencers) |
| `--toolbar-btn-size` | `32px` | Toolbar icon button size |
| `--toolbar-gap` | `4px` | Gap between toolbar buttons |

---

## 5. Interaction Behavior

### Tab and Navigation

| Action | Trigger | Effect |
|--------|---------|--------|
| Tab switch | Click "Connections" tab | Right panel content switches to ego graph + connections sidebar. Tab underline indicator animates to Connections tab. |
| Back navigation | Click back button or breadcrumb | Returns to previous screen. |
| Intervene | Click "Intervene" button | Opens Agent Intervene Modal (UI-10). |

### Ego Network Graph

| Action | Trigger | Effect |
|--------|---------|--------|
| Node hover | Hover on a connected node | Node enlarges slightly (1.5x). Tooltip shows: agent ID, community, trust score. Connected edge highlights (brighter). |
| Node click | Click on a connected node | Navigates to Agent Detail (UI-04) for that agent. |
| Center node | Always visible | Center node has permanent glow effect. Hovering shows this agent's full stats tooltip. Not clickable (already on this agent's page). |
| Zoom in | Click zoom in toolbar button or mouse wheel up | Zooms into graph canvas. Min zoom: fit all nodes. Max zoom: 5x. |
| Zoom out | Click zoom out toolbar button or mouse wheel down | Zooms out of graph canvas. |
| Fit to view | Click fit toolbar button | Resets zoom and pan to fit all nodes in viewport with padding. |
| Filter by community | Click filter toolbar button | Opens small popover with community checkboxes. Unchecked communities' nodes and edges are hidden from graph. |
| Pan | Click-drag on empty canvas area | Pans the graph viewport. |
| Edge hover | Hover on an edge | Edge brightens. Tooltip shows trust weight value between the two agents. |

### Top Connections Sidebar

| Action | Trigger | Effect |
|--------|---------|--------|
| Search connections | Type in search input | Filters connection list in real-time. Matches against agent ID/name and community. Debounce 200ms. |
| Connection item hover | Hover on a connection item | Item background highlights. Corresponding node in ego graph highlights with glow. |
| Connection item click | Click a connection item | Navigates to Agent Detail (UI-04) for that agent. |
| Scroll list | Scroll within connections sidebar | Virtual scrolling for performance with 247+ connections. Loads more items as user scrolls. |
| Sort order | Default | Sorted by trust score descending. |

### Real-time Updates

| Action | Trigger | Effect |
|--------|---------|--------|
| New connection | WebSocket push | New node appears in ego graph with fade-in animation. Connection list updates. Count increments. |
| Connection removed | WebSocket push | Node removed from ego graph with fade-out. List updates. Count decrements. |
| Trust change | WebSocket push | Edge opacity/thickness adjusts. Connection list re-sorts if rank changes. |

---

## 6. Data Binding (Backend API)

| Component | API Endpoint | Method | Payload / Response |
|-----------|-------------|--------|-------------------|
| Agent profile (left panel) | `GET /simulations/{id}/agents/{agentId}` | GET | `{ id, community, influence_score, connections_count, subscribers_count, trust_level, personality, status }` |
| Ego network graph | `GET /simulations/{id}/network?ego={agentId}` | GET | `{ nodes: [{ id, community, influence_score, x, y }], edges: [{ source, target, trust_weight }], center: agentId }` |
| Top connections list | `GET /simulations/{id}/agents/{agentId}/connections?sort=trust_score&limit=50` | GET | `[{ agent_id, name, community, trust_score, influence_score, last_interaction }]` |
| Search connections | `GET /simulations/{id}/agents/{agentId}/connections?search={q}&sort=trust_score` | GET | Filtered connection list |
| Memory summary | `GET /simulations/{id}/agents/{agentId}/memory` | GET | `{ text }` |
| Intervention | Opens UI-10 modal | -- | See UI-10 SPEC |
| Real-time updates | `WS /simulations/{id}/ws` | WebSocket | Ego network node/edge additions, removals, trust changes |

---

## 7. Pencil Node Reference

| Node ID | Element | Section |
|---------|---------|---------|
| `vJLFD` | Root frame (1440x900) | -- |
| `vJLFD/nav` | Navigation bar with back + breadcrumb + intervene | Top |
| `vJLFD/left` | Agent profile panel (left, 360px) | Left |
| `vJLFD/right` | Connections tab content (right) | Right |
| `vJLFD/tabs` | Tab bar (Activity / Connections* / Messages) | Right panel top |
| `vJLFD/ego` | Ego network container (graph + sidebar) | Right panel content |
| `vJLFD/ego/canvas` | Dark graph canvas (Cytoscape.js) | Graph area |
| `vJLFD/ego/centerNode` | Center agent node (20px, blue glow) | Graph virtual |
| `vJLFD/ego/connSidebar` | Top Connections sidebar (280px) | Right of graph |
