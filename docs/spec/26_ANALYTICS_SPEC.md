# 26 — Post-Run Analytics SPEC

> **Version:** 0.3.0
> **Status:** CURRENT
> **Authored:** 2026-04-12 (v0.1.0 as-built) · 2026-04-12 (v0.2.0 gap closure) · 2026-04-12 (v0.3.0 step-focus round-trip)
> **Replaces:** `07_FRONTEND_SPEC.md#simulationsidanalytics` (IP-protected, not on disk)

---

## 1. Scope

Defines the **Post-Run Analytics** page — a read-only summary surfaced after a
simulation has produced at least one step. The page is reached from the main
navigation (`Analytics` menu) and from in-simulation deep-links.

Route: `/analytics` (standalone) — also reachable from a simulation context.
Component: `frontend/src/pages/AnalyticsPage.tsx`.
Test contract: `frontend/src/__tests__/AnalyticsPage.test.tsx`.

This SPEC is an **as-built contract**. It captures the current page shape and
data bindings so that future changes (rename a section, drop a card, add a
chart) are intentional rather than accidental. It does not describe new work.

### Non-goals

- **Live streaming metrics during a running simulation** — that belongs to
  `GlobalMetricsPage` / `SimulationPage`. Analytics is post-hoc and reads a
  completed step history.
- **Cross-simulation comparison / Monte Carlo aggregation** — covered by the
  Compare and MC pages, not here.
- **Agent-level drill-down** — handled by `AgentDetailPage`.
- **Cost / LLM tier breakdown** — handled by `GlobalMetricsPage` Tier 1/2/3
  cards.
- **Data export** — JSON/CSV export lives on `GlobalMetricsPage`.

Anything the user wants from those buckets should be added to the owning page,
not duplicated here.

---

## 2. Data sources <a id="analytics-data"></a>

The page consumes `StepResult[]` and `Simulation` from two stacked sources, in
priority order:

1. **Live Zustand store** (`useSimulationStore`) — when the user just ran the
   simulation in this browser session, `store.steps` is already populated.
2. **TanStack Query fallback** (`useSimulationSteps(simulation_id)`) — when
   `store.steps.length === 0` but a `simulation_id` is available, fetch
   `GET /api/v1/simulations/{id}/steps`. Cached across navigations so reopening
   Analytics is instant.

Derivation functions (all pure, all defined at module scope, all wrapped in
`useMemo` to satisfy FE-PERF-15 / FE-PERF-16):

| Function | Input | Output | Used by |
|---|---|---|---|
| `buildAdoptionData(steps)` | `StepResult[]` | `{ step, total, [cid]: pct }[]` | Adoption Rate chart |
| `buildSentimentData(steps)` | `StepResult[]` | `{ step, sentiment }[]` | Sentiment chart |
| `buildCommunityAdoption(steps)` | `StepResult[]` | `{ community, rate, color }[]` (last step only) | Community Adoption bar |
| `getCommunityKeys(steps)` | `StepResult[]` | `string[]` | Chart line keys |
| `collectEmergentEvents(steps)` | `StepResult[]` | `EmergentEvent[]` (deduped by `type-step-community`) | Event timeline, ReferenceLine markers |

All percentages are formatted to **one decimal place** (`toFixed(1)`).
Sentiment is formatted to **three decimal places** (`toFixed(3)`).

---

## 3. Layout <a id="analytics-layout"></a>

Root element `div[data-testid="analytics-page"]`. Sticky header + scrollable
content. `max-w-5xl mx-auto` content column.

### 3.1 Header

- Back button — `aria-label="Go back"`, calls `navigate(-1)`.
- Title — `"Post-Run Analytics"` (`<h1>`, `text-base font-semibold`).
- Subtitle — `simulation.name` when available, truncated to `max-w-xs`.
- Icon — `BarChart3` (`lucide-react`), `text-[var(--primary)]`.

### 3.2 State gates (exclusive)

The body renders exactly one of these states:

