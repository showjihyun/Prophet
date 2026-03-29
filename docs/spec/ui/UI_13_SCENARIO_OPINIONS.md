# UI-13 — Scenario Opinions Overview SPEC
Version: 0.1.0 | Status: DRAFT
Source: pencil-shadcn.pen > Frame: Scenario Opinions Overview (ID: dAnYu)

---

## 1. Overview

The Scenario Opinions Overview screen provides a high-level landscape of agent opinions across all communities within a simulation scenario. It shows aggregate sentiment, polarization, conversation counts, and active cascades, then breaks them down by community with individual opinion cards. This is the entry point for the opinion drill-down hierarchy: Scenario > Community > Conversation Thread.

Navigation hierarchy:
- **Level 1** (this page): Scenario-wide opinion overview
- **Level 2**: Community opinion detail (UI-14)
- **Level 3**: Conversation thread (UI-15)

---

## 2. Layout Structure

```
+------------------------------------------------------------------------+
| Nav Bar                                                    [dAnYu/nav] |
| [<Back] Korea Election 2026 > Agent Opinion   [Level 1] [Settings] [A] |
+------------------------------------------------------------------------+
| Header                                                  [dAnYu/header] |
| "Scenario Opinion Landscape"                                           |
| Day 47 | 10,000 agents | 5 communities                               |
| +------------+ +------------+ +---------------+ +---------------+      |
| | Avg Sent.  | | Polariz.   | | Conversations | | Active Casc.  |      |
| | +0.34      | | 0.72       | | 1,247         | | 847           |      |
| +------------+ +------------+ +---------------+ +---------------+      |
+------------------------------------------------------------------------+
| Body                                                    [dAnYu/body]   |
| "Community Opinion Breakdown"        [Data-driven Map vs Faction btn]  |
| +-------------------+-------------------+-------------------+          |
| | Alpha (2,148)     | Beta (1,808)      | Gamma (1,414)     |          |
| | Sent: +0.52       | Sent: +0.41       | Sent: -0.16       |          |
| | Conv: 312         | Conv: 256         | Conv: 289         |          |
| | Pos 67%  [===]    | Pos 58%  [===]    | Mixed 42% [===]   |          |
| | [View Community]  | [View Community]  | [View Community]  |          |
| +-------------------+-------------------+-------------------+          |
| +-------------------+-------------------+                              |
| | Delta (998)       | Bridge (1,308)    |                              |
| | Sent: -0.35       | Mixed sentiment   |                              |
| | Conv: 194         | Conv: 182         |                              |
| | Neg 36%  [===]    | Mixed  [===]      |                              |
| | [View Community]  | [View Community]  |                              |
| +-------------------+-------------------+                              |
+------------------------------------------------------------------------+
```

---

## 3. Components

### Navigation Bar

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `dAnYu/nav` | `PageNav` | Top navigation bar with back, breadcrumb, badge, actions | `dAnYu` |
| `dAnYu/nav/backBtn` | `Button` | "Back" ghost button, navigates to previous page | `dAnYu/nav` |
| `dAnYu/nav/breadcrumb` | `Breadcrumb` | "Korea Election 2026 > Agent Opinion" | `dAnYu/nav` |
| `dAnYu/nav/levelBadge` | `Badge` | "Level 1" badge, variant=outline | `dAnYu/nav` |
| `dAnYu/nav/settingsBtn` | `Button` | Settings icon button, variant=ghost | `dAnYu/nav` |
| `dAnYu/nav/avatar` | `Avatar` | User avatar, 32px circle | `dAnYu/nav` |

### Header Section

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `dAnYu/header` | `div` (flex col) | Header container with title + description + stats | `dAnYu` |
| `dAnYu/header/title` | `h1` | "Scenario Opinion Landscape", font-display, text-2xl | `dAnYu/header` |
| `dAnYu/header/desc` | `p` | Context line: "Day 47 · 10,000 agents · 5 communities" | `dAnYu/header` |
| `dAnYu/header/stats` | `div` (grid 4-col) | 4 StatCard instances | `dAnYu/header` |
| `dAnYu/header/statSentiment` | `StatCard` | Avg Sentiment: +0.34, positive change indicator | `dAnYu/header/stats` |
| `dAnYu/header/statPolarization` | `StatCard` | Polarization: 0.72, warning change indicator | `dAnYu/header/stats` |
| `dAnYu/header/statConversations` | `StatCard` | Total Conversations: 1,247 | `dAnYu/header/stats` |
| `dAnYu/header/statCascades` | `StatCard` | Active Cascades: 847 | `dAnYu/header/stats` |

### Body — Community Opinion Cards

