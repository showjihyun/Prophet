/**
 * LLM Dashboard — real-time LLM usage statistics.
 * @spec docs/spec/07_FRONTEND_SPEC.md#llm-dashboard
 */
import { useSimulationStore } from "../../store/simulationStore";
import { useLLMStats, useLLMImpact } from "../../api/queries";

interface LLMStats {
  total_calls: number;
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate: number;
  avg_latency_ms: number;
  provider_breakdown: Record<string, number>;
  tier_breakdown: { tier1: number; tier2: number; tier3: number };
  estimated_cost_usd: number;
}

interface LLMImpact {
  reasoning_quality: number;
  cost_efficiency: string;
  simulation_velocity: string;
}

const EMPTY_STATS: LLMStats = {
  total_calls: 0,
  cache_hits: 0,
  cache_misses: 0,
  cache_hit_rate: 0,
  avg_latency_ms: 0,
  provider_breakdown: {},
  tier_breakdown: { tier1: 0, tier2: 0, tier3: 0 },
  estimated_cost_usd: 0,
};

function StatTile({
  label,
  value,
  sub,
}: {
  label: string;
  value: string;
  sub?: string;
}) {
  return (
    <div
      className="flex flex-col gap-0.5 px-4 py-3 rounded-lg border"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}
    >
      <span
        className="text-[10px] uppercase tracking-wider"
        style={{ color: "var(--muted-foreground)" }}
      >
        {label}
      </span>
      <span
        className="text-xl font-bold leading-tight"
        style={{ color: "var(--foreground)" }}
      >
        {value}
      </span>
      {sub && (
        <span className="text-[11px]" style={{ color: "var(--muted-foreground)" }}>
          {sub}
        </span>
      )}
    </div>
  );
}

