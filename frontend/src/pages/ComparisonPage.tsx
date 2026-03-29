/**
 * ComparisonPage — Side-by-side simulation scenario comparison.
 * @spec docs/spec/06_API_SPEC.md#get-simulationssimulation_idcompareother_simulation_id
 * @spec docs/spec/07_FRONTEND_SPEC.md#scenario-comparison
 */
import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Trophy, TrendingUp, Users, MessageSquare, BarChart3 } from "lucide-react";
import { apiClient } from "../api/client";
import { useSimulationStore } from "../store/simulationStore";

interface ComparisonData {
  simulation_a: string;
  simulation_b: string;
  comparison: {
    adoption_rate_a?: number;
    adoption_rate_b?: number;
    mean_sentiment_a?: number;
    mean_sentiment_b?: number;
    total_propagation_a?: number;
    total_propagation_b?: number;
    viral_cascades_a?: number;
    viral_cascades_b?: number;
    winner?: string;
  };
}

export default function ComparisonPage() {
  const { otherId } = useParams<{ otherId: string }>();
  const navigate = useNavigate();
  const simulation = useSimulationStore((s) => s.simulation);
  const [data, setData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const simulationId = simulation?.simulation_id ?? null;

  useEffect(() => {
    if (!simulationId || !otherId) {
      setLoading(false);
      setError(simulationId ? null : "No active simulation. Go back and select one.");
      return;
    }
    setLoading(true);
    apiClient.simulations
      .compare(simulationId, otherId)
      .then((res) => setData(res as ComparisonData))
      .catch((err) => setError(err instanceof Error ? err.message : "Failed to load comparison"))
      .finally(() => setLoading(false));
  }, [simulationId, otherId]);

  const simIdA = simulation?.simulation_id ?? "—";
  const simIdB = otherId ?? "—";
  const c = data?.comparison ?? {};

  return (
    <div className="min-h-screen bg-[var(--background)] text-[var(--foreground)]">
      {/* Header */}
      <header className="flex items-center gap-4 px-6 py-4 border-b border-[var(--border)]">
        <button
          onClick={() => navigate(-1)}
          className="p-2 rounded-md hover:bg-[var(--secondary)] transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
        </button>
        <div className="flex items-center gap-2">
          <BarChart3 className="w-5 h-5 text-[var(--community-delta)]" />
          <h1 className="text-lg font-semibold">Scenario Comparison</h1>
        </div>
      </header>

      <main className="max-w-4xl mx-auto p-6">
        {loading && (
          <div className="flex items-center justify-center py-20">
            <span className="text-sm text-[var(--muted-foreground)]">Loading comparison...</span>
          </div>
        )}

        {error && (
          <div className="flex items-center justify-center py-20">
            <span className="text-sm text-[var(--destructive)]">{error}</span>
          </div>
        )}

        {data && !loading && (
          <div className="flex flex-col gap-6">
            {/* Scenario labels */}
            <div className="grid grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-[var(--community-alpha)]/10 border border-[var(--community-alpha)]/30 text-center">
                <span className="text-xs text-[var(--muted-foreground)]">Scenario A</span>
                <p className="text-sm font-mono font-medium text-[var(--foreground)] mt-1 truncate">
                  {simIdA.slice(0, 12)}...
                </p>
              </div>
              <div className="flex items-center justify-center">
                <span className="text-lg font-bold text-[var(--muted-foreground)]">VS</span>
              </div>
              <div className="p-4 rounded-lg bg-[var(--community-beta)]/10 border border-[var(--community-beta)]/30 text-center">
                <span className="text-xs text-[var(--muted-foreground)]">Scenario B</span>
                <p className="text-sm font-mono font-medium text-[var(--foreground)] mt-1 truncate">
                  {simIdB.slice(0, 12)}...
                </p>
              </div>
            </div>

            {/* Winner */}
            {c.winner && (
              <div className="flex items-center justify-center gap-2 py-3 rounded-lg bg-[var(--sentiment-warning)]/10 border border-[var(--sentiment-warning)]/30">
                <Trophy className="w-5 h-5 text-[var(--sentiment-warning)]" />
                <span className="text-sm font-semibold text-[var(--foreground)]">
                  Winner: Scenario {c.winner === simIdA ? "A" : "B"}
                </span>
              </div>
            )}

            {/* Metrics comparison */}
            <div className="flex flex-col gap-3">
              <ComparisonRow
                icon={<TrendingUp className="w-4 h-4" />}
                label="Adoption Rate"
                valueA={c.adoption_rate_a}
                valueB={c.adoption_rate_b}
                format={(v) => `${(v * 100).toFixed(1)}%`}
              />
              <ComparisonRow
                icon={<MessageSquare className="w-4 h-4" />}
                label="Mean Sentiment"
                valueA={c.mean_sentiment_a}
                valueB={c.mean_sentiment_b}
                format={(v) => v.toFixed(3)}
              />
              <ComparisonRow
                icon={<Users className="w-4 h-4" />}
                label="Total Propagation"
                valueA={c.total_propagation_a}
                valueB={c.total_propagation_b}
                format={(v) => v.toLocaleString()}
              />
              <ComparisonRow
                icon={<BarChart3 className="w-4 h-4" />}
                label="Viral Cascades"
                valueA={c.viral_cascades_a}
                valueB={c.viral_cascades_b}
                format={(v) => String(v)}
              />
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

function ComparisonRow({
  icon,
  label,
  valueA,
  valueB,
  format,
}: {
  icon: React.ReactNode;
  label: string;
  valueA?: number;
  valueB?: number;
  format: (v: number) => string;
}) {
  const a = valueA ?? 0;
  const b = valueB ?? 0;
  const aWins = a > b;
  const bWins = b > a;

  return (
    <div className="grid grid-cols-3 items-center gap-4 p-4 rounded-lg bg-[var(--card)] border border-[var(--border)]">
      <div className={`text-right text-base font-mono font-semibold ${aWins ? "text-[var(--sentiment-positive)]" : "text-[var(--foreground)]"}`}>
        {format(a)}
      </div>
      <div className="flex items-center justify-center gap-2 text-[var(--muted-foreground)]">
        {icon}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <div className={`text-left text-base font-mono font-semibold ${bWins ? "text-[var(--sentiment-positive)]" : "text-[var(--foreground)]"}`}>
        {format(b)}
      </div>
    </div>
  );
}