| Gate | Condition | Content |
|---|---|---|
| **Loading** | `stepsQuery.isLoading` | "Loading analytics..." with `animate-pulse` |
| **Error** | `stepsQuery.error !== null` | Error message, `text-[var(--destructive)]` |
| **No simulation** | `!simulation && !loading` | Icon + "No active simulation. Run a simulation first." + "Go to Projects" button (navigates to `/projects`) |
| **Empty steps** | `simulation && !loading && !error && steps.length === 0` | Icon + "No step data available yet. Run the simulation to generate analytics." |
| **Content** | `simulation && !loading && !error && steps.length > 0` | Sections 4.1 – 4.5 |

---

## 4. Content sections <a id="analytics-charts"></a>

When the Content gate is active, render sections in this order inside
`<main class="max-w-5xl mx-auto px-6 py-8 flex flex-col gap-10">`:

1. §4.1 Summary Cards
2. §4.2 Adoption Rate Over Time
3. §4.3 Mean Sentiment Over Time
4. §4.4 Community Adoption Comparison
5. §4.6 Cascade Analytics (v0.2.0) — summary positioned before the detail drill-down
6. §4.5 Emergent Event Timeline

### 4.1 Summary Cards <a id="analytics-summary-cards"></a>

`grid grid-cols-2 gap-3 sm:grid-cols-4` of four `SummaryCard` components.

| Label | Value | Accent |
|---|---|---|
| `Total Steps` | `steps[last].step` | none |
| `Final Adoption` | `{(adoption_rate * 100).toFixed(1)}%` | `positive` |
| `Final Sentiment` | `mean_sentiment.toFixed(3)` | `positive` if `>= 0`, else `negative` |
| `Emergent Events` | `emergentEvents.length` | `warning` when `> 0` |

Accent colors map to CSS variables `--sentiment-positive`,
`--sentiment-negative`, `--sentiment-warning`.

### 4.2 Adoption Rate Over Time

Section title: **"Adoption Rate Over Time"**. Icon: `TrendingUp` in primary color.

- `recharts.LineChart`, height `220px`, `ResponsiveContainer` width `100%`.
- X axis: `dataKey="step"`, labelled `"Step"`.
- Y axis: unit `%`, `domain={[0, 100]}`.
- **Total line**: `dataKey="total"`, `stroke="var(--primary)"`, `strokeWidth={2}`.
- **Per-community dashed lines**: one `<Line>` per community key with color
  from `COMMUNITY_COLORS[idx % 5]`, `strokeDasharray="4 2"`, `strokeWidth={1.5}`.
- **Emergent event markers**: one `<ReferenceLine x={eventStep} />` per unique
  `emergentEvents[].step`, `stroke="var(--sentiment-warning)"`,
  `strokeDasharray="4 2"`.
- If any event markers exist, render the caption
  `"Dashed vertical lines indicate emergent events."` below the chart.

### 4.3 Mean Sentiment Over Time

Section title: **"Mean Sentiment Over Time"**. Icon: `BarChart3` in
`--community-alpha`.

- `recharts.LineChart`, height `180px`.
- Y axis `domain={[-1, 1]}`.
- `ReferenceLine y={0}` in `--border` as the neutral baseline.
- Same event-step `ReferenceLine` markers as 4.2 (in `--sentiment-warning`).
- Single line: `dataKey="sentiment"`, `stroke="var(--community-alpha)"`,
  `strokeWidth={2}`.

### 4.4 Community Adoption Comparison (Final Step)

Section title: **"Community Adoption Comparison (Final Step)"**. Icon:
`BarChart3` in `--community-delta`.

- `recharts.BarChart`, height `200px`. Data from `buildCommunityAdoption(steps)`
  (final step only).
- X axis: `dataKey="community"`, tilted `-20°`.
- Y axis: unit `%`, `domain={[0, 100]}`.
- Bar: `dataKey="rate"`, `radius={[4, 4, 0, 0]}`. Per-community colors via
  child `<rect fill={entry.color} />` per `entry`.
- **Fallback list** (always rendered below the chart) — a simple div-based
  horizontal bar list with color dot, community id, fill bar, and percentage.
  This exists because recharts `<Bar>` per-cell fills are unreliable under
  some CSS variable resolutions; the div list is the source of truth visually.

### 4.5 Emergent Event Timeline <a id="analytics-emergent-events"></a>

Section title: **"Emergent Event Timeline"**. Icon: `AlertTriangle` in
`--sentiment-warning`.

Three sub-components: **(a) filter toolbar**, **(b) event rows**, **(c) empty
state**.

