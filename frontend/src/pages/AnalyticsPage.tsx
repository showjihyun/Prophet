/**
 * AnalyticsPage — Post-run analytics for a completed simulation.
 * @spec docs/spec/07_FRONTEND_SPEC.md#simulationsidanalytics
 */
import { useEffect, useState } from "react";
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
import { ArrowLeft, TrendingUp, AlertTriangle, BarChart3, Zap } from "lucide-react";
import { useSimulationStore } from "../store/simulationStore";
import { apiClient } from "../api/client";
import { LS_KEY_MC_PREFIX } from "@/config/constants";
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
  const storeSteps = useSimulationStore((s) => s.steps);

  const [fetchedSteps, setFetchedSteps] = useState<StepResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Derive steps: prefer store (live), fall back to locally fetched
  const steps = storeSteps.length > 0 ? storeSteps : fetchedSteps;

  // Fetch steps from API only when store is empty
  useEffect(() => {
    if (storeSteps.length > 0) return;
    if (!simulation) return;

    const simulationId = simulation.simulation_id;
    queueMicrotask(() => setLoading(true));
    apiClient.simulations
      .getSteps(simulationId)
      .then((fetched) => {
        setFetchedSteps(fetched);
        setLoading(false);
      })
      .catch((err) => {
        setError(err instanceof Error ? err.message : "Failed to load steps");
        setLoading(false);
      });
  }, [simulation, storeSteps.length]);

  const adoptionData = buildAdoptionData(steps);
  const sentimentData = buildSentimentData(steps);
  const communityAdoption = buildCommunityAdoption(steps);
  const communityKeys = getCommunityKeys(steps);
  const emergentEvents = collectEmergentEvents(steps);

  // Steps where emergent events occurred (for ReferenceLine markers)
  const eventSteps = [...new Set(emergentEvents.map((e) => e.step))];

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
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
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
                    formatter={(v: number) => [`${v}%`]}
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
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
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
            <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] p-4">
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
                    formatter={(v: number) => [`${v}%`, "Adoption"]}
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
              <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] divide-y divide-[var(--border)] overflow-hidden">
                {emergentEvents.map((e, i) => (
                  <div key={i} className="flex items-start gap-4 px-4 py-3">
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
          </Section>

          {/* Monte Carlo Results */}
          <Section
            title="Monte Carlo Results"
            icon={<Zap className="w-4 h-4 text-[var(--community-bridge)]" />}
          >
            <MonteCarloSection simulationId={simulation?.simulation_id ?? null} />
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

function MonteCarloSection({ simulationId }: { simulationId: string | null }) {
  const [mcData, setMcData] = useState<Record<string, unknown> | null>(null);

  // Load MC results: API first (PostgreSQL), localStorage fallback
  useEffect(() => {
    if (!simulationId) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await apiClient.simulations.getLatestMonteCarlo(simulationId);
        if (!cancelled && res) { queueMicrotask(() => setMcData(res)); return; }
      } catch { /* API unavailable, try localStorage */ }
      try {
        const stored = localStorage.getItem(`${LS_KEY_MC_PREFIX}${simulationId}`);
        if (!cancelled && stored) queueMicrotask(() => setMcData(JSON.parse(stored)));
      } catch { /* ignore */ }
    })();
    return () => { cancelled = true; };
  }, [simulationId]);

  if (!mcData || mcData.status !== "completed") {
    return (
      <div className="rounded-xl border border-[var(--border)] bg-[var(--card)] px-4 py-6 text-center">
        <Zap className="w-8 h-8 text-[var(--muted-foreground)] mx-auto mb-2" />
        <p className="text-sm text-[var(--muted-foreground)]">
          No Monte Carlo results for this simulation.
        </p>
        <p className="text-xs text-[var(--muted-foreground)] mt-1">
          Run a Monte Carlo analysis from the simulation control panel to see results here.
        </p>
      </div>
    );
  }

  const vp = typeof mcData.viral_probability === "number" ? mcData.viral_probability : 0;
  const reach = typeof mcData.expected_reach === "number" ? mcData.expected_reach : 0;
  const p5 = typeof mcData.p5_reach === "number" ? mcData.p5_reach : 0;
  const p50 = typeof mcData.p50_reach === "number" ? mcData.p50_reach : 0;
  const p95 = typeof mcData.p95_reach === "number" ? mcData.p95_reach : 0;
  const communityAdoption = (mcData.community_adoption ?? {}) as Record<string, number>;

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <SummaryCard label="Viral Probability" value={`${(vp * 100).toFixed(1)}%`} accent={vp > 0.5 ? "positive" : "warning"} />
        <SummaryCard label="Expected Reach" value={String(Math.round(reach))} />
        <SummaryCard label="P5 (pessimistic)" value={String(Math.round(p5))} accent="negative" />
        <SummaryCard label="P50 (median)" value={String(Math.round(p50))} />
        <SummaryCard label="P95 (optimistic)" value={String(Math.round(p95))} accent="positive" />
      </div>
      {Object.keys(communityAdoption).length > 0 && (
        <div className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-4">
          <h4 className="text-sm font-medium text-[var(--foreground)] mb-3">Community Adoption</h4>
          <div className="space-y-2">
            {Object.entries(communityAdoption).map(([cid, rate]) => (
              <div key={cid} className="flex items-center gap-3">
                <span className="text-xs text-[var(--muted-foreground)] w-24 truncate">{cid}</span>
                <div className="flex-1 h-2 bg-[var(--secondary)] rounded-full overflow-hidden">
                  <div className="h-full bg-[var(--primary)] rounded-full" style={{ width: `${(rate as number) * 100}%` }} />
                </div>
                <span className="text-xs font-medium text-[var(--foreground)] w-12 text-right">
                  {((rate as number) * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
