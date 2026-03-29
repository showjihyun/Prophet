# UI-15 — Conversation Thread SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Conversation Thread (ID: q6TDI)

---

## 1. Overview

The Conversation Thread screen displays a full conversation between agents on a specific topic within a community. It shows individual agent messages with sentiment badges, reaction counts, and reply chains. This is Level 3 in the opinion drill-down hierarchy (Scenario > Community > **Conversation Thread**).

Users arrive here by clicking a conversation item from UI-14 (Community Opinion Detail). The thread view provides insight into how agents debate, agree, and influence each other on specific topics.

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| Nav Bar                                                    [q6TDI/nav] |
| [<Back to Community] Korea Election 2026 / Alpha / Conversation        |
|                                            [Level 3] (purple)          |
+------------------------------------------------------------------------+
| Header                                                  [q6TDI/header]|
| "Debate on progressive taxation reform impact"                         |
| [Election Reform] tag    Participants: 8    Timespan: 2h 15m           |
|                                    Participants 8  |  Avg Sentiment +0.2|
+------------------------------------------------------------------------+
| Thread Body (scrollable)                            [q6TDI/thread]     |
| +------------------------------------------------------------------+   |
| | Message 1                                         [q6TDI/msg1]   |   |
| | (●) Agent-A042  [Progressive]  2h ago                            |   |
| | "The progressive taxation reform would significantly reduce..."   |   |
| | 👍 Agree 12  |  👎 Disagree 3  |  🤔 Nuanced 5                  |   |
| +------------------------------------------------------------------+   |
| | Message 2                                         [q6TDI/msg2]   |   |
| | (●) Agent-B091  [Conservative]  1h 50m ago                       |   |
| | "While I understand the intent, the economic impact on..."        |   |
| | 👍 Agree 8   |  👎 Disagree 7  |  🤔 Nuanced 3                  |   |
| +------------------------------------------------------------------+   |
| |   Reply (indented)                               [q6TDI/reply1]  |   |
| |   (●) Agent-A042  [Progressive]  1h 45m ago                      |   |
| |   "That's a valid concern, but consider the data from..."         |   |
| |   👍 Agree 6   |  👎 Disagree 2  |  🤔 Nuanced 4                |   |
| +------------------------------------------------------------------+   |
| | Message 3                                         [q6TDI/msg3]   |   |
| | (●) Agent-G055  [Neutral]  1h 30m ago                            |   |
| | "Both sides make valid points. The key question is..."            |   |
| | 👍 Agree 15  |  👎 Disagree 1  |  🤔 Nuanced 8                  |   |
| +------------------------------------------------------------------+   |
+------------------------------------------------------------------------+
```

---

## 3. Components

### Navigation Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `q6TDI/nav` | `PageNav` | Top navigation with back, breadcrumb, Level 3 badge | `q6TDI` |
| `q6TDI/nav/backBtn` | `Button` | "Back to Community" ghost button | `q6TDI/nav` |
| `q6TDI/nav/breadcrumb` | `Breadcrumb` | "Korea Election 2026 / Alpha / Conversation" | `q6TDI/nav` |
| `q6TDI/nav/levelBadge` | `Badge` | "Level 3" badge, purple variant | `q6TDI/nav` |

### Header Section

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `q6TDI/header` | `div` (flex col) | Thread header with topic + metadata | `q6TDI` |
| `q6TDI/header/topic` | `h1` | Thread topic title, font-display, text-xl | `q6TDI/header` |
| `q6TDI/header/tag` | `Badge` | Topic category tag (e.g., "Election Reform"), variant=secondary | `q6TDI/header` |
| `q6TDI/header/participants` | `span` | "Participants: 8" with Users icon | `q6TDI/header` |
| `q6TDI/header/timespan` | `span` | "Timespan: 2h 15m" with Clock icon | `q6TDI/header` |
| `q6TDI/header/rightStats` | `div` (flex row) | Right-aligned: participant count + avg sentiment badge | `q6TDI/header` |
| `q6TDI/header/avgSentiment` | `Badge` | "Avg Sentiment +0.2", colored by value | `q6TDI/header/rightStats` |

### Thread Body

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `q6TDI/thread` | `div` (flex col) | Scrollable thread container | `q6TDI` |
| `q6TDI/thread/messages` | `div` (flex col) | List of ThreadMessage components | `q6TDI/thread` |

### ThreadMessage (Repeated Component)

| Property | Type | Description |
|----------|------|-------------|
| `messageId` | `string` | Unique message identifier |
| `agentId` | `string` | Agent identifier |
| `communityColor` | `string` | CSS variable for agent's community color |
| `stanceBadge` | `"Progressive" \| "Conservative" \| "Neutral"` | Agent's stance on the topic |
| `timestamp` | `string` | Relative time (e.g., "2h ago") |
| `content` | `string` | Message body text |
| `reactions` | `Reactions` | Agree/Disagree/Nuanced counts |
| `isReply` | `boolean` | If true, render indented as a reply |
| `replyToId` | `string?` | Parent message ID if reply |

### Reactions

```typescript
interface Reactions {
  agree: number;
  disagree: number;
  nuanced: number;
}
```

### Stance Badge Colors

| Stance | Background | Text |
|--------|-----------|------|
| Progressive | `bg-blue-500/20` | `text-blue-400` |
| Conservative | `bg-red-500/20` | `text-red-400` |
| Neutral | `bg-gray-500/20` | `text-gray-400` |

---

## 4. Design Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `font-display` | `'Instrument Serif', serif` | Thread topic title |
| `font-body` | `'Geist', sans-serif` | Message content + all body text |
| `--card` | `#18181b` | Message card background |
| `--border` | `#27272a` | Message dividers |
| Level badge color | purple (#a855f7) | Level 3 badge |
| Reply indent | `48px` | Left padding for reply messages |
| Avatar size | `36px` | Agent avatar circle |
| Message gap | `0` | Messages separated by border dividers, not gap |
| Reaction icon size | `14px` | Thumbs up/down/thinking icons |
| Reaction text | `text-xs` | Reaction count labels |
| Message padding | `20px 24px` | Inner padding per message |

---

## 5. Interaction Behavior

| ID | Trigger | Action |
|----|---------|--------|
| INT-01 | Page load | Fetch full conversation thread from API |
| INT-02 | Click "Back to Community" | Navigate to `/opinions/:communityId` (UI-14) |
| INT-03 | Click agent ID | Navigate to agent detail `/agents/:agentId` (UI-04) |
| INT-04 | Scroll thread | Infinite scroll / load more messages |
| INT-05 | Hover message | Subtle background highlight |
| INT-06 | Click reaction count | Show breakdown tooltip (future) |

---

## 6. Data Binding

| Component | API Endpoint | Method |
|-----------|-------------|--------|
| Thread header | `GET /api/v1/simulations/:id/opinions/threads/:threadId` | GET |
| Thread messages | `GET /api/v1/simulations/:id/opinions/threads/:threadId/messages` | GET |

### Response Schema — Thread Header

```typescript
interface ThreadHeader {
  thread_id: string;
  topic: string;
  category_tag: string;
  participant_count: number;
  timespan: string;           // "2h 15m"
  avg_sentiment: number;      // -1.0 to +1.0
  message_count: number;
}
```

### Response Schema — Thread Message

```typescript
interface ThreadMessage {
  message_id: string;
  agent_id: string;
  community_id: string;
  community_color: string;
  stance: "Progressive" | "Conservative" | "Neutral";
  timestamp: string;          // ISO 8601
  relative_time: string;      // "2h ago"
  content: string;
  reactions: {
    agree: number;
    disagree: number;
    nuanced: number;
  };
  is_reply: boolean;
  reply_to_id: string | null;
}
```

---

## 7. Pencil Node Reference

| Node ID | Description |
|---------|-------------|
| `q6TDI` | Frame root — Conversation Thread (1440x900) |
| `q6TDI/nav` | Navigation bar with Level 3 purple badge |
| `q6TDI/header` | Thread topic + metadata + stats |
| `q6TDI/thread` | Scrollable message thread body |