#### 4.5.1 Filter toolbar (v0.2.0)

Chip row above the event list. Chips: **All** plus one per event type present
in `emergentEvents`. Each chip is `role="button"`, `aria-pressed={true|false}`,
`tabIndex={0}`, keyboard-activatable via Enter/Space.

- Default: **All** is pressed; all events render.
- Click a type chip → `activeFilter = type`; only events of that type render.
- Click **All** → `activeFilter = null`; all events render.
- Filter chips render only when `emergentEvents.length > 0`. (No filter UI on
  empty state.)
- **Filtering narrows the timeline list only.** Summary card counts (§4.1) and
  chart ReferenceLine markers (§4.2, §4.3) MUST remain based on the unfiltered
  `emergentEvents`.

Data-testids: `event-filter-all`, `event-filter-{type}` (e.g.
`event-filter-viral_cascade`).

#### 4.5.2 Event rows

**Populated** (`filteredEvents.length > 0`): bordered card with `divide-y`
rows, one per event after filtering:

| Column | Content |
|---|---|
| Step | `Step {e.step}`, `font-mono text-xs`, fixed `w-14` |
| Icon | `EVENT_ICONS[e.event_type] ?? "📌"` (emoji, `text-base`) |
| Type | `e.event_type.replace(/_/g, " ")`, `capitalize` |
| Community pill | `e.community_id` in a `bg-[var(--secondary)]` pill, only when set |
| Severity | `sev {e.severity.toFixed(2)}`, color from `severityColor(sev)` |
| Description | `e.description`, `line-clamp-2` |

**Deep-link to simulation context (v0.2.0, completed v0.3.0)**: each row is
a button.

- `role="button"`, `tabIndex={0}`, `cursor-pointer`, hover highlight.
- `aria-label="View step {e.step} in simulation"`.
- Click (or Enter/Space key) → `navigate(`/simulation/${simulation_id}?step=${e.step}`)`.
- Fires only when `simulation.simulation_id` exists (it does, per §3.2
  Content gate).

**Round-trip contract (v0.3.0)** — when SimulationPage receives a
`?step=N` query parameter:

1. Parse `N` as a non-negative integer. If the parse fails, ignore the param
   silently and continue with live behavior.
2. Call `useSimulationStore.setFocusedStep(N)`. This is a new store field,
   orthogonal to `currentStep` — `appendStep` MUST NOT clobber it.
3. Render a dismissable banner above the main content area:
   `"Viewing step N from Analytics."` with a **Return to live** button.
4. Clicking **Return to live** does two things:
   a. `setFocusedStep(null)` — clears the focus field.
   b. Removes the `step` query parameter from the URL (so reload / share
      returns to live behavior).
5. `TimelinePanel` — when `focusedStep !== null`, its left-side step counter
   reads `"Step N (focused)"` instead of the live `"Step {currentStep} of {maxSteps}"`.

See §9 for scrubbing-of-actual-state (graph, metrics) which remains deferred
to v0.4.0 — v0.3.0 delivers the **focus announcement**, not state replay.

**Empty after filtering** (`filteredEvents.length === 0` but
`emergentEvents.length > 0`): card with
`"No events match the current filter."`

**Empty globally** (`emergentEvents.length === 0`): card with
`"No emergent events detected during this simulation."` No filter toolbar.

#### 4.5.3 Helpers

`severityColor`: `>= 0.7` → `--sentiment-negative`; `>= 0.4` →
`--sentiment-warning`; else `--muted-foreground`.

`EVENT_ICONS` map (exhaustive as of 0.2.0):

```ts
{
  viral_cascade: "⚡",
  slow_adoption: "🐢",
  polarization:  "⚔️",
  collapse:      "💥",
  echo_chamber:  "🔄",
}
```

---

### 4.6 Cascade Analytics (v0.2.0) <a id="analytics-cascade"></a>

Section title: **"Cascade Analytics"**. Icon: `GitBranch` in
`--community-gamma`.

Post-hoc summary of cascade structure across the full step history. Mirrors
the live cards on `GlobalMetricsPage` but is derived over the entire run, not
just "right now". Grid: `grid grid-cols-2 sm:grid-cols-4 gap-3`.

