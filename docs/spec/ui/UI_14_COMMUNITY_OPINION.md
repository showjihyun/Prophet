# UI-14 — Community Opinion Detail SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Community Opinion Detail (ID: YJMGR)

---

## 1. Overview

The Community Opinion Detail screen provides an in-depth view of opinions within a single community. It presents opinion clusters (grouped by topic) with stance breakdowns, and a feed of recent conversations. This is Level 2 in the opinion drill-down hierarchy (Scenario > **Community** > Conversation Thread).

Users arrive here by clicking "View Community" on a community card from UI-13 (Scenario Opinions Overview). They can drill further into individual conversation threads (UI-15).

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| Nav Bar                                                    [YJMGR/nav] |
| [<Back to Scenario] Korea Election 2026 > Alpha > Opinion              |
|                                          [Level 2 Community] [Settings]|
+------------------------------------------------------------------------+
| Header                                                  [YJMGR/header]|
| (●) Community Alpha    2,148 agents                                   |
| Sentiment +0.52  |  Conversations 312  |  Positive 67%                |
+------------------------------------------------------------------------+
| Body (2 columns)                                        [YJMGR/body]  |
| +-------------------------------+----------------------------------+   |
| | Left: Opinion Clusters (fill) | Right: Recent Conversations (460)|   |
| | [YJMGR/clusters]              | [YJMGR/conversations]           |   |
| |                                |                                  |   |
| | Filter: [Top Mentioned Topics] | "Recent Conversations" + count   |   |
| |                                |                                  |   |
| | +---------------------------+  | +------------------------------+ |   |
| | | Election Reform Policy    |  | | Debate on progressive tax    | |   |
| | | 847 agents                |  | | 🧑🧑 12 messages · 2h ago   | |   |
| | | Support 62% Neutral 24%  |  | +------------------------------+ |   |
| | | Oppose 14%   [====bar===]|  | | Economic policy fairness     | |   |
| | +---------------------------+  | | 🧑🧑 8 messages · 3h ago    | |   |
| | | Economic Inequality       |  | +------------------------------+ |   |
| | | 612 agents                |  | | Climate energy debate        | |   |
| | | Support 45% Neutral 31%  |  | | 🧑🧑 15 messages · 1h ago   | |   |
| | | Oppose 24%   [====bar===]|  | +------------------------------+ |   |
| | +---------------------------+  |                                  |   |
| | | Climate & Energy Policy   |  |                                  |   |
| | | 489 agents                |  |                                  |   |
| | | Support 38% Neutral 35%  |  |                                  |   |
| | | Oppose 27%   [====bar===]|  |                                  |   |
| | +---------------------------+  |                                  |   |
| +-------------------------------+----------------------------------+   |
+------------------------------------------------------------------------+
```

---

## 3. Components

### Navigation Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `YJMGR/nav` | `PageNav` | Top navigation with back, breadcrumb, level badge | `YJMGR` |
| `YJMGR/nav/backBtn` | `Button` | "Back to Scenario" ghost button | `YJMGR/nav` |
| `YJMGR/nav/breadcrumb` | `Breadcrumb` | "Korea Election 2026 > Alpha > Opinion" | `YJMGR/nav` |
| `YJMGR/nav/levelBadge` | `Badge` | "Level 2 Community" badge, blue variant | `YJMGR/nav` |
| `YJMGR/nav/settingsBtn` | `Button` | Settings icon, variant=ghost | `YJMGR/nav` |

### Header Section

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `YJMGR/header` | `div` (flex row) | Community name + stats row | `YJMGR` |
| `YJMGR/header/dot` | `span` | Community color dot (8px circle) | `YJMGR/header` |
| `YJMGR/header/name` | `h1` | Community name, font-display, text-2xl | `YJMGR/header` |
| `YJMGR/header/agentCount` | `span` | "2,148 agents" muted text | `YJMGR/header` |
| `YJMGR/header/stats` | `div` (flex row) | Inline stats: sentiment, conversations, positive % | `YJMGR/header` |

### Left Column — Opinion Clusters

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `YJMGR/clusters` | `div` (flex col) | Left column container, flex=1 | `YJMGR/body` |
| `YJMGR/clusters/title` | `div` (flex row) | "Opinion Clusters" heading + filter dropdown | `YJMGR/clusters` |
| `YJMGR/clusters/filter` | `Select` | "Top Mentioned Topics" filter dropdown | `YJMGR/clusters/title` |
| `YJMGR/clusters/list` | `div` (flex col) | Scrollable list of OpinionClusterCard components | `YJMGR/clusters` |

### OpinionClusterCard (Repeated Component)

| Property | Type | Description |
|----------|------|-------------|
| `topicName` | `string` | Cluster topic name |
| `description` | `string` | Brief description of the topic |
| `agentCount` | `number` | Number of agents in cluster |
| `stances` | `StanceBreakdown` | Support/Neutral/Oppose percentages |
| `stanceBar` | visual | Horizontal bar with 3-segment breakdown |

### StanceBreakdown

```typescript
interface StanceBreakdown {
  support: number;    // percentage 0-100
  neutral: number;
  oppose: number;
}
```

### Right Column — Recent Conversations

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `YJMGR/conversations` | `div` (flex col) | Right column container, width=460px | `YJMGR/body` |
| `YJMGR/conversations/title` | `div` (flex row) | "Recent Conversations" heading + count badge | `YJMGR/conversations` |
| `YJMGR/conversations/list` | `div` (flex col) | Scrollable list of ConversationItem components | `YJMGR/conversations` |

### ConversationItem (Repeated Component)

| Property | Type | Description |
|----------|------|-------------|
| `threadId` | `string` | Conversation thread ID |
| `topicTitle` | `string` | Topic/title of the conversation |
| `agentAvatars` | `string[]` | Array of agent IDs for avatar display |
| `messageCount` | `number` | Number of messages in thread |
| `timestamp` | `string` | Relative time (e.g., "2h ago") |
| `onClick` | `() => void` | Navigate to thread detail (UI-15) |

---

## 4. Design Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `font-display` | `'Instrument Serif', serif` | Community name heading |
| `font-body` | `'Geist', sans-serif` | All body text |
| `--card` | `#18181b` | Card backgrounds |
| `--border` | `#27272a` | Card/section borders |
| Right column width | `460px` | Fixed width for conversations column |
| Left column | `flex: 1` | Fills remaining space |
| Stance bar height | `8px` | Horizontal stance breakdown bar |
| Stance colors | Support=#22c55e, Neutral=#94a3b8, Oppose=#ef4444 | 3-segment bar |
| Card gap | `12px` | Gap between cluster/conversation cards |
| Level badge color | `blue` (#3b82f6) | Level 2 Community badge |

---

## 5. Interaction Behavior

| ID | Trigger | Action |
|----|---------|--------|
| INT-01 | Page load | Fetch community opinion clusters + recent conversations |
| INT-02 | Click conversation item | Navigate to `/opinions/:communityId/thread/:threadId` (UI-15) |
| INT-03 | Click "Back to Scenario" | Navigate to `/opinions` (UI-13) |
| INT-04 | Change topic filter | Re-sort/filter cluster cards |
| INT-05 | Hover cluster card | Subtle highlight border |
| INT-06 | Hover conversation item | Background highlight |

---

## 6. Data Binding

| Component | API Endpoint | Method |
|-----------|-------------|--------|
| Header stats | `GET /api/v1/simulations/:id/opinions/communities/:communityId` | GET |
| Opinion clusters | `GET /api/v1/simulations/:id/opinions/communities/:communityId/clusters` | GET |
| Recent conversations | `GET /api/v1/simulations/:id/opinions/communities/:communityId/conversations` | GET |

### Response Schema — Opinion Cluster

```typescript
interface OpinionCluster {
  cluster_id: string;
  topic_name: string;
  description: string;
  agent_count: number;
  stances: {
    support: number;    // percentage 0-100
    neutral: number;
    oppose: number;
  };
}
```

### Response Schema — Conversation Item

```typescript
interface ConversationItem {
  thread_id: string;
  topic_title: string;
  participant_ids: string[];
  message_count: number;
  timestamp: string;        // ISO 8601
  relative_time: string;    // "2h ago"
}
```

---

## 7. Pencil Node Reference

| Node ID | Description |
|---------|-------------|
| `YJMGR` | Frame root — Community Opinion Detail (1440x900) |
| `YJMGR/nav` | Navigation bar with Level 2 badge |
| `YJMGR/header` | Community name + inline stats |
| `YJMGR/clusters` | Left column — opinion cluster cards |
| `YJMGR/conversations` | Right column — recent conversations list |
