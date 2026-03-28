# UI-04 — Agent Detail SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Agent Detail (ID: pkFYA)

---

## 1. Overview

The Agent Detail screen provides an in-depth view of a single agent's profile, personality traits, memory summary, sentiment history, and interaction log. It is the primary drill-down destination when clicking an agent from the graph, influencer table, or conversation feed. The screen also offers an "Intervene" action allowing users to inject events or modify the agent's state during a running simulation.

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| Nav Bar                                                    [pkFYA/nav] |
| [<Back] Simulation > Community > Agent #3847       [Intervene] button  |
+------------------------------------------------------------------------+
| +-------------------+----------------------------------------------+   |
| | Left Panel (360px)| Right Panel (fill)               [pkFYA/right]|  |
| | [pkFYA/left]      |                                              |   |
| |                   | Tab Bar: [Activity] [Connections] [Messages]  |   |
| | [Avatar Circle]   | [pkFYA/tabs]                                 |   |
| | Agent #3847       +----------------------------------------------+   |
| | Community: Alpha  | Sentiment Over Time (Line Chart)              |   |
| |                   | [pkFYA/sentimentChart]                        |   |
| | Quick Stats:      |                                              |   |
| |  Influence: 98.2  +----------------------------------------------+   |
| |  Connections: 247 | Recent Interactions (Table)                   |   |
| |  Subscribers: 12  | [pkFYA/interactions]                         |   |
| |  Trust: 0.87      | Target | Type | Sentiment | Message | Time   |   |
| |                   | ...    | ...  | ...       | ...     | ...    |   |
| | Personality Traits|                                              |   |
| |  Openness   ===== |                                              |   |
| |  Skepticism ===   |                                              |   |
| |  Adaptability ====|                                              |   |
| |  Advocacy   ======|                                              |   |
| |  Trust/Safety ====|                                              |   |
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
| `pkFYA/nav` | `div` (flex row) | Top navigation bar with back button, breadcrumb, and action button | `pkFYA` |
| `pkFYA/nav/backBtn` | `Button` | "Back" button with ChevronLeft icon, returns to previous screen | `pkFYA/nav` |
| `pkFYA/nav/breadcrumb` | `Breadcrumb` | "Simulation > Community > Agent #3847" with clickable segments | `pkFYA/nav` |
| `pkFYA/nav/interveneBtn` | `Button` | "Intervene" button, variant=default (primary), opens intervention modal | `pkFYA/nav` |

### Left Panel -- Agent Profile

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `pkFYA/left` | `div` (flex col) | Left profile panel, width 360px, border-right | `pkFYA` |
| `pkFYA/left/avatar` | `Avatar` (large) | Circle avatar, 80px diameter, displays agent number centered, community-colored border ring | `pkFYA/left` |
| `pkFYA/left/agentId` | `h2` | "Agent #3847" heading | `pkFYA/left` |
| `pkFYA/left/communityBadge` | `Badge` | Community name badge with community color dot (e.g., "Alpha" with blue dot) | `pkFYA/left` |
| `pkFYA/left/quickStats` | `div` (grid 2-col) | Quick Stats section with 4 stat items | `pkFYA/left` |
| `pkFYA/left/statInfluence` | `div` | "Influence" label + value "98.2" (bold) | `pkFYA/left/quickStats` |
| `pkFYA/left/statConnections` | `div` | "Connections" label + value "247" (bold) | `pkFYA/left/quickStats` |
| `pkFYA/left/statSubscribers` | `div` | "Subscribers" label + value "12" (bold) | `pkFYA/left/quickStats` |
| `pkFYA/left/statTrust` | `div` | "Trust Level" label + value "0.87" (bold) | `pkFYA/left/quickStats` |
| `pkFYA/left/personalityTitle` | `h3` | "Personality Traits" section heading | `pkFYA/left` |
| `pkFYA/left/traitOpenness` | `div` (flex row) | "Openness" label + horizontal progress bar + percentage text | `pkFYA/left` |
| `pkFYA/left/traitSkepticism` | `div` (flex row) | "Skepticism" label + horizontal progress bar + percentage text | `pkFYA/left` |
| `pkFYA/left/traitAdaptability` | `div` (flex row) | "Adaptability" label + horizontal progress bar + percentage text | `pkFYA/left` |
| `pkFYA/left/traitAdvocacy` | `div` (flex row) | "Advocacy" label + horizontal progress bar + percentage text | `pkFYA/left` |
| `pkFYA/left/traitTrustSafety` | `div` (flex row) | "Trust/Safety" label + horizontal progress bar + percentage text | `pkFYA/left` |
| `pkFYA/left/memorySummary` | `Card` | "Memory Summary" card with text content showing agent's recent memory synopsis | `pkFYA/left` |

