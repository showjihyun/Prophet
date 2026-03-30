/**
 * GlobalMetricsPage — Global Insight & Metrics dashboard.
 * @spec docs/spec/ui/UI_05_GLOBAL_METRICS.md
 */
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
import { useSimulationStore } from "../store/simulationStore";

const POLARIZATION_DATA = [
  { day: "D41", value: 0.42 },
  { day: "D42", value: 0.48 },
  { day: "D43", value: 0.53 },
  { day: "D44", value: 0.58 },
  { day: "D45", value: 0.64 },
  { day: "D46", value: 0.68 },
  { day: "D47", value: 0.72 },
];

function polarizationColor(v: number): string {
  if (v < 0.3) return "var(--sentiment-positive)";
  if (v < 0.6) return "var(--sentiment-warning)";
  return "var(--sentiment-negative)";
}

const SENTIMENT_BY_COMMUNITY = [
  { name: "Alpha", positive: 62, neutral: 25, negative: 13, color: "var(--community-alpha)" },
  { name: "Beta", positive: 55, neutral: 30, negative: 15, color: "var(--community-beta)" },
  { name: "Gamma", positive: 40, neutral: 35, negative: 25, color: "var(--community-gamma)" },
  { name: "Delta", positive: 48, neutral: 32, negative: 20, color: "var(--community-delta)" },
  { name: "Bridge", positive: 35, neutral: 40, negative: 25, color: "var(--community-bridge)" },
];

