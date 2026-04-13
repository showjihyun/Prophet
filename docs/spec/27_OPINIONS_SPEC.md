# 27 — Opinions Pages SPEC

> **Version:** 0.1.0
> **Status:** CURRENT
> **Authored:** 2026-04-12
> **Replaces:** `docs/spec/ui/UI_13_SCENARIO_OPINIONS.md`,
> `docs/spec/ui/UI_14_COMMUNITY_OPINION.md`,
> `docs/spec/ui/UI_15_CONVERSATION_THREAD.md` — IP-protected, not on disk.

---

## 1. Scope

Defines the three-level **Opinions** hierarchy reachable from the main nav
(`Agent Opinion`):

| Level | Route | Component | Purpose |
|---|---|---|---|
| **L1** | `/opinions` | `ScenarioOpinionsPage.tsx` | Scenario-wide opinion landscape — 4 stat cards, 5 community cards, faction-map toggle |
| **L2** | `/opinions/:communityId` | `CommunityOpinionPage.tsx` | Community-level opinion clusters + recent conversation threads |
| **L3** | `/opinions/:communityId/thread/:threadId` | `ConversationThreadPage.tsx` | Individual conversation thread with messages + reactions |

This SPEC is an **as-built contract**. It captures the current page shape and
data bindings so future changes (rename a section, drop a card, change a data
source) are intentional. It does not introduce new features beyond the gap
closures listed in §6.

### Non-goals

- **Live streaming during a running simulation** — covered by
  `SimulationPage` / `GlobalMetricsPage`.
- **Cross-simulation comparison** — covered by `Compare` and `MC` pages.
- **EliteLLM synthesis service internals** — owned by
  `25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis`. This SPEC only
  defines how the frontend invokes and renders that synthesis.
- **Agent profile rendering** — owned by `AgentDetailPage`.

---

## 2. Data sources <a id="opinions-data"></a>

All three pages consume `StepResult[]` and `Simulation` from two stacked
sources, in priority order:

1. **Live Zustand store** (`useSimulationStore`) — when the user just ran the
   simulation in this browser session, `store.steps` is already populated.
2. **TanStack Query fallback** (`useSimulationSteps(simulation_id)`) — when
   `store.steps.length === 0` but a `simulation_id` is available, fetch
   `GET /api/v1/simulations/{id}/steps`. Cached across navigations.

L2 (CommunityOpinionPage) and L3 (ConversationThreadPage) additionally consume
the threads API:

| Hook | Endpoint | Used by | Purpose |
|---|---|---|---|
| `useCommunityThreads(simId, communityId)` | `GET /simulations/{id}/communities/{cid}/threads` | L2 | Real recent conversations list |
| `useCommunityThread(simId, communityId, threadId)` | `GET /simulations/{id}/communities/{cid}/threads/{tid}` | L3 | Real thread detail with messages |

Both pages **prefer real API thread data over step-derived synthetic data**.
Synthetic step-derived data is only used as a fallback when the API returns
an empty list (e.g. older simulation runs without persisted threads).

---

## 3. Sentiment colour contract <a id="opinions-sentiment-color"></a>

A single shared utility owns the mapping from a numeric sentiment value to a
CSS variable, so the threshold and colour palette stay consistent across the
three pages.

**Module:** `frontend/src/utils/sentiment.ts`

**Public API:**

```ts
export type SentimentTone = 'positive' | 'negative' | 'neutral';

/** Bucket a numeric sentiment into a tone using ±0.1 thresholds. */
export function sentimentTone(value: number): SentimentTone;

/** Map a numeric sentiment to a Tailwind text-colour class. */
export function sentimentTextClass(value: number): string;
```

**Threshold contract:**

| Range | Tone | Text class |
|---|---|---|
| `value > 0.1` | `positive` | `text-[var(--sentiment-positive)]` |
| `value < -0.1` | `negative` | `text-[var(--destructive)]` |
| otherwise | `neutral` | `text-[var(--muted-foreground)]` |

All three pages MUST import from this module and MUST NOT inline the threshold
or colour expression. Tests assert by querying for the expected `text-[…]`
class on the rendered sentiment label.

---

## 4. Scenario Opinions page (L1) <a id="opinions-l1"></a>

**Component:** `frontend/src/pages/ScenarioOpinionsPage.tsx`
**Test contract:** `frontend/src/__tests__/ScenarioOpinions.test.tsx`

### 4.1 Page structure

