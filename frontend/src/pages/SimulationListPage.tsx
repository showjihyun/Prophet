/**
 * SimulationListPage — Entry screen for the Simulation menu.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#simulation-list
 *
 * Shows a list of all simulations. Clicking a row navigates to
 * `/simulation/:simulationId` which mounts the full SimulationPage detail
 * view. This decouples "pick a simulation" from "run a simulation" so the
 * sidebar's Simulation menu has a neutral landing page instead of an
 * empty graph with no context.
 */
import { useNavigate } from "react-router-dom";
import { Play, Plus, Clock, Loader2 } from "lucide-react";
import { useSimulations } from "../api/queries";
import type { SimulationRun } from "../types/simulation";
import { SIM_STATUS, type SimulationStatus } from "@/config/constants";

const STATUS_STYLES: Record<string, string> = {
  [SIM_STATUS.RUNNING]: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  [SIM_STATUS.PAUSED]: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  [SIM_STATUS.COMPLETED]: "bg-sky-500/15 text-sky-400 border-sky-500/30",
  [SIM_STATUS.FAILED]: "bg-rose-500/15 text-rose-400 border-rose-500/30",
  [SIM_STATUS.CONFIGURED]: "bg-slate-500/15 text-slate-400 border-slate-500/30",
  [SIM_STATUS.CREATED]: "bg-slate-500/15 text-slate-400 border-slate-500/30",
};

function formatTimestamp(iso?: string | null): string {
  if (!iso) return "—";
  try {
    const d = new Date(iso);
    return d.toLocaleString();
  } catch {
    return iso;
  }
}

export default function SimulationListPage() {
  const navigate = useNavigate();
  const simulationsQuery = useSimulations();
  const items: SimulationRun[] = simulationsQuery.data?.items ?? [];
  const loading = simulationsQuery.isLoading;
  const error = simulationsQuery.error
    ? simulationsQuery.error instanceof Error
      ? simulationsQuery.error.message
      : String(simulationsQuery.error)
    : null;

  return (
    <div
      data-testid="simulation-list-page"
      className="flex flex-col h-full p-6 gap-4 bg-[var(--background)]"
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-[var(--foreground)]">
            Simulations
          </h1>
          <p className="text-sm text-[var(--muted-foreground)] mt-1">
            Pick a simulation to open its live workspace, or create a new one.
          </p>
        </div>
        <button
          onClick={() => navigate("/setup")}
          className="h-10 px-4 text-sm font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 flex items-center gap-2 transition-opacity"
        >
          <Plus className="w-4 h-4" />
          New Simulation
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 min-h-0 overflow-y-auto">
        {loading && (
          <div
            data-testid="simulation-list-loading"
            className="h-full flex items-center justify-center text-[var(--muted-foreground)]"
          >
            <Loader2 className="w-5 h-5 animate-spin mr-2" />
            Loading simulations…
          </div>
        )}

        {!loading && error && (
          <div
            data-testid="simulation-list-error"
            className="h-full flex items-center justify-center text-sm text-rose-400"
          >
            Failed to load simulations: {error}
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <div
            data-testid="simulation-list-empty"
            className="h-full flex flex-col items-center justify-center gap-3 text-center"
          >
            <Play className="w-12 h-12 text-[var(--muted-foreground)]" />
            <h2 className="text-lg font-semibold text-[var(--foreground)]">
              No simulations yet
            </h2>
            <p className="text-sm text-[var(--muted-foreground)] max-w-md">
              Create your first simulation to see it here. Each run captures a
              full campaign scenario with agents, networks, and step history.
            </p>
            <button
              onClick={() => navigate("/setup")}
              className="mt-2 h-9 px-4 text-sm font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Create Simulation
            </button>
          </div>
        )}

        {!loading && !error && items.length > 0 && (
          <ul className="flex flex-col gap-2">
            {items.map((sim) => {
              const statusKey = sim.status as SimulationStatus;
              const statusStyle =
                STATUS_STYLES[statusKey] ??
                "bg-slate-500/15 text-slate-400 border-slate-500/30";
              return (
                <li key={sim.simulation_id}>
                  <button
                    data-testid={`simulation-row-${sim.simulation_id}`}
                    onClick={() => navigate(`/simulation/${sim.simulation_id}`)}
                    className="w-full text-left rounded-lg border border-[var(--border)] bg-[var(--card)] hover:border-[var(--primary)] hover:shadow-md transition-all px-4 py-3 flex items-center gap-4"
                  >
                    {/* Name + id */}
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-semibold text-[var(--foreground)] truncate">
                        {sim.name || "(unnamed)"}
                      </div>
                      <div className="text-[11px] font-mono text-[var(--muted-foreground)] truncate">
                        {sim.simulation_id}
                      </div>
                    </div>

                    {/* Step progress */}
                    <div className="hidden md:flex flex-col items-end shrink-0">
                      <span className="text-[10px] uppercase tracking-wide text-[var(--muted-foreground)]">
                        Step
                      </span>
                      <span className="text-sm font-semibold text-[var(--foreground)] tabular-nums">
                        {sim.current_step ?? 0} / {sim.max_steps ?? 0}
                      </span>
                    </div>

                    {/* Created at */}
                    <div className="hidden lg:flex items-center gap-1.5 text-[11px] text-[var(--muted-foreground)] shrink-0 w-44">
                      <Clock className="w-3 h-3" />
                      {formatTimestamp(sim.created_at)}
                    </div>

                    {/* Status badge */}
                    <span
                      className={`shrink-0 text-[10px] uppercase tracking-wide font-semibold px-2 py-1 rounded-full border ${statusStyle}`}
                    >
                      {statusKey}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}