export default function GlobalMetricsPage() {
  const simulation = useSimulationStore((s) => s.simulation);
  const simId = simulation?.simulation_id ?? null;

  function handleExport(format: 'json' | 'csv') {
    if (simId) {
      apiClient.simulations.export(simId, format);
    }
  }

  return (
    <div
      data-testid="global-metrics-page"
      className="min-h-screen bg-[var(--background)] flex flex-col"
    >
      <PageNav
        breadcrumbs={[{ label: "Back to Simulation", href: "/" }, { label: "Global Insight & Metrics" }]}
        actions={
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleExport('json')}
              disabled={!simId}
              className="h-9 px-4 text-sm font-medium border border-[var(--border)] rounded-md bg-[var(--card)] hover:bg-[var(--secondary)] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              title={simId ? "Export as JSON" : "No active simulation"}
            >
              <DownloadIcon />
              Export JSON
            </button>
            <button
              onClick={() => handleExport('csv')}
              disabled={!simId}
              className="h-9 px-4 text-sm font-medium border border-[var(--border)] rounded-md bg-[var(--card)] hover:bg-[var(--secondary)] flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
              title={simId ? "Export as CSV" : "No active simulation"}
            >
              <DownloadIcon />
              Export CSV
            </button>
          </div>
        }
      />

      <div className="flex-1 p-6 flex flex-col gap-6 overflow-auto">
        {/* Summary Stats */}
        <div className="grid grid-cols-4 gap-4">
          <StatCard
            label="Total Agents"
            value="6,500"
            change="+2% system"
            changeType="positive"
            icon={<UsersIcon />}
            changeTestId="total-agents-delta"
          />
          <StatCard
            label="Active Cascades"
            value="847"
            change="+12 today"
            changeType="positive"
            icon={<ZapIcon />}
            changeTestId="cascades-delta"
          />
          <StatCard
            label="Polarization"
            value="0.72"
            change="+0.08 from Day 46"
            changeType="negative"
            icon={<ActivityIcon />}
            changeTestId="polarization-delta"
          />
          <div>
            <StatCard
              label="Simulation Day"
              value="Day 47"
              change="of 365 days"
              changeType="neutral"
              icon={<CalendarIcon />}
            />
            <div data-testid="sim-day-progress" className="mt-2 h-1.5 rounded-full" style={{ backgroundColor: 'var(--muted)' }}>
              <div className="h-full rounded-full" style={{ width: `${(47 / 365) * 100}%`, backgroundColor: 'var(--primary)' }} />
            </div>
          </div>
        </div>

        {/* Charts Area - 2 column */}
        <div className="grid grid-cols-2 gap-6">
          {/* Polarization Trend */}
          <div data-testid="polarization-trend-chart" className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
            <h3 className="text-base font-semibold text-[var(--foreground)] mb-4">
              Polarization Trend
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={POLARIZATION_DATA}
                margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
              >
                <XAxis dataKey="day" tick={{ fontSize: 11 }} />
                <YAxis domain={[0, 1]} tick={{ fontSize: 11 }} tickCount={6} />
                <Tooltip
                  formatter={(value: number) => [
                    value.toFixed(2),
                    "Polarization Index",
                  ]}
                />
                <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                  {POLARIZATION_DATA.map((entry, i) => (
                    <Cell key={i} fill={polarizationColor(entry.value)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>

          {/* Sentiment by Community */}
          <div data-testid="sentiment-community-chart" className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
            <h3 className="text-base font-semibold text-[var(--foreground)] mb-4">
              Sentiment by Community
            </h3>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart
                data={SENTIMENT_BY_COMMUNITY}
                layout="vertical"
                margin={{ top: 8, right: 8, bottom: 0, left: 0 }}
              >
                <XAxis type="number" domain={[0, 100]} tick={{ fontSize: 11 }} />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={56}
                  tick={{ fontSize: 11 }}
                />
                <Tooltip
                  formatter={(value: number, name: string) => [
                    `${value}%`,
                    name.charAt(0).toUpperCase() + name.slice(1),
                  ]}
                />
                <Bar
                  dataKey="positive"
                  stackId="sentiment"
                  fill="var(--sentiment-positive)"
                  name="Positive"
                />
                <Bar
                  dataKey="neutral"
                  stackId="sentiment"
                  fill="var(--sentiment-neutral)"
                  name="Neutral"
                />
                <Bar
                  dataKey="negative"
                  stackId="sentiment"
                  fill="var(--sentiment-negative)"
                  name="Negative"
                  radius={[0, 4, 4, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bottom Area - 2 column */}
        <div className="grid grid-cols-2 gap-6">
          {/* Prophet 3-Tier Cost Optimization */}
          <div className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
            <h3 className="text-base font-semibold text-[var(--foreground)] mb-4">
              Prophet 3-Tier Cost Optimization
            </h3>
            <div className="space-y-3">
              <TierCard
                testId="tier1-card"
                tier="Tier 1: Mass SLM"
                count="4,800 agents"
                description="Rule-based + local SLM inference"
                color="var(--community-alpha)"
                icon={<CpuIcon />}
              />
              <TierCard
                testId="tier2-card"
                tier="Tier 2: Semantic"
                count="1,700 agents"
                description="Heuristic + semantic analysis"
                color="var(--sentiment-warning)"
                icon={<BrainIcon />}
              />
              <TierCard
                testId="tier3-card"
                tier="Tier 3: Elite LLM"
                count="~0 agents"
                description="Full LLM reasoning (Claude/GPT)"
                color="var(--community-delta)"
                icon={<SparklesIcon />}
              />
            </div>
            {/* Cost distribution bar */}
            <div className="mt-4">
              <div className="flex h-3 rounded-full overflow-hidden">
                <div style={{ width: "73.8%", backgroundColor: "var(--community-alpha)" }} />
                <div style={{ width: "26.2%", backgroundColor: "var(--sentiment-warning)" }} />
                <div style={{ width: "0%", backgroundColor: "var(--community-delta)" }} />
              </div>
              <div className="flex justify-between text-[10px] text-[var(--muted-foreground)] mt-1">
                <span>Tier 1 (73.8%)</span>
                <span>Tier 2 (26.2%)</span>
                <span>Tier 3 (0%)</span>
              </div>
            </div>
          </div>

          {/* Cascade Analytics */}
          <div className="bg-[var(--card)] rounded-lg border border-[var(--border)] shadow-sm p-4">
            <h3 className="text-base font-semibold text-[var(--foreground)] mb-4">
              Cascade Analytics
            </h3>
            <div className="grid grid-cols-2 gap-3">
              <CascadeStat
                testId="avg-cascade-depth"
                label="Avg Cascade Depth"
                value="4.7"
                color="var(--community-alpha)"
                icon={<GitBranchIcon />}
              />
              <CascadeStat
                testId="max-cascade-width"
                label="Max Cascade Width"
                value="128"
                color="var(--community-beta)"
                icon={<GitMergeIcon />}
              />
              <CascadeStat
                testId="critical-path"
                label="Critical Paths"
                value="23"
                color="var(--community-gamma)"
                icon={<RouteIcon />}
              />
              <CascadeStat
                testId="decay-rate"
                label="Decay Rate"
                value="0.12/step"
                color="var(--community-bridge)"
                icon={<TrendDownIcon />}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

/* Sub-components */

function TierCard({
  tier,
  count,
  description,
  color,
  icon,
  testId,
}: {
  tier: string;
  count: string;
  description: string;
  color: string;
  icon: React.ReactNode;
  testId?: string;
}) {
  return (
    <div
      data-testid={testId}
      className="flex items-center gap-3 p-3 rounded-lg border border-[var(--border)] hover:shadow-sm transition-shadow"
      style={{ borderLeftColor: color, borderLeftWidth: 3 }}
    >
      <span style={{ color }}>{icon}</span>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-semibold text-[var(--foreground)]">{tier}</div>
        <div className="text-xl font-bold text-[var(--foreground)]">{count}</div>
        <div className="text-xs text-[var(--muted-foreground)]">{description}</div>
      </div>
    </div>
  );
}

function CascadeStat({
  label,
  value,
  color,
  icon,
  testId,
}: {
  label: string;
  value: string;
  color: string;
  icon: React.ReactNode;
  testId?: string;
}) {
  return (
    <div data-testid={testId} className="p-3 rounded-lg border border-[var(--border)] flex flex-col gap-1">
      <span style={{ color }}>{icon}</span>
      <span className="text-2xl font-bold text-[var(--foreground)]">{value}</span>
      <span className="text-xs text-[var(--muted-foreground)]">{label}</span>
    </div>
  );
}

/* Inline icons */
function UsersIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2" /><circle cx="9" cy="7" r="4" /><path d="M22 21v-2a4 4 0 0 0-3-3.87" /><path d="M16 3.13a4 4 0 0 1 0 7.75" />
    </svg>
  );
}
function ZapIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" />
    </svg>
  );
}
function ActivityIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
    </svg>
  );
}
function CalendarIcon() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="4" width="18" height="18" rx="2" /><line x1="16" y1="2" x2="16" y2="6" /><line x1="8" y1="2" x2="8" y2="6" /><line x1="3" y1="10" x2="21" y2="10" />
    </svg>
  );
}
function DownloadIcon() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="7 10 12 15 17 10" /><line x1="12" y1="15" x2="12" y2="3" />
    </svg>
  );
}
function CpuIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <rect x="4" y="4" width="16" height="16" rx="2" /><rect x="9" y="9" width="6" height="6" /><line x1="9" y1="1" x2="9" y2="4" /><line x1="15" y1="1" x2="15" y2="4" /><line x1="9" y1="20" x2="9" y2="23" /><line x1="15" y1="20" x2="15" y2="23" /><line x1="20" y1="9" x2="23" y2="9" /><line x1="20" y1="14" x2="23" y2="14" /><line x1="1" y1="9" x2="4" y2="9" /><line x1="1" y1="14" x2="4" y2="14" />
    </svg>
  );
}
function BrainIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9.5 2A2.5 2.5 0 0 1 12 4.5v15a2.5 2.5 0 0 1-4.96.44 2.5 2.5 0 0 1-2.96-3.08 3 3 0 0 1-.34-5.58 2.5 2.5 0 0 1 1.32-4.24 2.5 2.5 0 0 1 1.98-3A2.5 2.5 0 0 1 9.5 2Z" /><path d="M14.5 2A2.5 2.5 0 0 0 12 4.5v15a2.5 2.5 0 0 0 4.96.44 2.5 2.5 0 0 0 2.96-3.08 3 3 0 0 0 .34-5.58 2.5 2.5 0 0 0-1.32-4.24 2.5 2.5 0 0 0-1.98-3A2.5 2.5 0 0 0 14.5 2Z" />
    </svg>
  );
}
function SparklesIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z" /><path d="M5 3v4" /><path d="M19 17v4" /><path d="M3 5h4" /><path d="M17 19h4" />
    </svg>
  );
}
function GitBranchIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <line x1="6" y1="3" x2="6" y2="15" /><circle cx="18" cy="6" r="3" /><circle cx="6" cy="18" r="3" /><path d="M18 9a9 9 0 0 1-9 9" />
    </svg>
  );
}
function GitMergeIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="18" cy="18" r="3" /><circle cx="6" cy="6" r="3" /><path d="M6 21V9a9 9 0 0 0 9 9" />
    </svg>
  );
}
function RouteIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="6" cy="19" r="3" /><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15" /><circle cx="18" cy="5" r="3" />
    </svg>
  );
}
function TrendDownIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <polyline points="23 18 13.5 8.5 8.5 13.5 1 6" /><polyline points="17 18 23 18 23 12" />
    </svg>
  );
}
