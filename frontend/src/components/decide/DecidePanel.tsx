/**
 * DecidePanel — Step 6 "Decide" unified entry point.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#decide-panel
 *
 * Surfaces three previously-hidden features behind one discoverable
 * modal:
 *   1. Compare — pick another simulation and navigate to /compare
 *   2. Monte Carlo — run N parallel variations (UI only; backend
 *      endpoint is a follow-up)
 *   3. Export — download JSON or CSV
 *
 * Before this panel, the compare entry point was buried in the sidebar
 * and the export endpoint had no UI trigger at all.
 */
import { memo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { X, GitCompare, Dices, Download, Flame, TrendingUp } from "lucide-react";
import {
  useSimulations,
  useRunMonteCarlo,
  useExportSimulation,
} from "../../api/queries";
import { useSimulationStore } from "../../store/simulationStore";
import type { MonteCarloResponse } from "../../types/api";

type Tab = "compare" | "monte_carlo" | "export";

interface DecidePanelProps {
  onClose: () => void;
}

// --------------------------------------------------------------------------- //
// Compare tab                                                                 //
// --------------------------------------------------------------------------- //

function CompareTab({ onClose }: { onClose: () => void }) {
  const navigate = useNavigate();
  const currentSimId = useSimulationStore((s) => s.simulation?.simulation_id);
  const [otherId, setOtherId] = useState<string>("");
  const sims = useSimulations();

  const candidates = (sims.data?.items ?? []).filter(
    (s) => s.simulation_id !== currentSimId,
  );

  const canCompare = !!currentSimId && !!otherId;

  const handleCompare = () => {
    if (!canCompare || !currentSimId) return;
    navigate(`/simulation/${currentSimId}/compare/${otherId}`);
    onClose();
  };

  return (
    <div className="p-4 space-y-3">
      <p className="text-xs text-[var(--muted-foreground)]">
        Pick another simulation to compare side-by-side. Metrics shown:
        adoption rate, mean sentiment, propagation count, viral cascades.
      </p>
      <label className="block text-xs font-medium text-[var(--foreground)]">
        Other simulation
      </label>
      <select
        data-testid="decide-compare-select"
        value={otherId}
        onChange={(e) => setOtherId(e.target.value)}
        className="w-full h-9 px-3 rounded-md border border-[var(--border)] bg-[var(--background)] text-sm text-[var(--foreground)]"
      >
        <option value="">Select a simulation…</option>
        {candidates.map((s) => (
          <option key={s.simulation_id} value={s.simulation_id}>
            {s.name ?? s.simulation_id.slice(0, 8)} — {s.status}
          </option>
        ))}
      </select>
      {sims.isLoading && (
        <p className="text-[10px] text-[var(--muted-foreground)]">
          Loading simulation list…
        </p>
      )}
      {candidates.length === 0 && !sims.isLoading && (
        <p className="text-[10px] text-amber-500">
          No other simulations found. Create one first to compare.
        </p>
      )}
      <button
        data-testid="decide-compare-submit"
        type="button"
        onClick={handleCompare}
        disabled={!canCompare}
        className="w-full h-9 rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
      >
        Compare →
      </button>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Monte Carlo tab                                                             //
// --------------------------------------------------------------------------- //

/**
 * Monte Carlo tab.
 * @spec docs/spec/29_MONTE_CARLO_SPEC.md#33-decidepanel-mc-tab-ux-mc-fe-03
 *
 * Calls POST /simulations/{id}/monte-carlo and renders the aggregate
 * (viral probability + reach percentiles) inline. The earlier `run-all`
 * fallback was a lie — it ran a single seed and called it MC.
 */
function MonteCarloTab() {
  const [runs, setRuns] = useState<number>(10);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<MonteCarloResponse | null>(null);
  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id);
  const monteCarlo = useRunMonteCarlo();

  const handleRun = async () => {
    if (!simulationId) return;
    setError(null);
    setResult(null);
    try {
      const data = await monteCarlo.mutateAsync({
        simId: simulationId,
        n_runs: runs,
      });
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Monte Carlo run failed");
    }
  };

  const running = monteCarlo.isPending;

  return (
    <div className="p-4 space-y-3">
      <p className="text-xs text-[var(--muted-foreground)]">
        Run the same configuration N times with different seeds to quantify
        variance in adoption and cascade metrics.
      </p>
      <label className="block text-xs font-medium text-[var(--foreground)]">
        Number of runs: <span className="tabular-nums">{runs}</span>
      </label>
      {/* SPEC 29 §3.3 — slider range is [2, 50] (was 5–50; single seed is not MC) */}
      <input
        data-testid="decide-mc-runs-slider"
        type="range"
        min={2}
        max={50}
        step={1}
        value={runs}
        onChange={(e) => setRuns(Number(e.target.value))}
        className="w-full accent-[var(--primary)]"
      />
      <div className="flex justify-between text-[10px] text-[var(--muted-foreground)]">
        <span>2</span>
        <span>26</span>
        <span>50</span>
      </div>
      {error && (
        <p data-testid="decide-mc-error" className="text-[11px] text-red-500">
          {error}
        </p>
      )}
      <button
        data-testid="decide-mc-run"
        type="button"
        onClick={handleRun}
        disabled={!simulationId || running}
        className="w-full h-9 rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity"
      >
        {running ? `Running ${runs} sweeps…` : `Run ${runs} Scenarios`}
      </button>
      {running && (
        <p className="text-[10px] text-[var(--muted-foreground)] italic">
          Each run is a full N-step replay with a fresh seed. Expect
          ~30–90s wall time depending on tier-3 cache hits.
        </p>
      )}

      {result && !running && (
        <div
          data-testid="decide-mc-result"
          className="mt-3 p-3 rounded-md bg-[var(--secondary)] border border-[var(--border)] space-y-2"
        >
          <div className="flex items-center gap-2">
            <Flame className="w-4 h-4 text-amber-400" aria-hidden="true" />
            <span className="text-xs text-[var(--muted-foreground)]">
              Viral probability
            </span>
            <span
              data-testid="decide-mc-viral-prob"
              className="ml-auto text-base font-semibold tabular-nums text-[var(--foreground)]"
            >
              {(result.viral_probability * 100).toFixed(0)}%
            </span>
          </div>
          <div className="flex items-center gap-2">
            <TrendingUp className="w-4 h-4 text-[var(--primary)]" aria-hidden="true" />
            <span className="text-xs text-[var(--muted-foreground)]">
              Expected reach
            </span>
            <span
              data-testid="decide-mc-expected"
              className="ml-auto text-base font-semibold tabular-nums text-[var(--foreground)]"
            >
              {result.expected_reach.toFixed(0)}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center pt-1 border-t border-[var(--border)]">
            <PercentileCell label="P5" value={result.p5_reach} />
            <PercentileCell label="P50" value={result.p50_reach} />
            <PercentileCell label="P95" value={result.p95_reach} />
          </div>
          <p className="text-[10px] text-[var(--muted-foreground)] italic">
            Aggregated over {result.n_runs} runs · seeds offset from base
          </p>
        </div>
      )}
    </div>
  );
}

function PercentileCell({ label, value }: { label: string; value: number }) {
  return (
    <div>
      <p className="text-[10px] text-[var(--muted-foreground)]">{label}</p>
      <p className="text-sm font-mono tabular-nums text-[var(--foreground)]">
        {value.toFixed(0)}
      </p>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Export tab                                                                  //
// --------------------------------------------------------------------------- //

function ExportTab({ onClose }: { onClose: () => void }) {
  const [format, setFormat] = useState<"json" | "csv">("json");
  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id);
  const triggerExport = useExportSimulation();

  const handleExport = () => {
    if (!simulationId) return;
    triggerExport(simulationId, format);
    onClose();
  };

  return (
    <div className="p-4 space-y-3">
      <p className="text-xs text-[var(--muted-foreground)]">
        Download all step metrics, community summaries, and emergent
        events for external analysis.
      </p>
      <label className="block text-xs font-medium text-[var(--foreground)]">
        Format
      </label>
      <div className="flex gap-2">
        {(["json", "csv"] as const).map((f) => (
          <button
            key={f}
            type="button"
            data-testid={`decide-export-format-${f}`}
            onClick={() => setFormat(f)}
            aria-pressed={format === f}
            className={`flex-1 h-9 rounded-md text-sm font-medium transition-colors ${
              format === f
                ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                : "bg-[var(--secondary)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/70"
            }`}
          >
            {f.toUpperCase()}
          </button>
        ))}
      </div>
      <button
        data-testid="decide-export-submit"
        type="button"
        onClick={handleExport}
        disabled={!simulationId}
        className="w-full h-9 rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-90 transition-opacity flex items-center justify-center gap-2"
      >
        <Download className="w-4 h-4" />
        Download {format.toUpperCase()}
      </button>
    </div>
  );
}

// --------------------------------------------------------------------------- //
// Shell                                                                       //
// --------------------------------------------------------------------------- //

function DecidePanel({ onClose }: DecidePanelProps) {
  const [tab, setTab] = useState<Tab>("compare");

  const tabs: Array<{ id: Tab; label: string; icon: typeof GitCompare }> = [
    { id: "compare", label: "Compare", icon: GitCompare },
    { id: "monte_carlo", label: "Monte Carlo", icon: Dices },
    { id: "export", label: "Export", icon: Download },
  ];

  return (
    <div
      data-testid="decide-panel"
      role="dialog"
      aria-modal="true"
      aria-labelledby="decide-panel-title"
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-[var(--card)] border border-[var(--border)] rounded-lg shadow-2xl w-full max-w-md max-h-[80vh] flex flex-col"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)]">
          <h2
            id="decide-panel-title"
            className="text-sm font-semibold text-[var(--foreground)]"
          >
            Decide · What&apos;s next?
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close decide panel"
            className="p-1 rounded hover:bg-[var(--secondary)] text-[var(--muted-foreground)]"
          >
            <X className="w-4 h-4" />
          </button>
        </header>

        <nav className="flex border-b border-[var(--border)]">
          {tabs.map((t) => {
            const Icon = t.icon;
            const isActive = tab === t.id;
            return (
              <button
                key={t.id}
                type="button"
                data-testid={`decide-tab-${t.id}`}
                onClick={() => setTab(t.id)}
                aria-pressed={isActive}
                className={`flex-1 h-10 flex items-center justify-center gap-2 text-xs font-medium transition-colors ${
                  isActive
                    ? "text-[var(--primary)] border-b-2 border-[var(--primary)]"
                    : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]"
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                {t.label}
              </button>
            );
          })}
        </nav>

        <div className="flex-1 overflow-y-auto">
          {tab === "compare" && <CompareTab onClose={onClose} />}
          {tab === "monte_carlo" && <MonteCarloTab />}
          {tab === "export" && <ExportTab onClose={onClose} />}
        </div>
      </div>
    </div>
  );
}

export default memo(DecidePanel);
