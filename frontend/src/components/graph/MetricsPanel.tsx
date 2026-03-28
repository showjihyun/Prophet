/**
 * MetricsPanel — Right sidebar (Zone 2 Right).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-2-right-metrics-panel
 *
 * Real-time metrics: Active Agents, Sentiment Distribution,
 * Polarization Index, Cascade Stats, Top Influencers.
 */
import { useNavigate } from "react-router-dom";
import { useSimulationStore } from "../../store/simulationStore";

const COMMUNITY_COLORS: Record<string, string> = {
  Alpha: "var(--community-alpha)",
  Beta: "var(--community-beta)",
  Gamma: "var(--community-gamma)",
  Delta: "var(--community-delta)",
  Bridge: "var(--community-bridge)",
};

const MOCK_TOP_INFLUENCERS = [
  { id: "A-0042", community: "Alpha", score: 98.2 },
  { id: "BR-0012", community: "Bridge", score: 96.5 },
  { id: "B-0091", community: "Beta", score: 94.7 },
  { id: "D-0067", community: "Delta", score: 92.1 },
];

// Mock defaults for when no live data is available
const MOCK_METRICS = {
  activeAgents: 5847,
  totalAgents: 6500,
  sentimentPositive: 62,
  sentimentNeutral: 25,
  sentimentNegative: 13,
  polarization: 0.72,
  cascadeDepth: 12,
  cascadeWidth: 847,
};

export default function MetricsPanel() {
  const navigate = useNavigate();
  const steps = useSimulationStore((s) => s.steps);
  const latestStep = steps.length > 0 ? steps[steps.length - 1] : null;

  // Derive metrics from latest step or fall back to mock
  const activeAgents = latestStep?.total_adoption ?? MOCK_METRICS.activeAgents;
  const totalAgents = MOCK_METRICS.totalAgents;
  const activePercent = ((activeAgents / totalAgents) * 100).toFixed(1);

  // Sentiment: derive from mean_sentiment [-1, 1] range
  const sentimentPositive = latestStep
    ? Math.round(Math.max(0, latestStep.mean_sentiment) * 100)
    : MOCK_METRICS.sentimentPositive;
  const sentimentNegative = latestStep
    ? Math.round(Math.max(0, -latestStep.mean_sentiment) * 100)
    : MOCK_METRICS.sentimentNegative;
  const sentimentNeutral = latestStep
    ? 100 - sentimentPositive - sentimentNegative
    : MOCK_METRICS.sentimentNeutral;

  const polarization = latestStep?.sentiment_variance ?? MOCK_METRICS.polarization;

  // Action distribution for cascade stats
  const cascadeDepth = latestStep?.llm_calls_this_step ?? MOCK_METRICS.cascadeDepth;
  const cascadeWidth = latestStep
    ? Object.values(latestStep.action_distribution).reduce((a, b) => a + b, 0)
    : MOCK_METRICS.cascadeWidth;

  const topInfluencers = MOCK_TOP_INFLUENCERS;

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
              {activeAgents.toLocaleString()}
            </span>
            <span className="text-xs text-[var(--muted-foreground)]">
              / {totalAgents.toLocaleString()}
            </span>
          </div>
          <div className="mt-2 h-2 rounded-full bg-[var(--secondary)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--community-alpha)] transition-all duration-500"
              style={{ width: `${activePercent}%` }}
            />
          </div>
        </MetricCard>

        {/* Sentiment Distribution */}
        <MetricCard>
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-2">
            Sentiment Distribution
          </div>
          <SentimentBar label="Positive" value={sentimentPositive} color="var(--sentiment-positive)" />
          <SentimentBar label="Neutral" value={sentimentNeutral} color="var(--sentiment-neutral)" />
          <SentimentBar label="Negative" value={sentimentNegative} color="var(--sentiment-negative)" />
        </MetricCard>

        {/* Polarization Index */}
        <MetricCard>
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1">
            Polarization Index
          </div>
          <span className="text-lg font-bold text-[var(--foreground)]">
            {polarization.toFixed(2)}
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
              style={{ left: `${Math.min(polarization * 100, 100)}%` }}
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
              {cascadeDepth}
            </span>
          </MetricCard>
          <MetricCard>
            <div className="text-[11px] text-[var(--muted-foreground)] font-medium">
              Width
            </div>
            <span className="text-lg font-bold text-[var(--foreground)]">
              {cascadeWidth.toLocaleString()}
            </span>
          </MetricCard>
        </div>

        {/* Top Influencers */}
        <MetricCard>
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-2">
            Top Influencers
          </div>
          <div className="flex flex-col gap-1.5">
            {topInfluencers.map((inf, i) => (
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