| Card | Label | Value source |
|---|---|---|
| 1 | **Longest Cascade Run** | Longest consecutive run of steps with `diffusion_rate > 0`. Integer. |
| 2 | **Peak Adoption Delta** | Maximum single-step delta in `total_adoption`. Integer. |
| 3 | **Viral/Cascade Events** | Count of `emergent_events` whose `event_type` contains `"cascade"` or `"viral"` (case-insensitive). Integer. |
| 4 | **Decay Rate** | `(peakRate - latestRate) / peakRate` where `rate = diffusion_rate`, `toFixed(2)`, suffix `/step`. `"0.00/step"` when `peakRate == 0`. |

**Derivation function**: `buildCascadeStats(steps: StepResult[])` — pure, at
module scope, returning `{ depth: string; width: string; paths: string; decay: string }`.

Must be wrapped in `useMemo([steps])`. When `steps.length === 0`, the Content
gate (§3.2) already prevents this section from rendering, so the derivation
does not need its own empty-state branch — but MUST still return `"0"` / `"0"`
/ `"0"` / `"0.00/step"` if called with an empty array, to be defensive.

Data-testids: `cascade-depth`, `cascade-width`, `cascade-paths`, `cascade-decay`.

---

## 5. Styling & tokens

All colors MUST come from CSS variables. No hex literals for community colors
— use the `COMMUNITY_COLORS` palette:

```ts
const COMMUNITY_COLORS = [
  "var(--community-alpha)",
  "var(--community-beta)",
  "var(--community-gamma)",
  "var(--community-delta)",
  "var(--community-bridge)",
];
```

Indexing is `idx % COMMUNITY_COLORS.length` so more than 5 communities cycle.

Recharts `Tooltip` uses:
`backgroundColor: var(--card)`, `border: 1px solid var(--border)`,
`borderRadius: 6px`, `fontSize: 11px`.

---

## 6. Performance constraints

Authoritative: **`18_FRONTEND_PERFORMANCE_SPEC.md` FE-PERF-15, FE-PERF-16**.

Requirements (already met in current `AnalyticsPage.tsx`):

- `buildAdoptionData`, `buildSentimentData`, `buildCommunityAdoption`,
  `getCommunityKeys`, `collectEmergentEvents` MUST be wrapped in `useMemo`
  with `[steps]` (or `[latestStep, storeStepsLength, fetchedSteps]` for the
  `steps` derivation itself).
- The Zustand subscription is split — subscribe to `steps.length` and
  `latestStep` (primitives) and read the full `steps` array lazily via
  `useSimulationStore.getState().steps` inside the `useMemo`. This matches
  FE-PERF-H1.
- Recharts components may be wrapped in `React.memo` (FE-PERF-16 — optional,
  not currently applied).

---

## 7. Accessibility <a id="analytics-a11y"></a>

- Back button: `aria-label="Go back"`.
- Loading / empty / error states use visible text, not just icons.
- Decorative icons (`BarChart3`, `TrendingUp`, `AlertTriangle`, `GitBranch`)
  are not labelled because they accompany text headings.
- **Chart wrappers (v0.2.0)**: each chart is wrapped in
  `<div role="img" aria-label="{description}">` so screen readers announce
  the chart's purpose. Required labels:
  - §4.2 → `"Adoption rate over time, line chart"`
  - §4.3 → `"Mean sentiment over time, line chart"`
  - §4.4 → `"Community adoption comparison at final step, bar chart"`
- **Event rows (v0.2.0)**: `role="button"`, `tabIndex={0}`,
  `aria-label="View step {n} in simulation"`. Enter/Space activates navigate.
- **Filter chips (v0.2.0)**: `role="button"`, `aria-pressed={bool}`,
  `tabIndex={0}`. Enter/Space toggles.

---

## 8. Test contract <a id="analytics-tests"></a>

Authoritative: `frontend/src/__tests__/AnalyticsPage.test.tsx`.