| Section | testid / accessible name | Required content |
|---|---|---|
| Page nav | `data-testid="page-nav"` | Breadcrumb `[simulation.name, "Agent Opinion"]`, `Level 1` badge |
| Title | text `Scenario Opinion Landscape` | always visible |
| Subtitle | text `Step N · X agents · Y communities` | derived from latest step |
| Demo banner | `Showing demo data. Run a simulation to see real results.` | shown ⇔ `derivedCommunities.length === 0` |
| Overall opinion panel | `<OverallOpinionPanel>` | passes `simulationId` |
| Stat grid | 4 `<StatCard>` | see §4.2 |
| Section title | text `Community Opinion Breakdown` | always visible |
| View toggle | button `Switch to Faction View` / `Switch to Data-driven Map` | toggles `viewMode` |
| Body | data view (cards grid) or `<FactionMapView>` | mutually exclusive |

### 4.2 Stat card contract <a id="opinions-l1-stat"></a>

The four stat cards MUST display **real deltas** computed from the previous
step, not hard-coded demo strings. When fewer than two steps exist, the
`change` prop is omitted (renders no delta line).

| Card label | Value source | Delta source |
|---|---|---|
| `Avg Sentiment` | `latest.mean_sentiment.toFixed(2)` (signed) | `(latest.mean_sentiment - prev.mean_sentiment)` |
| `Polarization` | `latest.sentiment_variance.toFixed(2)` | `(latest.sentiment_variance - prev.sentiment_variance)` |
| `Total Conversations` | sum of `community_metrics[*].new_propagation_count` | `(latest sum) - (prev sum)` |
| `Active Cascades` | `Math.round(latest.adoption_rate * 1000)` | `(latest scaled) - (prev scaled)` |

**Delta formatting** (`utils/sentiment.ts` exports a helper for this):

```ts
export function formatDelta(diff: number, suffix?: string): string;
// e.g. formatDelta(0.08, "from prev step") → "+0.08 from prev step"
//      formatDelta(-12, "today")            → "-12 today"
//      formatDelta(0)                       → "no change"
```

`changeType` follows the sign of the diff: `>0 → "positive"`,
`<0 → "negative"`, `0 → "neutral"`.

For `Polarization` the convention is inverted: a *higher* polarization is
**bad**, so `diff > 0 → "negative"`, `diff < 0 → "positive"`. This is the only
inverted card.

### 4.3 Acceptance criteria (L1)

- **AC-L1-01** Page nav, title, 4 stat cards, 5 community cards, section title, view toggle all render when one step is in the store. (existing — preserved)
- **AC-L1-02** Each stat card's `change` line reflects the *real* delta from the previous step. With one step in the store, the change line is absent. (new — gap closure)
- **AC-L1-03** The Polarization card uses inverted `changeType`: an increase is rendered as `negative`, a decrease as `positive`. (new)
- **AC-L1-04** Sentiment colour on community cards comes from `sentimentTextClass` and the file does not contain a literal ternary on `> 0.1` / `< -0.1`. (new)

---

## 5. Community Opinion page (L2) <a id="opinions-l2"></a>

**Component:** `frontend/src/pages/CommunityOpinionPage.tsx`
**Test contract:** `frontend/src/__tests__/CommunityOpinion.test.tsx`

### 5.1 Page structure

| Section | testid / accessible name | Required content |
|---|---|---|
| Page nav | `data-testid="page-nav"` | Breadcrumb, `Level 2 Community` badge |
| Header | community name + colour dot | agent count, sentiment, conversation count, positive % |
| Demo banner | shown ⇔ `derivedClusters.length === 0` and `apiThreads.length === 0` |
| EliteLLM panel | `<EliteLLMNarrativePanel>` | passes `simulationId`, `communityId` |
| Left column | section title `Opinion Clusters`, sort `<select>`, cluster cards | from `derivedClusters` |
| Right column | section title `Recent Conversations`, count badge, conversation cards | see §5.2 |

### 5.2 Recent Conversations data flow <a id="opinions-l2-threads"></a>

The Recent Conversations list MUST prefer the real threads API over the
synthetic step-derived list:

```
useCommunityThreads(simId, communityId).data?.threads
  → if non-empty, render those (priority 1)
  → if empty / loading / error, fall back to derivedConversations (priority 2)
```

**Real-thread rendering shape:**

```ts
{
  thread_id: string;            // from API ThreadSummary
  topic_title: string;          // from API ThreadSummary.topic
  participant_ids: string[];    // synthesized from participant_count
  message_count: number;        // from API ThreadSummary.message_count
  relative_time: string;        // "n messages" or step-derived
}
```

