/**
 * MetricsPanel — Right sidebar (Zone 2 Right).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-2-right-metrics-panel
 *
 * Real-time metrics: Active Agents, Sentiment Distribution,
 * Polarization Index, Cascade Stats, Top Influencers.
 */
import { useNavigate } from "react-router-dom";

const COMMUNITY_COLORS: Record<string, string> = {
  Alpha: "var(--community-alpha)",
  Beta: "var(--community-beta)",
  Gamma: "var(--community-gamma)",
  Delta: "var(--community-delta)",
  Bridge: "var(--community-bridge)",
};

const TOP_INFLUENCERS = [
  { id: "A-0042", community: "Alpha", score: 98.2 },
  { id: "BR-0012", community: "Bridge", score: 96.5 },
  { id: "B-0091", community: "Beta", score: 94.7 },
  { id: "D-0067", community: "Delta", score: 92.1 },
];

export default function MetricsPanel() {
  const navigate = useNavigate();

  return (
    <div
      data-testid="metrics-panel"
      className="shrink-0 flex flex-col border-l border-[var(--border)] bg-[var(--card)] overflow-y-auto"
      style={{
        width: "var(--metrics-panel-width)",
        padding: "var(--panel-padding)",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <span className="text-sm font-semibold text-[var(--foreground)]">
          Real-Time Metrics
        </span>
        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-[var(--live-badge)] uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--live-badge)] animate-pulse-dot" />
          Live
        </span>
      </div>

      <div className="flex flex-col" style={{ gap: "var(--card-gap)" }}>
        {/* Active Agents */}
        <MetricCard>
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1">
            Active Agents
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold text-[var(--foreground)]">
              5,847
            </span>
            <span className="text-xs text-[var(--muted-foreground)]">
              / 6,500
            </span>
          </div>
          <div className="mt-2 h-2 rounded-full bg-[var(--secondary)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--community-alpha)] transition-all duration-500"
              style={{ width: "89.9%" }}
            />
          </div>
        </MetricCard>

        {/* Sentiment Distribution */}
        <MetricCard>
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-2">
            Sentiment Distribution
          </div>
          <SentimentBar label="Positive" value={62} color="var(--sentiment-positive)" />
          <SentimentBar label="Neutral" value={25} color="var(--sentiment-neutral)" />
          <SentimentBar label="Negative" value={13} color="var(--sentiment-negative)" />
        </MetricCard>

        {/* Polarization Index */}
        <MetricCard>
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1">
            Polarization Index
          </div>
          <span className="text-lg font-bold text-[var(--foreground)]">
            0.72
          </span>
          <div className="relative mt-2 h-2 rounded-full overflow-hidden">
            <div
              className="absolute inset-0 rounded-full"
              style={{
                background:
                  "linear-gradient(to right, #22c55e, #eab308, #ef4444)",
              }}
            />
            <div
              className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white border-2 border-[var(--foreground)] shadow"
              style={{ left: "72%" }}
            />
          </div>
        </MetricCard>

        {/* Cascade Stats */}
        <div className="grid grid-cols-2 gap-2">
          <MetricCard>
            <div className="text-[11px] text-[var(--muted-foreground)] font-medium">
              Depth
            </div>
            <span className="text-lg font-bold text-[var(--foreground)]">
              12
            </span>
          </MetricCard>
          <MetricCard>
            <div className="text-[11px] text-[var(--muted-foreground)] font-medium">
              Width
            </div>
            <span className="text-lg font-bold text-[var(--foreground)]">
              847
            </span>
          </MetricCard>
        </div>

        {/* Top Influencers */}
        <MetricCard>
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-2">
            Top Influencers
          </div>
          <div className="flex flex-col gap-1.5">
            {TOP_INFLUENCERS.map((inf, i) => (
              <button
                key={inf.id}
                onClick={() => navigate(`/agents/${inf.id}`)}
                className="flex items-center gap-2 text-left hover:bg-[var(--secondary)] rounded px-1 py-0.5 transition-colors"
              >
                <span className="text-[11px] font-semibold text-[var(--muted-foreground)] w-4">
                  {i + 1}
                </span>
                <span
                  className="w-2 h-2 rounded-full shrink-0"
                  style={{
                    backgroundColor:
                      COMMUNITY_COLORS[inf.community] ?? "#94a3b8",
                  }}
                />
                <span className="text-xs font-medium text-[var(--foreground)] flex-1">
                  {inf.id}
                </span>
                <span className="text-[11px] text-[var(--muted-foreground)]">
                  {inf.score}
                </span>
              </button>
            ))}
          </div>
        </MetricCard>
      </div>
    </div>
  );
}

function MetricCard({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-[var(--border)] bg-white p-3">
      {children}
    </div>
  );
}

function SentimentBar({
  label,
  value,
  color,
}: {
  label: string;
  value: number;
  color: string;
}) {
  return (
    <div className="flex items-center gap-2 mb-1.5 last:mb-0">
      <span className="text-[11px] text-[var(--muted-foreground)] w-14">
        {label}
      </span>
      <div className="flex-1 h-2 rounded-full bg-[var(--secondary)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${value}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-[11px] font-medium text-[var(--foreground)] w-8 text-right">
        {value}%
      </span>
    </div>
  );
}