| Component ID | Type | Description | Parent ID |
|-------------|------|-------------|-----------|
| `dAnYu/body` | `div` (flex col) | Body container with section title + grid | `dAnYu` |
| `dAnYu/body/sectionTitle` | `div` (flex row) | "Community Opinion Breakdown" + view toggle button | `dAnYu/body` |
| `dAnYu/body/viewToggle` | `Button` | "Data-driven Map vs Faction", variant=outline | `dAnYu/body/sectionTitle` |
| `dAnYu/body/grid` | `div` (grid 3-col) | Grid of CommunityOpinionCard components, gap=16px | `dAnYu/body` |
| `dAnYu/body/cardAlpha` | `CommunityOpinionCard` | Alpha community card | `dAnYu/body/grid` |
| `dAnYu/body/cardBeta` | `CommunityOpinionCard` | Beta community card | `dAnYu/body/grid` |
| `dAnYu/body/cardGamma` | `CommunityOpinionCard` | Gamma community card | `dAnYu/body/grid` |
| `dAnYu/body/cardDelta` | `CommunityOpinionCard` | Delta community card | `dAnYu/body/grid` |
| `dAnYu/body/cardBridge` | `CommunityOpinionCard` | Bridge agents card | `dAnYu/body/grid` |

### CommunityOpinionCard (Repeated Component)

| Property | Type | Description |
|----------|------|-------------|
| `communityName` | `string` | Community display name |
| `agentCount` | `number` | Number of agents in community |
| `sentiment` | `number` | Average sentiment value (-1.0 to +1.0) |
| `conversations` | `number` | Active conversation count |
| `dominantStance` | `string` | "positive" / "negative" / "mixed" + percentage |
| `sentimentBar` | `SentimentBar` | Visual bar showing positive/neutral/negative distribution |
| `communityColor` | `string` | CSS variable for community color dot |
| `onViewCommunity` | `() => void` | Navigation callback to community detail |

---

## 4. Design Tokens

| Token | Value | Usage |
|-------|-------|-------|
| `font-display` | `'Instrument Serif', serif` | Page title |
| `font-body` | `'Geist', sans-serif` | All body text |
| `--card` | `#18181b` | Card background |
| `--border` | `#27272a` | Card border |
| `--background` | `#09090b` | Page background |
| `--foreground` | `#fafafa` | Primary text |
| `--muted-foreground` | `#a1a1aa` | Secondary text |
| `--sentiment-positive` | `#22c55e` | Positive sentiment bar/text |
| `--sentiment-neutral` | `#94a3b8` | Neutral sentiment |
| `--sentiment-negative` | `#ef4444` | Negative sentiment bar/text |
| `--community-*` | See index.css | Community color dots |
| Card padding | `20px` | Inner padding for opinion cards |
| Grid gap | `16px` | Gap between community cards |
| Stat card grid | `4 columns` | Header stat cards |
| Community grid | `3 columns` | Community opinion cards (3+2 layout) |

---

## 5. Interaction Behavior

| ID | Trigger | Action |
|----|---------|--------|
| INT-01 | Page load | Fetch scenario opinion data from API |
| INT-02 | Click "View Community" on card | Navigate to `/opinions/:communityId` (UI-14) |
| INT-03 | Click breadcrumb "Korea Election 2026" | Navigate back to project scenarios page |
| INT-04 | Click "Data-driven Map vs Faction" | Toggle between card grid and map visualization (future) |
| INT-05 | Hover community card | Subtle scale transform (1.02) |
| INT-06 | Click back button | Navigate to previous page |

---

## 6. Data Binding

| Component | API Endpoint | Method |
|-----------|-------------|--------|
| Header stats | `GET /api/v1/simulations/:id/opinions/summary` | GET |
| Community cards | `GET /api/v1/simulations/:id/opinions/communities` | GET |

### Response Schema — Opinion Summary

```typescript
interface OpinionSummary {
  avg_sentiment: number;        // -1.0 to +1.0
  polarization: number;         // 0.0 to 1.0
  total_conversations: number;
  active_cascades: number;
  day: number;
  total_agents: number;
  community_count: number;
}
```

### Response Schema — Community Opinions

```typescript
interface CommunityOpinion {
  community_id: string;
  community_name: string;
  agent_count: number;
  avg_sentiment: number;
  conversation_count: number;
  dominant_stance: "positive" | "negative" | "mixed";
  dominant_pct: number;
  sentiment_distribution: {
    positive: number;   // percentage 0-100
    neutral: number;
    negative: number;
  };
}
```

---

## 7. Pencil Node Reference

| Node ID | Description |
|---------|-------------|
| `dAnYu` | Frame root — Scenario Opinions Overview (1440x900) |
| `dAnYu/nav` | Navigation bar |
| `dAnYu/header` | Header with title + 4 stat cards |
| `dAnYu/body` | Community opinion breakdown grid |
