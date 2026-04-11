/**
 * MetricsPanel — Right sidebar (Zone 2 Right).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-2-right-metrics-panel
 *
 * Real-time metrics: Active Agents, Sentiment Distribution,
 * Polarization Index, Cascade Stats, Top Influencers.
 */
import { useNavigate } from "react-router-dom";
import { useSimulationStore } from "../../store/simulationStore";
import { useAgents } from "../../api/queries";
import HelpTooltip from "../shared/HelpTooltip";

const COMMUNITY_COLORS: Record<string, string> = {
  Alpha: "var(--community-alpha)",
  Beta: "var(--community-beta)",
  Gamma: "var(--community-gamma)",
  Delta: "var(--community-delta)",
  Bridge: "var(--community-bridge)",
};

// MOCK_TOP_INFLUENCERS / MOCK_METRICS removed — the panel now renders only
// real values from the simulation store + agent query. Empty/zero states
// are explicit ("—" placeholders) so the user can tell when data hasn't
// arrived yet. Real-data-only.

const COMMUNITY_ID_TO_NAME: Record<string, string> = {
  A: "Alpha", B: "Beta", C: "Gamma", D: "Delta", E: "Bridge",
};

export default function MetricsPanel() {
  const navigate = useNavigate();
  const latestStep = useSimulationStore((s) => s.latestStep);
  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id) ?? null;

  // TanStack Query — fetched once per simulation, deduplicated across
  // any other consumer asking for the same `agents` list. Throttling-by-10
  // is no longer necessary because the cache already prevents duplicate
  // fetches; if a fresh value is needed, the query is refetched lazily.
  const agentsQuery = useAgents(simulationId, { limit: 4 });
  const topInfluencers = agentsQuery.data
    ? [...agentsQuery.data.items]
        .sort((a, b) => b.influence_score - a.influence_score)
        .slice(0, 4)
        .map((a) => ({
          id: a.agent_id,
          community: COMMUNITY_ID_TO_NAME[a.community_id] ?? a.community_id,
          score: Math.round(a.influence_score * 100 * 10) / 10,
        }))
    : [];

  // Real-data-only: every metric is null when no step has arrived yet.
  // The render path uses these nulls to show "—" placeholders instead of
  // fake numbers.
  const hasStep = latestStep !== null;
  const activeAgents = hasStep ? latestStep.total_adoption : null;
  const totalAgents =
    hasStep && latestStep.adoption_rate > 0
      ? Math.round(latestStep.total_adoption / latestStep.adoption_rate)
      : null;
  const activePercent =
    activeAgents !== null && totalAgents !== null && totalAgents > 0
      ? ((activeAgents / totalAgents) * 100).toFixed(1)
      : null;

  // Sentiment: derive from mean_sentiment [-1, 1] range
  const sentimentPositive = hasStep
    ? Math.round(Math.max(0, latestStep.mean_sentiment) * 100)
    : null;
  const sentimentNegative = hasStep
    ? Math.round(Math.max(0, -latestStep.mean_sentiment) * 100)
    : null;
  const sentimentNeutral =
    sentimentPositive !== null && sentimentNegative !== null
      ? 100 - sentimentPositive - sentimentNegative
      : null;

  const polarization = hasStep ? latestStep.sentiment_variance : null;

  // Action distribution for cascade stats
  const cascadeDepth = hasStep ? latestStep.llm_calls_this_step : null;
  const cascadeWidth = hasStep
    ? Object.values(latestStep.action_distribution).reduce((a, b) => a + b, 0)
    : null;

  const dash = "—";

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
        <span data-testid="live-badge" className="inline-flex items-center gap-1 text-[10px] font-semibold text-[var(--live-badge)] uppercase">
          <span className="w-1.5 h-1.5 rounded-full bg-[var(--live-badge)] animate-pulse-dot" />
          Live
        </span>
      </div>

      <div className="flex flex-col" style={{ gap: "var(--card-gap)" }}>
        {/* Active Agents */}
        <MetricCard testId="active-agents-metric">
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1 flex items-center gap-1.5">
            <span>Active Agents</span>
            <HelpTooltip term="activeAgents" align="right" />
          </div>
          <div className="flex items-baseline gap-1">
            <span className="text-2xl font-bold text-[var(--foreground)]">
              {activeAgents !== null ? activeAgents.toLocaleString() : dash}
            </span>
            <span className="text-xs text-[var(--muted-foreground)]">
              / {totalAgents !== null ? totalAgents.toLocaleString() : dash}
            </span>
          </div>
          <div className="mt-2 h-2 rounded-full bg-[var(--secondary)] overflow-hidden">
            <div
              className="h-full rounded-full bg-[var(--community-alpha)] transition-all duration-500"
              style={{ width: `${activePercent ?? 0}%` }}
            />
          </div>
        </MetricCard>

        {/* Sentiment Distribution */}
        <MetricCard testId="sentiment-distribution">
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-2 flex items-center gap-1.5">
            <span>Sentiment Distribution</span>
            <HelpTooltip term="sentimentDistribution" align="right" />
          </div>
          <SentimentBar label="Positive" value={sentimentPositive ?? 0} color="var(--sentiment-positive)" missing={sentimentPositive === null} />
          <SentimentBar label="Neutral" value={sentimentNeutral ?? 0} color="var(--sentiment-neutral)" missing={sentimentNeutral === null} />
          <SentimentBar label="Negative" value={sentimentNegative ?? 0} color="var(--sentiment-negative)" missing={sentimentNegative === null} />
        </MetricCard>

        {/* Polarization Index */}
        <MetricCard testId="polarization-index">
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-1 flex items-center gap-1.5">
            <span>Polarization Index</span>
            <HelpTooltip term="polarization" align="right" />
          </div>
          <span className="text-lg font-bold text-[var(--foreground)]">
            {polarization !== null ? polarization.toFixed(2) : dash}
          </span>
          <div className="relative mt-2 h-2 rounded-full overflow-hidden">
            <div
              className="absolute inset-0 rounded-full"
              style={{
                background:
                  "linear-gradient(to right, #22c55e, #eab308, #ef4444)",
              }}
            />
            {polarization !== null && (
              <div
                className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-[var(--card)] border-2 border-[var(--foreground)] shadow"
                style={{ left: `${Math.min(polarization * 100, 100)}%` }}
              />
            )}
          </div>
        </MetricCard>

        {/* Cascade Stats */}
        <div className="grid grid-cols-2 gap-2">
          <MetricCard testId="cascade-depth">
            <div className="text-[11px] text-[var(--muted-foreground)] font-medium flex items-center gap-1.5">
              <span>Depth</span>
              <HelpTooltip term="cascadeDepth" />
            </div>
            <span className="text-lg font-bold text-[var(--foreground)]">
              {cascadeDepth !== null ? cascadeDepth : dash}
            </span>
          </MetricCard>
          <MetricCard testId="cascade-width">
            <div className="text-[11px] text-[var(--muted-foreground)] font-medium flex items-center gap-1.5">
              <span>Width</span>
              <HelpTooltip term="cascadeWidth" align="right" />
            </div>
            <span className="text-lg font-bold text-[var(--foreground)]">
              {cascadeWidth !== null ? cascadeWidth.toLocaleString() : dash}
            </span>
          </MetricCard>
        </div>

        {/* Top Influencers */}
        <MetricCard testId="top-influencers">
          <div className="text-[11px] text-[var(--muted-foreground)] font-medium mb-2 flex items-center gap-1.5">
            <span>Top Influencers</span>
            <HelpTooltip term="influencer" align="right" />
          </div>
          <div className="flex flex-col gap-1.5">
            {topInfluencers.length === 0 && (
              <span className="text-[11px] text-[var(--muted-foreground)]">
                No agents available yet.
              </span>
            )}
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

function MetricCard({ children, testId }: { children: React.ReactNode; testId?: string }) {
  return (
    <div data-testid={testId} className="rounded-lg border border-[var(--border)] bg-[var(--card)] p-3">
      {children}
    </div>
  );
}

function SentimentBar({
  label,
  value,
  color,
  missing = false,
}: {
  label: string;
  value: number;
  color: string;
  missing?: boolean;
}) {
  return (
    <div className="flex items-center gap-2 mb-1.5 last:mb-0">
      <span className="text-[11px] text-[var(--muted-foreground)] w-14">
        {label}
      </span>
      <div className="flex-1 h-2 rounded-full bg-[var(--secondary)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-500"
          style={{ width: `${missing ? 0 : value}%`, backgroundColor: color }}
        />
      </div>
      <span className="text-[11px] font-medium text-[var(--foreground)] w-8 text-right">
        {missing ? "—" : `${value}%`}
      </span>
    </div>
  );
}
