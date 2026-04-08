/**
 * GlobalMetricsPage — Global Insight & Metrics dashboard.
 * @spec docs/spec/ui/UI_05_GLOBAL_METRICS.md
 *
 * Applied Skills: react-state-management (Zustand selectors for derived data).
 */
import { useEffect, useMemo, useState, useRef } from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from "recharts";
import PageNav from "../components/shared/PageNav";
import StatCard from "../components/shared/StatCard";
import { apiClient } from "../api/client";
import { useSimulationSteps } from "../api/queries";
import { useSimulationStore } from "../store/simulationStore";
import type { CommunityStepMetrics } from "../types/simulation";

const COMMUNITY_COLORS = [
  "var(--community-alpha)", "var(--community-beta)", "var(--community-gamma)",
  "var(--community-delta)", "var(--community-bridge)",
];

function polarizationColor(v: number): string {
  if (v < 0.3) return "var(--sentiment-positive)";
  if (v < 0.6) return "var(--sentiment-warning)";
  return "var(--sentiment-negative)";
}

export default function GlobalMetricsPage() {
  const simulation = useSimulationStore((s) => s.simulation);
  // FE-PERF-H2: subscribe to length + latestStep, read full array lazily inside memos
  const stepsLength = useSimulationStore((s) => s.steps.length);
  const latestStep = useSimulationStore((s) => s.latestStep);
  const simId = simulation?.simulation_id ?? null;

  // TanStack Query — only enabled when the live store is empty.
  // Cached across navigations.
  const stepsQuery = useSimulationSteps(stepsLength === 0 ? simId : null);
  // Hydrate the store once when fetched data arrives.
  useEffect(() => {
    if (stepsQuery.data && stepsLength === 0) {
      useSimulationStore.getState().setStepsBulk(stepsQuery.data);
    }
  }, [stepsQuery.data, stepsLength]);

  const totalAgents = useMemo(() => {
    if (!latestStep?.community_metrics) return 0;
    return Object.values(latestStep.community_metrics).reduce(
      (sum: number, cm: CommunityStepMetrics) => sum + (cm.adoption_count ?? 0) / Math.max(cm.adoption_rate ?? 1, 0.001), 0,
    );
  }, [latestStep]);

  const polarizationData = useMemo(() => {
    // Lazy read — re-runs when latestStep / stepsLength change
    const recent = useSimulationStore.getState().steps.slice(-10);
    return recent.map((s) => ({
      day: `D${s.step}`,
      value: s.sentiment_variance ?? 0,
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestStep, stepsLength]);

  const sentimentByCommunity = useMemo(() => {
    if (!latestStep?.community_metrics) return [];
    return Object.entries(latestStep.community_metrics).map(([cid, cm]: [string, CommunityStepMetrics], idx) => {
      const belief = cm.mean_belief ?? 0;
      // Derive sentiment distribution from belief (-1 to +1)
      const positive = Math.max(0, Math.round((belief + 1) / 2 * 100));
      const negative = Math.max(0, Math.round((1 - belief) / 2 * 30));
      const neutral = Math.max(0, 100 - positive - negative);
      return {
        name: cm.community_id ? String(cm.community_id).slice(0, 8) : cid.slice(0, 8),
        positive,
        neutral,
        negative,
        color: COMMUNITY_COLORS[idx % COMMUNITY_COLORS.length],
      };
    });
  }, [latestStep]);

  // Real tier distribution from /llm/stats endpoint.
  // Previously this was computed as `slmLlmRatio * totalAgents` which is a
  // slider value, not actual telemetry — it bore no relation to what the
  // engine really did. Now we call the real endpoint and map its
  // tier_breakdown (tier number → call count) directly.
  type LLMStatsResponse = {
    total_calls: number;
    tier_breakdown?: Record<string, number>;
  };
  const [llmStats, setLlmStats] = useState<LLMStatsResponse | null>(null);
  // Poll LLM stats at most every 5 steps to avoid flooding the backend
  // during fast simulations (speed 10 = 100ms/step = 10 req/s without this).
  useEffect(() => {
    if (!simId) { setLlmStats(null); return; }
    if (latestStep > 0 && latestStep % 5 !== 0) return;
    let cancelled = false;
    apiClient.llm.getStats(simId)
      .then((res) => {
        if (!cancelled) setLlmStats(res as LLMStatsResponse);
      })
      .catch(() => {
        if (!cancelled) setLlmStats(null);
      });
    return () => { cancelled = true; };
  }, [simId, latestStep]);

  const tierStats = useMemo(() => {
    const breakdown = llmStats?.tier_breakdown ?? {};
    const t1 = Number(breakdown["1"] ?? breakdown[1] ?? 0);
    const t2 = Number(breakdown["2"] ?? breakdown[2] ?? 0);
    const t3 = Number(breakdown["3"] ?? breakdown[3] ?? 0);
    const total = Math.max(t1 + t2 + t3, 1);
    return {
      t1, t2, t3,
      t1Pct: ((t1 / total) * 100).toFixed(1),
      t2Pct: ((t2 / total) * 100).toFixed(1),
      t3Pct: ((t3 / total) * 100).toFixed(1),
      hasData: t1 + t2 + t3 > 0,
    };
  }, [llmStats]);

  // Cascade analytics — derived from real step history and emergent events.
  //   depth:  longest consecutive run of non-zero-diffusion steps (the
  //           classic "cascade depth" definition from SPEC 03_DIFFUSION)
  //   width:  maximum adoption delta seen in any single step
  //   paths:  count of emergent events with "cascade"/"viral" in event_type
  //   decay:  drop in diffusion_rate from peak → latest step
  const cascadeStats = useMemo(() => {
    const steps = useSimulationStore.getState().steps;
    if (steps.length === 0) return { depth: "0", width: "0", paths: "0", decay: "0/step" };

    // Longest consecutive run of active propagation
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

    // Widest single-step propagation (peak adoption delta)
    let peakDelta = 0;
    let prevAdopt = 0;
    for (const s of steps) {
      const delta = (s.total_adoption ?? 0) - prevAdopt;
      if (delta > peakDelta) peakDelta = delta;
      prevAdopt = s.total_adoption ?? 0;
    }

    // Real cascade event count from emergent_events
    const cascadeEvents = steps.reduce((sum, s) => {
      const events = s.emergent_events ?? [];
      return sum + events.filter((e) => {
        const t = (e.event_type ?? "").toLowerCase();
        return t.includes("cascade") || t.includes("viral");
      }).length;
    }, 0);

    // Decay: peak diffusion_rate vs latest
    const diffRates = steps.map((s) => s.diffusion_rate ?? 0);
    const peakRate = Math.max(...diffRates, 0);
    const latestRate = diffRates[diffRates.length - 1] ?? 0;
    const decay = peakRate > 0 ? ((peakRate - latestRate) / peakRate).toFixed(2) : "0";

    return {
      depth: String(longestRun),
      width: String(peakDelta),
      paths: String(cascadeEvents),
      decay: `${decay}/step`,
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestStep, stepsLength]);

  const currentStep = latestStep?.step ?? 0;
  const maxSteps = simulation?.max_steps ?? 365;
  const polarization = latestStep?.sentiment_variance ?? 0;
  // prevPol: read from store lazily — only changes when latestStep changes
  const prevPol = useMemo(() => {
    const steps = useSimulationStore.getState().steps;
    return steps.length >= 2 ? steps[steps.length - 2]?.sentiment_variance ?? 0 : 0;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestStep]);
  const polDelta = polarization - prevPol;
  const activeCascades = latestStep ? Math.round((latestStep.adoption_rate ?? 0) * Math.max(totalAgents, 1)) : 0;

  // Check if we have real data or should show "no data" state
  const hasData = stepsLength > 0;

  const [exportOpen, setExportOpen] = useState(false);
  const exportRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!exportOpen) return;
    function handleClickOutside(e: MouseEvent) {
      if (exportRef.current && !exportRef.current.contains(e.target as Node)) {
        setExportOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [exportOpen]);

  function handleExport(format: 'json' | 'csv') {
    if (simId) apiClient.simulations.export(simId, format);
    setExportOpen(false);
  }

  return (
    <div data-testid="global-metrics-page" className="min-h-screen bg-[var(--background)] flex flex-col">
      <PageNav
        breadcrumbs={[{ label: "Back to Simulation", href: "/" }, { label: "Global Insight & Metrics" }]}
        actions={
          <div className="relative" ref={exportRef}>
            <button
              onClick={() => setExportOpen((o) => !o)}
              disabled={!simId}
              className="h-9 px-4 text-sm font-medium border border-[var(--border)] rounded-md bg-[var(--card)] hover:bg-[var(--secondary)] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              title={simId ? "Export data" : "No active simulation"}
            >
              <DownloadIcon /> Export <ChevronDownIcon />
            </button>
            {exportOpen && (
              <div className="absolute right-0 mt-1 w-40 rounded-md border border-[var(--border)] bg-[var(--card)] shadow-lg z-50 overflow-hidden">
                <button
                  onClick={() => handleExport('json')}
                  className="w-full text-left px-4 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--secondary)] flex items-center gap-2"
                >
                  <DownloadIcon /> Export JSON
                </button>
                <button
                  onClick={() => handleExport('csv')}
                  className="w-full text-left px-4 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--secondary)] flex items-center gap-2"
                >
                  <DownloadIcon /> Export CSV
                </button>
                <button
                  onClick={() => { window.print(); setExportOpen(false); }}
                  className="w-full text-left px-4 py-2 text-sm text-[var(--foreground)] hover:bg-[var(--secondary)] flex items-center gap-2"
                >
                  <DownloadIcon /> Export PDF
                </button>
              </div>
            )}
          </div>
        }
      />

      <div className="flex-1 p-6 flex flex-col gap-6 overflow-auto">
        {!hasData && (
          <div className="text-center py-12 text-[var(--muted-foreground)]">
            <p className="text-lg font-medium">No simulation data yet</p>
            <p className="text-sm mt-1">Run a simulation to see global metrics here.</p>
          </div>
        )}

        {/* Summary Stats */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard label="Total Agents" value={hasData ? totalAgents.toLocaleString() : "—"} change={hasData ? "active" : "no data"} changeType="positive" icon={<UsersIcon />} changeTestId="total-agents-delta" />
          <StatCard label="Active Cascades" value={hasData ? activeCascades.toLocaleString() : "—"} change={hasData ? `step ${currentStep}` : "no data"} changeType="positive" icon={<ZapIcon />} changeTestId="cascades-delta" />
          <StatCard label="Polarization" value={hasData ? polarization.toFixed(2) : "—"} change={hasData ? `${polDelta >= 0 ? "+" : ""}${polDelta.toFixed(2)} from prev` : "no data"} changeType={polDelta > 0 ? "negative" : "positive"} icon={<ActivityIcon />} changeTestId="polarization-delta" />
          <div>
            <StatCard label="Simulation Day" value={hasData ? `Day ${currentStep}` : "—"} change={`of ${maxSteps} days`} changeType="neutral" icon={<CalendarIcon />} />
            <div data-testid="sim-day-progress" className="mt-2 h-1.5 rounded-full" style={{ backgroundColor: 'var(--muted)' }}>
              <div className="h-full rounded-full" style={{ width: `${(currentStep / maxSteps) * 100}%`, backgroundColor: 'var(--primary)' }} />
            </div>
          </div>
        </div>

        {/* Charts Area */}
        {hasData && (
          <div className="grid grid-cols-2 gap-6">
            {/* Polarization Trend */}
            <div data-testid="polarization-trend-chart" className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
              <h3 className="text-base font-semibold text-[var(--foreground)] mb-4">Polarization Trend</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={polarizationData} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} tickCount={6} />
                  <Tooltip formatter={(value: number) => [value.toFixed(2), "Polarization Index"]} />
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {polarizationData.map((entry, i) => (
                      <Cell key={i} fill={polarizationColor(entry.value)} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>

            {/* Sentiment by Community */}
            <div data-testid="sentiment-community-chart" className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
              <h3 className="text-base font-semibold text-[var(--foreground)] mb-4">Sentiment by Community</h3>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={sentimentByCommunity} layout="vertical" margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                  <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <YAxis type="category" dataKey="name" width={56} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(value: number, name: string) => [`${value}%`, name.charAt(0).toUpperCase() + name.slice(1)]} />
                  <Bar dataKey="positive" stackId="sentiment" fill="var(--sentiment-positive)" name="Positive" />
                  <Bar dataKey="neutral" stackId="sentiment" fill="var(--sentiment-neutral)" name="Neutral" />
                  <Bar dataKey="negative" stackId="sentiment" fill="var(--sentiment-negative)" name="Negative" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* Bottom Area */}
        {hasData && (
          <div className="grid grid-cols-2 gap-6">
            {/* Prophet 3-Tier Cost Optimization */}
            <div className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
              <h3 className="text-base font-semibold text-[var(--foreground)] mb-4">Prophet 3-Tier Cost Optimization</h3>
              <div className="space-y-3">
                <TierCard testId="tier1-card" tier="Tier 1: Mass SLM" count={`${tierStats.t1.toLocaleString()} agents`} description="Rule-based + local SLM inference" color="var(--community-alpha)" icon={<CpuIcon />} />
                <TierCard testId="tier2-card" tier="Tier 2: Semantic" count={`${tierStats.t2.toLocaleString()} agents`} description="Heuristic + semantic analysis" color="var(--sentiment-warning)" icon={<BrainIcon />} />
                <TierCard testId="tier3-card" tier="Tier 3: Elite LLM" count={`${tierStats.t3.toLocaleString()} agents`} description="Full LLM reasoning (Claude/GPT)" color="var(--community-delta)" icon={<SparklesIcon />} />
              </div>
              <div className="mt-4">
                <div className="flex h-3 rounded-full overflow-hidden">
                  <div style={{ width: `${tierStats.t1Pct}%`, backgroundColor: "var(--community-alpha)" }} />
                  <div style={{ width: `${tierStats.t2Pct}%`, backgroundColor: "var(--sentiment-warning)" }} />
                  <div style={{ width: `${tierStats.t3Pct}%`, backgroundColor: "var(--community-delta)" }} />
                </div>
                <div className="flex justify-between text-[10px] text-[var(--muted-foreground)] mt-1">
                  <span>Tier 1 ({tierStats.t1Pct}%)</span>
                  <span>Tier 2 ({tierStats.t2Pct}%)</span>
                  <span>Tier 3 ({tierStats.t3Pct}%)</span>
                </div>
              </div>
            </div>

            {/* Cascade Analytics */}
            <div className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
              <h3 className="text-base font-semibold text-[var(--foreground)] mb-4">Cascade Analytics</h3>
              <div className="grid grid-cols-2 gap-3">
                <CascadeStat testId="avg-cascade-depth" label="Avg Cascade Depth" value={cascadeStats.depth} color="var(--community-alpha)" icon={<GitBranchIcon />} />
                <CascadeStat testId="max-cascade-width" label="Max Cascade Width" value={cascadeStats.width} color="var(--community-beta)" icon={<GitMergeIcon />} />
                <CascadeStat testId="critical-path" label="Critical Paths" value={cascadeStats.paths} color="var(--community-gamma)" icon={<RouteIcon />} />
                <CascadeStat testId="decay-rate" label="Decay Rate" value={cascadeStats.decay} color="var(--community-bridge)" icon={<TrendDownIcon />} />
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/* Sub-components */
function TierCard({ tier, count, description, color, icon, testId }: { tier: string; count: string; description: string; color: string; icon: React.ReactNode; testId?: string }) {
  return (
    <div data-testid={testId} className="flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] hover:shadow-sm transition-shadow" style={{ borderLeftColor: color, borderLeftWidth: 3 }}>
      <span style={{ color }}>{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-[var(--foreground)]">{tier}</div>
        <div className="text-xl font-bold text-[var(--foreground)]">{count}</div>
        <div className="text-xs text-[var(--muted-foreground)]">{description}</div>
      </div>
    </div>
  );
}

function CascadeStat({ label, value, color, icon, testId }: { label: string; value: string; color: string; icon: React.ReactNode; testId?: string }) {
  return (
    <div data-testid={testId} className="p-3 rounded-lg border border-[var(--border)] flex flex-col gap-1">
      <span style={{ color }}>{icon}</span>
      <span className="text-2xl font-bold text-[var(--foreground)]">{value}</span>
      <span className="text-xs text-[var(--muted-foreground)]">{label}</span>
    </div>
  );
}

/* Inline icons */
function UsersIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" /></svg>; }
function ZapIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" /></svg>; }
function ActivityIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12" /></svg>; }
function CalendarIcon() { return <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" /></svg>; }
function DownloadIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" /></svg>; }
function ChevronDownIcon() { return <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="6 9 12 15 18 9" /></svg>; }
function CpuIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" /><line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" /><line x1="20" y1="9" x2="23" y2="9" /><line x1="20" y1="14" x2="23" y2="14" /><line x1="1" y1="9" x2="4" y2="9" /><line x1="1" y1="14" x2="4" y2="14" /></svg>; }
function BrainIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" /><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" /></svg>; }
function SparklesIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" /><path d="M5 3v4" /><path d="M19 17v4" /><path d="M3 5h4" /><path d="M17 19h4" /></svg>; }
function GitBranchIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="6" y1="3" x2="6" y2="15" /><circle cx="18" cy="6" r="3" /><circle cx="6" cy="18" r="3" /><path d="M18 9a9 9 0 0 1-9 9" /></svg>; }
function GitMergeIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="18" r="3" /><circle cx="6" cy="6" r="3" /><path d="M6 21V9a9 9 0 0 0 9 9" /></svg>; }
function RouteIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="6" cy="19" r="3" /><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15" /><circle cx="18" cy="5" r="3" /></svg>; }
function TrendDownIcon() { return <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="23 18 13.5 8.5 8.5 13.5 1 6" /><polyline points="17 18 23 18 23 12" /></svg>; }
