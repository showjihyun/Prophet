/**
 * AnalyticsPage — Post-run analytics for a completed simulation.
 * @spec docs/spec/26_ANALYTICS_SPEC.md
 * @spec-legacy docs/spec/07_FRONTEND_SPEC.md#simulationsidanalytics (IP-protected, superseded by 26)
 */
import { useMemo, useState, useCallback, type KeyboardEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import {
  ArrowLeft,
  TrendingUp,
  AlertTriangle,
  BarChart3,
  GitBranch,
} from "lucide-react";
import { useSimulationStore } from "../store/simulationStore";
import { useSimulationSteps } from "../api/queries";
import type { StepResult, EmergentEvent } from "../types/simulation";

// ----- Colour palette for communities -----
const COMMUNITY_COLORS = [
  "var(--community-alpha)",
  "var(--community-beta)",
  "var(--community-gamma)",
  "var(--community-delta)",
  "var(--community-bridge)",
];

// ----- Helpers -----

/** Build adoption-rate-over-time data for Recharts. */
function buildAdoptionData(steps: StepResult[]) {
  return steps.map((s) => {
    const row: Record<string, number | string> = {
      step: s.step,
      total: parseFloat((s.adoption_rate * 100).toFixed(1)),
    };
    for (const [cid, m] of Object.entries(s.community_metrics ?? {})) {
      row[cid] = parseFloat(((m.adoption_rate ?? 0) * 100).toFixed(1));
    }
    return row;
  });
}

/** Build sentiment-over-time data. */
function buildSentimentData(steps: StepResult[]) {
  return steps.map((s) => ({
    step: s.step,
    sentiment: parseFloat((s.mean_sentiment ?? 0).toFixed(3)),
  }));
}

/** Build final community adoption for bar chart. */
function buildCommunityAdoption(steps: StepResult[]) {
  if (steps.length === 0) return [];
  const last = steps[steps.length - 1];
  return Object.entries(last.community_metrics ?? {}).map(([cid, m], idx) => ({
    community: cid,
    rate: parseFloat(((m.adoption_rate ?? 0) * 100).toFixed(1)),
    color: COMMUNITY_COLORS[idx % COMMUNITY_COLORS.length],
  }));
}

/** Get community keys from step data. */
function getCommunityKeys(steps: StepResult[]): string[] {
  if (steps.length === 0) return [];
  return Object.keys(steps[0].community_metrics ?? {});
}

/**
 * Cascade Analytics derivation (SPEC 26 §4.6).
 * Pure, module-scoped, returns formatted strings ready for rendering.
 *
 * Mirrors GlobalMetricsPage's cascadeStats derivation so the live and
 * post-hoc views stay consistent.
 */
function buildCascadeStats(steps: StepResult[]): {
  depth: string;
  width: string;
  paths: string;
  decay: string;
} {
  if (steps.length === 0) {
    return { depth: "0", width: "0", paths: "0", decay: "0.00/step" };
  }

  // Longest consecutive run of steps with non-zero diffusion
  let longestRun = 0;
  let currentRun = 0;
  for (const s of steps) {
    if ((s.diffusion_rate ?? 0) > 0) {
      currentRun += 1;
      if (currentRun > longestRun) longestRun = currentRun;
    } else {
      currentRun = 0;
    }
  }

  // Widest single-step delta in total_adoption (peak adoption delta)
  let peakDelta = 0;
  let prevAdopt = 0;
  for (const s of steps) {
    const delta = (s.total_adoption ?? 0) - prevAdopt;
    if (delta > peakDelta) peakDelta = delta;
    prevAdopt = s.total_adoption ?? 0;
  }

  // Viral / cascade event count
  const cascadeEvents = steps.reduce((sum, s) => {
    const events = s.emergent_events ?? [];
    return (
      sum +
      events.filter((e) => {
        const t = (e.event_type ?? "").toLowerCase();
        return t.includes("cascade") || t.includes("viral");
      }).length
    );
  }, 0);

  // Decay: peak diffusion rate vs latest
  const diffRates = steps.map((s) => s.diffusion_rate ?? 0);
  const peakRate = Math.max(...diffRates, 0);
  const latestRate = diffRates[diffRates.length - 1] ?? 0;
  const decay =
    peakRate > 0 ? ((peakRate - latestRate) / peakRate).toFixed(2) : "0.00";

  return {
    depth: String(longestRun),
    width: String(peakDelta),
    paths: String(cascadeEvents),
    decay: `${decay}/step`,
  };
}

/** All emergent events across steps. */
function collectEmergentEvents(steps: StepResult[]): EmergentEvent[] {
  const seen = new Set<string>();
  const events: EmergentEvent[] = [];
  for (const s of steps) {
    for (const e of s.emergent_events ?? []) {
      const key = `${e.event_type}-${e.step}-${e.community_id}`;
      if (!seen.has(key)) {
        seen.add(key);
        events.push(e);
      }
    }
  }
  return events;
}

/** Severity badge colour. */
function severityColor(severity: number): string {
  if (severity >= 0.7) return "text-[var(--sentiment-negative)]";
  if (severity >= 0.4) return "text-[var(--sentiment-warning)]";
  return "text-[var(--muted-foreground)]";
}

/** Event icon map. */
const EVENT_ICONS: Record<string, string> = {
  viral_cascade: "⚡",
  slow_adoption: "🐢",
  polarization: "⚔️",
  collapse: "💥",
  echo_chamber: "🔄",
};

// ----- Section wrapper -----
function Section({
  title,
  icon,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        {icon}
        <h2 className="text-sm font-semibold text-[var(--foreground)]">{title}</h2>
      </div>
      {children}
    </section>
  );
}

// ----- Main Page -----
export default function AnalyticsPage() {
  const navigate = useNavigate();
  const simulation = useSimulationStore((s) => s.simulation);
  // FE-PERF-H1: subscribe to length + latestStep, read array lazily inside memos
  const storeStepsLength = useSimulationStore((s) => s.steps.length);
  const latestStep = useSimulationStore((s) => s.latestStep);

  // Event timeline filter state (SPEC 26 §4.5.1, v0.2.0).
  // `null` = show all; otherwise filter to the matching `event_type`.
  const [activeFilter, setActiveFilter] = useState<string | null>(null);

  // TanStack Query — only fetches when the live store is empty.
  // Cached across navigations, so reopening Analytics is instant.
  const stepsQuery = useSimulationSteps(
    storeStepsLength === 0 ? simulation?.simulation_id ?? null : null,
  );
  const fetchedSteps = stepsQuery.data ?? [];
  const loading = stepsQuery.isLoading;
  const error = stepsQuery.error
    ? stepsQuery.error instanceof Error
      ? stepsQuery.error.message
      : "Failed to load steps"
    : null;

  // Derive steps: prefer store (live), fall back to query-fetched
  const steps = useMemo<StepResult[]>(() => {
    const live = useSimulationStore.getState().steps;
    return live.length > 0 ? live : fetchedSteps;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestStep, storeStepsLength, fetchedSteps]);

  // FE-PERF-MEDIUM: memoize all recharts data so charts don't re-build on every parent render
  const adoptionData = useMemo(() => buildAdoptionData(steps), [steps]);
  const sentimentData = useMemo(() => buildSentimentData(steps), [steps]);
  const communityAdoption = useMemo(() => buildCommunityAdoption(steps), [steps]);
  const communityKeys = useMemo(() => getCommunityKeys(steps), [steps]);
  const emergentEvents = useMemo(() => collectEmergentEvents(steps), [steps]);

  // SPEC 26 §4.6 — Cascade Analytics
  const cascadeStats = useMemo(() => buildCascadeStats(steps), [steps]);

  // SPEC 26 §4.5.1 — distinct event types present, for filter chips
  const availableEventTypes = useMemo(() => {
    const seen = new Set<string>();
    for (const e of emergentEvents) seen.add(e.event_type);
    return [...seen];
  }, [emergentEvents]);

  // SPEC 26 §4.5.1 — filter narrows the timeline list only. Summary cards
  // and chart markers still use `emergentEvents` (unfiltered).
  const filteredEvents = useMemo(() => {
    if (activeFilter == null) return emergentEvents;
    return emergentEvents.filter((e) => e.event_type === activeFilter);
  }, [emergentEvents, activeFilter]);

  // Steps where emergent events occurred (for ReferenceLine markers) —
  // based on UNFILTERED events per SPEC §4.5.1.
  const eventSteps = [...new Set(emergentEvents.map((e) => e.step))];

  // SPEC 26 §4.5.2 — deep-link navigator (closed-over simulation id)
  const openEventInSimulation = useCallback(
    (e: EmergentEvent) => {
      if (!simulation?.simulation_id) return;
      navigate(`/simulation/${simulation.simulation_id}?step=${e.step}`);
    },
    [navigate, simulation?.simulation_id],
  );

  const handleEventRowKeyDown = useCallback(
    (e: KeyboardEvent<HTMLDivElement>, event: EmergentEvent) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        openEventInSimulation(event);
      }
    },
    [openEventInSimulation],
  );

  return (
    <div
      data-testid="analytics-page"
      className="min-h-screen bg-[var(--background)] text-[var(--foreground)]"
    >
      {/* Header */}
      <header className="flex items-center gap-4 px-6 py-4 border-b border-[var(--border)] bg-[var(--card)] sticky top-0 z-10">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-md hover:bg-[var(--secondary)] transition-colors"
          aria-label="Go back"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-[var(--primary)]" />
          <div>
            <h1 className="text-base font-semibold leading-tight">Post-Run Analytics</h1>
            {simulation && (
              <p className="text-xs text-[var(--muted-foreground)] truncate max-w-xs">
                {simulation.name}
              </p>
            )}
          </div>
        </div>
      </header>

      {/* Loading */}
      {loading && (
        <div className="flex items-center justify-center py-24">
          <span className="text-sm text-[var(--muted-foreground)] animate-pulse">
            Loading analytics...
          </span>
        </div>
      )}

      {/* Error */}
      {error && (
        <div className="flex items-center justify-center py-24">
          <span className="text-sm text-[var(--destructive)]">{error}</span>
        </div>
      )}

      {/* No simulation */}
      {!simulation && !loading && (
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <BarChart3 className="w-12 h-12 text-[var(--muted-foreground)]" />
          <p className="text-sm text-[var(--muted-foreground)]">
            No active simulation. Run a simulation first.
          </p>
          <button
            onClick={() => navigate("/projects")}
            className="mt-2 h-9 px-5 text-sm font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity"
          >
            Go to Projects
          </button>
        </div>
      )}

      {/* Empty steps */}
      {simulation && !loading && !error && steps.length === 0 && (
        <div className="flex flex-col items-center justify-center py-24 gap-3">
          <TrendingUp className="w-12 h-12 text-[var(--muted-foreground)]" />
          <p className="text-sm text-[var(--muted-foreground)]">
            No step data available yet. Run the simulation to generate analytics.
          </p>
        </div>
      )}

      {/* Analytics content */}
      {simulation && !loading && !error && steps.length > 0 && (
        <main className="max-w-5xl mx-auto px-6 py-8 flex flex-col gap-10">

          {/* Summary cards */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <SummaryCard
              label="Total Steps"
              value={String(steps[steps.length - 1].step)}
            />
            <SummaryCard
              label="Final Adoption"
              value={`${(steps[steps.length - 1].adoption_rate * 100).toFixed(1)}%`}
              accent="positive"
            />
            <SummaryCard
              label="Final Sentiment"
              value={steps[steps.length - 1].mean_sentiment.toFixed(3)}
              accent={steps[steps.length - 1].mean_sentiment >= 0 ? "positive" : "negative"}
            />
            <SummaryCard
              label="Emergent Events"
              value={String(emergentEvents.length)}
              accent={emergentEvents.length > 0 ? "warning" : undefined}
            />
          </div>

          {/* Adoption Rate Over Time */}
          <Section
            title="Adoption Rate Over Time"
            icon={<TrendingUp className="w-4 h-4 text-[var(--primary)]" />}
          >
            <div
              className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4"
              role="img"
              aria-label="Adoption rate over time, line chart"
            >
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={adoptionData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="step"
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    label={{ value: "Step", position: "insideBottom", offset: -2, fontSize: 11, fill: "var(--muted-foreground)" }}
                  />
                  <YAxis
                    unit="%"
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    domain={[0, 100]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      fontSize: "11px",
                    }}
                    formatter={(v) => `${v}%`}
                  />
                  <Legend wrapperStyle={{ fontSize: "11px" }} />
                  {/* Event markers */}
                  {eventSteps.map((step) => (
                    <ReferenceLine
                      key={step}
                      x={step}
                      stroke="var(--sentiment-warning)"
                      strokeDasharray="4 2"
                      strokeWidth={1.5}
                    />
                  ))}
                  {/* Total line */}
                  <Line
                    type="monotone"
                    dataKey="total"
                    name="Total"
                    stroke="var(--primary)"
                    strokeWidth={2}
                    dot={false}
                    activeDot={{ r: 4 }}
                  />
                  {/* Per-community lines */}
                  {communityKeys.map((cid, idx) => (
                    <Line
                      key={cid}
                      type="monotone"
                      dataKey={cid}
                      name={cid}
                      stroke={COMMUNITY_COLORS[idx % COMMUNITY_COLORS.length]}
                      strokeWidth={1.5}
                      strokeDasharray="4 2"
                      dot={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
              {eventSteps.length > 0 && (
                <p className="mt-1 text-[10px] text-[var(--sentiment-warning)]">
                  Dashed vertical lines indicate emergent events.
                </p>
              )}
            </div>
          </Section>

          {/* Sentiment Over Time */}
          <Section
            title="Mean Sentiment Over Time"
            icon={<BarChart3 className="w-4 h-4 text-[var(--community-alpha)]" />}
          >
            <div
              className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4"
              role="img"
              aria-label="Mean sentiment over time, line chart"
            >
              <ResponsiveContainer width="100%" height={180}>
                <LineChart data={sentimentData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="step"
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    domain={[-1, 1]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      fontSize: "11px",
                    }}
                  />
                  <ReferenceLine y={0} stroke="var(--border)" />
                  {eventSteps.map((step) => (
                    <ReferenceLine
                      key={step}
                      x={step}
                      stroke="var(--sentiment-warning)"
                      strokeDasharray="4 2"
                      strokeWidth={1.5}
                    />
                  ))}
                  <Line
                    type="monotone"
                    dataKey="sentiment"
                    name="Sentiment"
                    stroke="var(--community-alpha)"
                    strokeWidth={2}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </Section>

          {/* Community Adoption Comparison */}
          <Section
            title="Community Adoption Comparison (Final Step)"
            icon={<BarChart3 className="w-4 h-4 text-[var(--community-delta)]" />}
          >
            <div
              className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4"
              role="img"
              aria-label="Community adoption comparison at final step, bar chart"
            >
              <ResponsiveContainer width="100%" height={200}>
                <BarChart
                  data={communityAdoption}
                  margin={{ top: 5, right: 20, left: 0, bottom: 20 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                  <XAxis
                    dataKey="community"
                    tick={{ fontSize: 10, fill: "var(--muted-foreground)" }}
                    angle={-20}
                    textAnchor="end"
                  />
                  <YAxis
                    unit="%"
                    tick={{ fontSize: 11, fill: "var(--muted-foreground)" }}
                    domain={[0, 100]}
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "var(--card)",
                      border: "1px solid var(--border)",
                      borderRadius: "6px",
                      fontSize: "11px",
                    }}
                    formatter={(v) => [`${v}%`, "Adoption"]}
                  />
                  <Bar dataKey="rate" name="Adoption Rate" radius={[4, 4, 0, 0]}>
                    {communityAdoption.map((entry, idx) => (
                      <rect key={idx} fill={entry.color} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Fallback: simple bar divs if recharts bar color doesn't work */}
            <div className="flex flex-col gap-2">
              {communityAdoption.map((entry, idx) => (
                <div key={entry.community} className="flex items-center gap-3">
                  <div
                    className="w-3 h-3 rounded-sm shrink-0"
                    style={{ backgroundColor: COMMUNITY_COLORS[idx % COMMUNITY_COLORS.length] }}
                  />
                  <span className="text-xs text-[var(--muted-foreground)] w-32 truncate">
                    {entry.community}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-[var(--secondary)] overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${entry.rate}%`,
                        backgroundColor: COMMUNITY_COLORS[idx % COMMUNITY_COLORS.length],
                      }}
                    />
                  </div>
                  <span className="text-xs font-mono text-[var(--foreground)] w-10 text-right">
                    {entry.rate}%
                  </span>
                </div>
              ))}
            </div>
          </Section>

          {/* Cascade Analytics (SPEC 26 §4.6, v0.2.0) */}
          <Section
            title="Cascade Analytics"
            icon={<GitBranch className="w-4 h-4 text-[var(--community-gamma)]" />}
          >
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              <CascadeStatCard
                testId="cascade-depth"
                label="Longest Cascade Run"
                value={cascadeStats.depth}
              />
              <CascadeStatCard
                testId="cascade-width"
                label="Peak Adoption Delta"
                value={cascadeStats.width}
              />
              <CascadeStatCard
                testId="cascade-paths"
                label="Viral / Cascade Events"
                value={cascadeStats.paths}
              />
              <CascadeStatCard
                testId="cascade-decay"
                label="Decay Rate"
                value={cascadeStats.decay}
              />
            </div>
          </Section>

          {/* Emergent Event Timeline */}
          <Section
            title="Emergent Event Timeline"
            icon={<AlertTriangle className="w-4 h-4 text-[var(--sentiment-warning)]" />}
          >
            {emergentEvents.length === 0 ? (
              <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-6 text-center">
                <p className="text-sm text-[var(--muted-foreground)]">
                  No emergent events detected during this simulation.
                </p>
              </div>
            ) : (
              <>
                {/* Filter toolbar — SPEC 26 §4.5.1 (v0.2.0) */}
                <div className="flex flex-wrap items-center gap-2">
                  <FilterChip
                    testId="event-filter-all"
                    label="All"
                    pressed={activeFilter === null}
                    onClick={() => setActiveFilter(null)}
                  />
                  {availableEventTypes.map((t) => (
                    <FilterChip
                      key={t}
                      testId={`event-filter-${t}`}
                      label={t.replace(/_/g, " ")}
                      pressed={activeFilter === t}
                      onClick={() => setActiveFilter(t)}
                    />
                  ))}
                </div>

                {filteredEvents.length === 0 ? (
                  <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-6 text-center">
                    <p className="text-sm text-[var(--muted-foreground)]">
                      No events match the current filter.
                    </p>
                  </div>
                ) : (
                  <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] divide-y divide-[var(--border)] overflow-hidden">
                    {filteredEvents.map((e, i) => (
                      <div
                        key={i}
                        role="button"
                        tabIndex={0}
                        aria-label={`View step ${e.step} in simulation`}
                        onClick={() => openEventInSimulation(e)}
                        onKeyDown={(ev) => handleEventRowKeyDown(ev, e)}
                        className="flex items-start gap-4 px-4 py-3 cursor-pointer hover:bg-[var(--secondary)]/50 focus:outline-none focus:bg-[var(--secondary)]/70 transition-colors"
                      >
                        <span className="shrink-0 font-mono text-xs text-[var(--muted-foreground)] w-14">
                          Step {e.step}
                        </span>
                        <span className="shrink-0 text-base" title={e.event_type}>
                          {EVENT_ICONS[e.event_type] ?? "📌"}
                        </span>
                        <div className="flex flex-col gap-0.5 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-medium text-[var(--foreground)] capitalize">
                              {(e.event_type ?? "event").replace(/_/g, " ")}
                            </span>
                            {e.community_id && (
                              <span className="text-[10px] px-1.5 py-0.5 rounded bg-[var(--secondary)] text-[var(--muted-foreground)]">
                                {e.community_id}
                              </span>
                            )}
                            <span className={`text-[10px] font-mono ${severityColor(e.severity)}`}>
                              sev {e.severity.toFixed(2)}
                            </span>
                          </div>
                          <p className="text-xs text-[var(--muted-foreground)] line-clamp-2">
                            {e.description}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </Section>

        </main>
      )}
    </div>
  );
}

function SummaryCard({
  label,
  value,
  accent,
}: {
  label: string;
  value: string;
  accent?: "positive" | "negative" | "warning";
}) {
  const valueClass =
    accent === "positive"
      ? "text-[var(--sentiment-positive)]"
      : accent === "negative"
        ? "text-[var(--sentiment-negative)]"
        : accent === "warning"
          ? "text-[var(--sentiment-warning)]"
          : "text-[var(--foreground)]";

  return (
    <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-4 py-3 flex flex-col gap-1">
      <p className="text-[10px] font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
        {label}
      </p>
      <p className={`text-xl font-bold ${valueClass}`}>{value}</p>
    </div>
  );
}

/**
 * CascadeStatCard — SPEC 26 §4.6.
 * Like SummaryCard but wraps with a data-testid so the test contract can
 * scope value assertions to an individual card. No accent variants; cascade
 * stats are neutral.
 */
function CascadeStatCard({
  testId,
  label,
  value,
}: {
  testId: string;
  label: string;
  value: string;
}) {
  return (
    <div
      data-testid={testId}
      className="rounded-lg border border-[var(--border)] bg-[var(--card)] px-4 py-3 flex flex-col gap-1"
    >
      <p className="text-[10px] font-medium uppercase tracking-wide text-[var(--muted-foreground)]">
        {label}
      </p>
      <p className="text-xl font-bold text-[var(--foreground)] font-mono">{value}</p>
    </div>
  );
}

/**
 * FilterChip — SPEC 26 §4.5.1.
 * Single-select filter toggle for the event timeline. aria-pressed reflects
 * state; Enter/Space activates via the native button semantics of <button>.
 */
function FilterChip({
  testId,
  label,
  pressed,
  onClick,
}: {
  testId: string;
  label: string;
  pressed: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      data-testid={testId}
      aria-pressed={pressed}
      onClick={onClick}
      className={`text-xs px-2.5 py-1 rounded-full border transition-colors capitalize ${
        pressed
          ? "border-[var(--primary)] bg-[var(--primary)] text-[var(--primary-foreground)]"
          : "border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/50"
      }`}
    >
      {label}
    </button>
  );
}