export default function LLMDashboard() {
  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id) ?? null;
  // FE-PERF-01: subscribe only to derived primitives
  const stepsLength = useSimulationStore((s) => s.steps.length);
  const lastLLMCalls = useSimulationStore((s) => s.latestStep?.llm_calls_this_step ?? 0);

  // TanStack Query — `step` is part of the cache key so a new simulation
  // step naturally invalidates the cache. No imperative refetch loop, no
  // local state, no mount effect. Two components calling this hook get
  // automatic request deduplication.
  const statsQuery = useLLMStats(simulationId, stepsLength);
  const impactQuery = useLLMImpact(simulationId, stepsLength);

  const stats = (statsQuery.data as LLMStats | undefined) ?? EMPTY_STATS;
  const impact = (impactQuery.data as LLMImpact | null | undefined) ?? null;
  const loading = statsQuery.isLoading || impactQuery.isLoading;

  if (!simulationId) {
    return (
      <div
        data-testid="llm-dashboard"
        className="w-full flex items-center justify-center rounded-lg border py-6"
        style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}
      >
        <span className="text-sm" style={{ color: "var(--muted-foreground)" }}>
          No active simulation
        </span>
      </div>
    );
  }

  // Derived values
  const cacheRate = stats.cache_hit_rate
    ? `${(stats.cache_hit_rate * 100).toFixed(1)}%`
    : "—";
  const avgLatency = stats.avg_latency_ms
    ? `${Math.round(stats.avg_latency_ms)} ms`
    : "—";
  const costEst = `$${stats.estimated_cost_usd.toFixed(4)}`;

  const { tier1, tier2, tier3 } = stats.tier_breakdown ?? { tier1: 0, tier2: 0, tier3: 0 };
  const totalTiers = tier1 + tier2 + tier3 || 1;
  const tier1Pct = Math.round((tier1 / totalTiers) * 100);
  const tier2Pct = Math.round((tier2 / totalTiers) * 100);
  const tier3Pct = 100 - tier1Pct - tier2Pct;

  // Provider breakdown bar
  const providers = Object.entries(stats.provider_breakdown ?? {});
  const totalProviderCalls = providers.reduce((s, [, v]) => s + v, 0) || 1;

  const PROVIDER_COLORS: Record<string, string> = {
    ollama: "var(--community-alpha)",
    anthropic: "var(--community-gamma)",
    openai: "var(--community-beta)",
    cache: "var(--community-delta)",
  };

  return (
    <div
      data-testid="llm-dashboard"
      className="w-full rounded-lg border overflow-hidden"
      style={{ borderColor: "var(--border)", backgroundColor: "var(--background)" }}
    >
      {/* Header */}
      <div
        className="flex items-center justify-between px-4 py-2 border-b"
        style={{ borderColor: "var(--border)" }}
      >
        <span className="text-xs font-semibold" style={{ color: "var(--foreground)" }}>
          LLM Usage
        </span>
        {loading && (
          <span className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>
            Refreshing…
          </span>
        )}
        {impact && (
          <span className="text-[10px]" style={{ color: "var(--muted-foreground)" }}>
            {impact.cost_efficiency} cost · {impact.simulation_velocity} speed
          </span>
        )}
      </div>

      {/* Stat grid — 6 tiles */}
      <div className="grid grid-cols-6 gap-2 p-3">
        <StatTile
          label="Total Calls"
          value={stats.total_calls.toLocaleString()}
          sub={`+${lastLLMCalls} last step`}
        />
        <StatTile
          label="Cache Hit Rate"
          value={cacheRate}
          sub={`${stats.cache_hits} hits`}
        />
        <StatTile
          label="Avg Latency"
          value={avgLatency}
          sub="per call"
        />
        <StatTile
          label="Est. Cost"
          value={costEst}
          sub="cumulative"
        />

        {/* Tier breakdown tile */}
        <div
          className="flex flex-col gap-1 px-4 py-3 rounded-lg border"
          style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}
        >
          <span
            className="text-[10px] uppercase tracking-wider"
            style={{ color: "var(--muted-foreground)" }}
          >
            Tier Mix
          </span>
          <div className="flex h-2 w-full rounded-full overflow-hidden mt-1">
            <div style={{ width: `${tier1Pct}%`, backgroundColor: "var(--community-alpha)" }} />
            <div style={{ width: `${tier2Pct}%`, backgroundColor: "var(--community-gamma)" }} />
            <div style={{ width: `${tier3Pct}%`, backgroundColor: "var(--community-delta)" }} />
          </div>
          <div className="flex gap-2 text-[10px]" style={{ color: "var(--muted-foreground)" }}>
            <span>T1 {tier1Pct}%</span>
            <span>T2 {tier2Pct}%</span>
            <span>T3 {tier3Pct}%</span>
          </div>
        </div>

        {/* Provider breakdown tile */}
        <div
          className="flex flex-col gap-1 px-4 py-3 rounded-lg border"
          style={{ borderColor: "var(--border)", backgroundColor: "var(--card)" }}
        >
          <span
            className="text-[10px] uppercase tracking-wider"
            style={{ color: "var(--muted-foreground)" }}
          >
            Providers
          </span>
          {providers.length === 0 ? (
            <span className="text-xs" style={{ color: "var(--muted-foreground)" }}>—</span>
          ) : (
            <>
              <div className="flex h-2 w-full rounded-full overflow-hidden mt-1">
                {providers.map(([name, count]) => (
                  <div
                    key={name}
                    style={{
                      width: `${Math.round((count / totalProviderCalls) * 100)}%`,
                      backgroundColor: PROVIDER_COLORS[name] ?? "var(--muted-foreground)",
                    }}
                  />
                ))}
              </div>
              <div className="flex flex-wrap gap-x-2 text-[10px]" style={{ color: "var(--muted-foreground)" }}>
                {providers.map(([name, count]) => (
                  <span key={name}>
                    {name} {Math.round((count / totalProviderCalls) * 100)}%
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