| Section anchor | Test `describe` block | What it enforces |
|---|---|---|
| `#analytics-layout` | `Layout` | `data-testid="analytics-page"`, title, back button, back nav |
| `#analytics-data` (empty) | `Empty / No-Simulation State` | no-sim gate, Go to Projects button + nav |
| `#analytics-simulation-name` | `Simulation Name Display` | subtitle = `simulation.name` |
| `#analytics-fetch` | `Step Fetching` | calls `getSteps` iff store empty; loading / error / empty gates |
| `#analytics-summary-cards` | `Summary Cards` | all 4 card labels + Final Adoption `40.0%` case |
| `#analytics-charts` | `Chart Sections` | section titles render for 4.2, 4.3, 4.4 |
| `#analytics-emergent-events` | `Emergent Event Timeline` | title, type text, description, empty message, severity format, community pill, Step prefix, deep-link click+keyboard, filter chips (v0.2.0) |
| `#analytics-cascade` | `Cascade Analytics (v0.2.0)` | section title, 4 cards, derived values for test fixture, empty-array defensive return |
| `#analytics-a11y` | `Chart a11y (v0.2.0)` | `role="img"` + `aria-label` on each chart wrapper |

**Round-trip contract tests (v0.3.0)** — these live outside `AnalyticsPage.test.tsx`
because they exercise the receiving end of the deep link:

| File | Tests |
|---|---|
| `simulationStore.test.ts` | `setFocusedStep(n)` updates the field; `setFocusedStep(null)` clears; `appendStep` does not clobber `focusedStep` (regression guard) |
| `SimulationPage.test.tsx` | arriving with `?step=47` sets `focusedStep=47` in store; banner renders with "Viewing step 47"; dismiss button clears `focusedStep` and removes the `step` query param; arriving without `?step=` leaves `focusedStep` null and hides the banner |

Any change to the page that renames a section heading, removes a card, or
changes a test-id MUST update both this SPEC and the matching test anchor.

---

## 9. Known gaps

These are deliberately-deferred items. Adding any of them requires a SPEC
version bump and a matching test update.

- **Graph state scrubbing at focused step** — v0.3.0 announces the focus
  ("Viewing step 47") but the 3D graph still renders the live/latest state,
  not the propagation pairs that fired AT step 47. Would require loading the
  historic `propagation_pairs` for step N (already persisted) and temporarily
  replacing the graph animation source. Deferred to v0.4.0.
- **Metrics panel historic view** — same constraint: `MetricsPanel` reads
  from `latestStep`, not from a "step N snapshot". Deferred to v0.4.0.
- **Severity filter** — the v0.2.0 filter toolbar filters by event type only.
  A `min_severity` slider would let users hide low-severity noise. Deferred.
- **Multi-select type filter** — v0.2.0 chips are single-select (All + one
  type). True multi-select (e.g., "viral_cascade OR polarization") is
  deferred — single-select covers the 80% case without UI noise.
- **No comparison across runs** — intentional, see Non-goals.

### Closed in v0.2.0

- ~~Chart a11y descriptions~~ — §7 now mandates `role="img"` + `aria-label`.
- ~~Per-event filtering~~ — §4.5.1 filter toolbar.
- ~~Event deep-link~~ — §4.5.2 each row navigates to
  `/simulation/{id}?step={n}`.
- ~~Cascade depth/width summary~~ — §4.6 Cascade Analytics.

### Closed in v0.3.0

- ~~SimulationPage consumption of `?step=`~~ — §4.5.2 round-trip contract:
  `focusedStep` store field, SimulationPage banner, TimelinePanel counter
  swap, dismiss-and-clear-URL. State replay (graph/metrics) remains in the
  v0.4.0 gap list above.

---

## 10. Change log

| Version | Date | Change |
|---|---|---|
| 0.1.0 | 2026-04-12 | Initial as-built SPEC. Replaces the IP-protected `07_FRONTEND_SPEC.md#simulationsidanalytics` anchor. No behavioral change. |
| 0.2.0 | 2026-04-12 | Gap closure: §4.5 filter toolbar + event-row deep-link + keyboard activation. §4.6 Cascade Analytics section. §7 chart a11y `role="img"` + `aria-label`. §9 updated with v0.3.0 deferrals (SimulationPage `?step=` consumption, severity filter, multi-select filter). |
| 0.3.0 | 2026-04-12 | §4.5.2 round-trip contract: SimulationPage reads `?step=N`, sets `focusedStep` store field, renders dismiss banner, swaps TimelinePanel counter. `appendStep` must not clobber `focusedStep`. Graph/metrics state replay remains deferred to v0.4.0 (§9). |
