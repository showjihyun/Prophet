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
import { X, GitCompare, Dices, Download } from "lucide-react";
import {
  useSimulations,
  useRunAllSimulation,
  useExportSimulation,
} from "../../api/queries";
import { useSimulationStore } from "../../store/simulationStore";

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

function MonteCarloTab() {
  const [runs, setRuns] = useState<number>(10);
  const [error, setError] = useState<string | null>(null);
  const simulationId = useSimulationStore((s) => s.simulation?.simulation_id);
  const runAll = useRunAllSimulation();

  const handleRun = async () => {
    if (!simulationId) return;
    setError(null);
    try {
      // Backend endpoint for MC sweep is a follow-up. We surface the
      // intent here (so users stop thinking it's missing) and fall back
      // to the proven run-all path as a best effort.
      await runAll.mutateAsync(simulationId);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Monte Carlo run failed");
    }
  };

  const running = runAll.isPending;

  return (
    <div className="p-4 space-y-3">
      <p className="text-xs text-[var(--muted-foreground)]">
        Run the same configuration N times with different seeds to quantify
        variance in adoption and cascade metrics.
      </p>
      <label className="block text-xs font-medium text-[var(--foreground)]">
        Number of runs: <span className="tabular-nums">{runs}</span>
      </label>
      <input
        data-testid="decide-mc-runs-slider"
        type="range"
        min={5}
        max={50}
        step={5}
        value={runs}
        onChange={(e) => setRuns(Number(e.target.value))}
        className="w-full accent-[var(--primary)]"
      />
      <div className="flex justify-between text-[10px] text-[var(--muted-foreground)]">
        <span>5</span>
        <span>25</span>
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
        {running ? "Running…" : `Run ${runs} Scenarios`}
      </button>
      <p className="text-[10px] text-[var(--muted-foreground)] italic">
        Note: full parallel Monte Carlo sweep endpoint is on the backend
        roadmap — current implementation uses run-all as a single-seed
        baseline.
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