The button `onClick` navigates to `/opinions/{communityId}/thread/{thread_id}`
in both real and fallback modes.

### 5.3 Sort modes (clusters)

| Value | Sort key |
|---|---|
| `mentioned` (default) | `agent_count` desc |
| `contested` | `|support - oppose|` desc (i.e. closest to balanced first) |
| `newest` | reverse insertion order |

### 5.4 Acceptance criteria (L2)

- **AC-L2-01** Page nav, Level 2 badge, community name, agent count, Opinion Clusters section, Recent Conversations section all render when one step is in the store. (existing — preserved)
- **AC-L2-02** When `useCommunityThreads` returns a non-empty list, the rendered conversation count badge reflects the API count, not the step-derived count. (new — gap closure)
- **AC-L2-03** Sentiment colour in the header comes from `sentimentTextClass`. (new)
- **AC-L2-04** Sort `<select>` is keyboard-accessible and the visible options are `Top Mentioned Topics`, `Most Contested`, `Newest`. (existing — preserved)

---

## 6. Conversation Thread page (L3) <a id="opinions-l3"></a>

**Component:** `frontend/src/pages/ConversationThreadPage.tsx`
**Test contract:** `frontend/src/__tests__/ConversationThread.test.tsx`

### 6.1 Page structure

| Section | testid / accessible name | Required content |
|---|---|---|
| Page nav | `data-testid="page-nav"` | Breadcrumb with community name (not hard-coded `Alpha`), `Level 3` badge |
| Header | thread topic, category tag, participant count, timespan, avg sentiment | sentiment colour from `sentimentTextClass` |
| Loading | text `Loading thread…` | shown ⇔ `apiLoading` |
| Empty state | text `No conversation data` + `Back to opinions` button | shown ⇔ no thread resolved |
| Body | message list (`data-testid="thread-message"` / `thread-reply`) | see §6.2 |

### 6.2 Message list data flow <a id="opinions-l3-messages"></a>

The message list MUST prefer real API messages over synthetic step-derived
messages. (This is the existing behaviour — preserved.)

```
useCommunityThread(simId, communityId, threadId).data
  → if defined, render apiThread.messages (priority 1)
  → otherwise, render derivedMessages from store steps (priority 2)
```

The breadcrumb's middle entry MUST be the actual `communityId` (or its
title-cased label), not a hard-coded literal. Tests assert that the breadcrumb
contains the routed `communityId`.

### 6.3 Acceptance criteria (L3)

- **AC-L3-01** When the API returns a thread, the rendered topic, participant count and message count come from the API (not the synthetic derivation). (existing — preserved)
- **AC-L3-02** The breadcrumb middle entry contains the routed `communityId`, not a hard-coded label. (new — gap closure)
- **AC-L3-03** Sentiment label colour comes from `sentimentTextClass`. (new)

---

## 7. Open issues / gap closure changelog <a id="opinions-changelog"></a>

| ID | Gap | Resolution |
|---|---|---|
| **G-OP-01** | L1 stat cards displayed hard-coded demo deltas (`+0.08 from yesterday`, `12 new`, `High`) | Compute deltas from `steps[N-1]` vs `steps[N]`; omit `change` when only one step exists |
| **G-OP-02** | L2 Recent Conversations was always step-derived synthetic | Prefer `useCommunityThreads` API; fall back to step-derived only when API empty |
| **G-OP-03** | Three pages duplicated the `> 0.1 / < -0.1` ternary | Centralised in `utils/sentiment.ts` |
| **G-OP-04** | L3 breadcrumb hard-coded `Alpha` regardless of routed `communityId` | Use routed `communityId` |
| **G-OP-05** | UI SPEC files (UI_13/14/15) referenced in docstrings did not exist on disk | This SPEC (27) replaces them |

---

## 8. Test counts

| Page | Test file | Existing tests | New tests (this SPEC) |
|---|---|---|---|
| L1 ScenarioOpinionsPage | `ScenarioOpinions.test.tsx` | 8 | +3 (delta absence, delta present, sentiment-class import) |
| L2 CommunityOpinionPage | `CommunityOpinion.test.tsx` | 6 | +2 (API thread priority, sentiment-class import) |
| L3 ConversationThreadPage | `ConversationThread.test.tsx` | 0 | +3 (breadcrumb derived, API priority, sentiment-class import) |

Total: **22 tests** for the opinions hierarchy.