### Right Panel -- Agent Activity & Interactions

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `pkFYA/right` | `div` (flex col) | Right content panel, flex=1 | `pkFYA` |
| `pkFYA/tabs` | `Tabs` | Tab bar with 3 tabs: "Activity", "Connections", "Messages" | `pkFYA/right` |
| `pkFYA/tabs/activity` | `TabsTrigger` | "Activity" tab (default active) | `pkFYA/tabs` |
| `pkFYA/tabs/connections` | `TabsTrigger` | "Connections" tab | `pkFYA/tabs` |
| `pkFYA/tabs/messages` | `TabsTrigger` | "Messages" tab | `pkFYA/tabs` |

#### Activity Tab Content

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `pkFYA/sentimentChart` | `Card` | "Sentiment Over Time" card containing line chart | `pkFYA/right` |
| `pkFYA/sentimentChart/chart` | `LineChart` (Recharts) | Line chart: X-axis=simulation days, Y-axis=sentiment (-1 to +1). Two lines: Positive (green #22c55e), Negative (red #ef4444). Area fill with low opacity. Tooltip on hover shows exact values per day. | `pkFYA/sentimentChart` |
| `pkFYA/interactions` | `Card` | "Recent Interactions" card containing interaction table | `pkFYA/right` |
| `pkFYA/interactions/table` | `Table` | Interaction log table, most recent first | `pkFYA/interactions` |
| `pkFYA/interactions/colTarget` | `TableColumn` | "Target Agent" -- Agent ID of interaction partner, clickable link | `pkFYA/interactions/table` |
| `pkFYA/interactions/colType` | `TableColumn` | "Type" -- Interaction type: "Share", "Reply", "Mention", "Influence" | `pkFYA/interactions/table` |
| `pkFYA/interactions/colSentiment` | `TableColumn` | "Sentiment" -- Badge: Positive (green), Neutral (gray), Negative (red) | `pkFYA/interactions/table` |
| `pkFYA/interactions/colMessage` | `TableColumn` | "Message Preview" -- Truncated message text (max 60 chars), expandable on click | `pkFYA/interactions/table` |
| `pkFYA/interactions/colTime` | `TableColumn` | "Time" -- Relative timestamp (e.g., "2h ago", "Day 45") | `pkFYA/interactions/table` |

#### Connections Tab Content (visible when "Connections" tab is active)

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `pkFYA/connectionsGraph` | `div` | Mini force-directed graph showing this agent's ego network (direct connections) rendered via Cytoscape.js | `pkFYA/right` |
| `pkFYA/connectionsList` | `Table` | List of connected agents: Agent ID, Community, Relationship Strength, Last Interaction | `pkFYA/right` |

#### Messages Tab Content (visible when "Messages" tab is active)

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `pkFYA/messagesFeed` | `div` (flex col) | Chronological feed of all messages sent/received by this agent | `pkFYA/right` |
| `pkFYA/messageCard` | `Card` (repeated) | Individual message card: sender/receiver, message text, sentiment, timestamp | `pkFYA/messagesFeed` |

### Intervention Modal (opened by Intervene button)

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `pkFYA/interventionModal` | `Dialog` | Modal dialog for agent intervention | `pkFYA` |
| `pkFYA/interventionModal/typeSelect` | `Select` | Intervention type: "Inject Message", "Modify Sentiment", "Change Community", "Boost Influence" | `pkFYA/interventionModal` |
| `pkFYA/interventionModal/paramFields` | `div` | Dynamic parameter fields based on selected intervention type | `pkFYA/interventionModal` |
| `pkFYA/interventionModal/submitBtn` | `Button` | "Apply Intervention" button, variant=default | `pkFYA/interventionModal` |
| `pkFYA/interventionModal/cancelBtn` | `Button` | "Cancel" button, variant=outline | `pkFYA/interventionModal` |

---

## 4. Design Tokens

### Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--community-alpha` | `#3b82f6` | Alpha community badge, avatar ring |
| `--community-beta` | `#22c55e` | Beta community badge, avatar ring |
| `--community-gamma` | `#f97316` | Gamma community badge, avatar ring |
| `--community-delta` | `#a855f7` | Delta community badge, avatar ring |
| `--community-bridge` | `#ef4444` | Bridge community badge, avatar ring |
| `--bg-page` | `#f8fafc` / `#0f172a` (dark) | Page background |
| `--bg-card` | `#ffffff` / `#1e293b` (dark) | Card backgrounds |
| `--bg-left-panel` | `#ffffff` / `#1e293b` (dark) | Left profile panel background |
| `--sentiment-positive` | `#22c55e` | Positive sentiment line, badge, and area fill |
| `--sentiment-negative` | `#ef4444` | Negative sentiment line, badge, and area fill |
| `--sentiment-neutral` | `#94a3b8` | Neutral sentiment badge |
| `--trait-bar-bg` | `#e2e8f0` / `#334155` (dark) | Personality trait progress bar track |
| `--trait-bar-fill` | `#3b82f6` | Personality trait progress bar fill |
| `--interaction-share` | `#3b82f6` | "Share" type indicator |
| `--interaction-reply` | `#22c55e` | "Reply" type indicator |
| `--interaction-mention` | `#f97316` | "Mention" type indicator |
| `--interaction-influence` | `#a855f7` | "Influence" type indicator |
| `--intervene-btn` | primary color | Intervene button |
| `--avatar-size` | `80px` | Avatar circle diameter |
| `--avatar-ring-width` | `3px` | Avatar community color ring width |

### Typography

| Element | Font | Size | Weight |
|---------|------|------|--------|
| Agent ID heading | Instrument Serif | 24px | 700 |
| Quick stat value | Geist (tabular-nums) | 20px | 700 |
| Quick stat label | Geist | 12px | 400 |
| Personality trait label | Geist | 13px | 400 |
| Personality trait percentage | Geist (tabular-nums) | 12px | 600 |
| Section heading (h3) | Instrument Serif | 14px | 600 |
| Table header | Geist | 13px | 600 |
| Table body cell | Geist | 13px | 400 |
| Memory summary text | Geist | 13px | 400, line-height 1.5 |
| Chart axis labels | Geist | 11px | 400 |
| Tab trigger | Geist | 14px | 500 |

### Spacing

| Token | Value | Usage |
|-------|-------|-------|
| `--left-panel-width` | `360px` | Left profile panel width |
| `--left-panel-padding` | `24px` | Left panel inner padding |
| `--right-panel-padding` | `24px` | Right panel inner padding |
| `--trait-bar-height` | `8px` | Personality trait bar height |
| `--trait-gap` | `12px` | Gap between personality trait rows |
| `--stat-grid-gap` | `16px` | Gap between quick stat items |
| `--section-gap` | `24px` | Gap between sections in left panel |
| `--table-row-height` | `48px` | Interaction table row height |

---

## 5. Interaction Behavior

| Action | Trigger | Effect |
|--------|---------|--------|
| Back navigation | Click back button or breadcrumb segment | Returns to previous screen (simulation main, influencer list, etc.) |
| Tab switch | Click "Activity" / "Connections" / "Messages" tab | Switches right panel content with fade transition. Tab indicator underline animates to selected tab. |
| Sentiment chart hover | Hover on chart line/area | Tooltip shows: "Day {n}: Positive {val}, Negative {val}" |
| Sentiment chart zoom | Mouse wheel on chart | Zooms X-axis to show smaller day range. Drag to pan. |
| Target agent click | Click agent ID in interactions table | Navigates to Agent Detail (UI-04) for that agent. |
| Message expand | Click message preview in table | Expands row to show full message text inline. |
| Intervene button | Click "Intervene" button | Opens intervention modal dialog. |
| Intervention submit | Fill form and click "Apply Intervention" | POST intervention to backend. Modal closes. Toast notification confirms: "Intervention applied to Agent #3847". Agent data refreshes. |
| Intervention cancel | Click "Cancel" or close modal | Closes modal without changes. |
| Personality trait hover | Hover on a trait bar | Tooltip shows exact value and percentile rank among all agents. |
| Memory summary | Auto-loads on page mount | Fetches agent memory summary from backend. Shows loading skeleton while fetching. |
| Connections graph (tab) | Switch to "Connections" tab | Loads and renders ego network mini-graph for this agent. Nodes are clickable to navigate to other agents. |
| Messages feed (tab) | Switch to "Messages" tab | Loads chronological message feed. Scroll to load more (infinite scroll). |
| Real-time updates | WebSocket push | Sentiment chart appends new data point. Interactions table prepends new entries. Quick stats update. |

---

## 6. Data Binding (Backend API)

| Component | API Endpoint | Method | Payload / Response |
|-----------|-------------|--------|-------------------|
| Agent profile | `GET /simulations/{id}/agents/{agentId}` | GET | `{ id, community, influence_score, connections_count, subscribers_count, trust_level, personality: { openness, skepticism, adaptability, advocacy, trust_safety }, status }` |
| Community badge | `GET /simulations/{id}/communities/{communityId}` | GET | `{ name, color }` |
| Memory summary | `GET /simulations/{id}/agents/{agentId}/memory` | GET | `{ episodic_summary, semantic_summary, social_summary, text }` |
| Sentiment over time | `GET /simulations/{id}/agents/{agentId}/sentiment-history` | GET | `[{ step, positive, negative }]` |
| Recent interactions | `GET /simulations/{id}/agents/{agentId}/interactions?limit=50` | GET | `[{ target_agent_id, type, sentiment, message_preview, timestamp }]` |
| Connections list | `GET /simulations/{id}/agents/{agentId}/connections` | GET | `[{ agent_id, community, strength, last_interaction }]` |
| Ego network graph | `GET /simulations/{id}/agents/{agentId}/ego-network` | GET | `{ nodes: [...], edges: [...] }` |
| Messages feed | `GET /simulations/{id}/agents/{agentId}/messages?page={p}` | GET | `{ items: [{ sender, receiver, text, sentiment, timestamp }], total, page }` |
| Intervention | `POST /simulations/{id}/agents/{agentId}/intervene` | POST | `{ type, params }` -> `{ success, message }` |
| Real-time updates | `WS /simulations/{id}/ws` | WebSocket | Agent-specific state updates per step |

---

## 7. Pencil Node Reference

| Node ID | Element | Section |
|---------|---------|---------|
| `pkFYA` | Root frame (1440x900) | -- |
| `pkFYA/nav` | Navigation bar with back + breadcrumb + intervene | Top |
| `pkFYA/left` | Agent profile panel (left, 360px) | Left |
| `pkFYA/left/avatar` | Agent avatar circle | Left panel |
| `pkFYA/left/quickStats` | Quick stats grid (4 items) | Left panel |
| `pkFYA/left/traitOpenness` | Openness personality bar | Left panel |
| `pkFYA/left/traitSkepticism` | Skepticism personality bar | Left panel |
| `pkFYA/left/traitAdaptability` | Adaptability personality bar | Left panel |
| `pkFYA/left/traitAdvocacy` | Advocacy personality bar | Left panel |
| `pkFYA/left/traitTrustSafety` | Trust/Safety personality bar | Left panel |
| `pkFYA/left/memorySummary` | Memory summary card | Left panel |
| `pkFYA/right` | Activity & interactions panel (right) | Right |
| `pkFYA/tabs` | Tab bar (Activity / Connections / Messages) | Right panel |
| `pkFYA/sentimentChart` | Sentiment over time chart | Right panel (Activity tab) |
| `pkFYA/interactions` | Recent interactions table | Right panel (Activity tab) |
| `pkFYA/interventionModal` | Intervention modal dialog | Overlay |
