/**
 * "Compare" dropdown in the Simulation Control Bar. Lists other simulations
 * that the current one can be compared against.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 */
import { useState } from "react";
import { GitCompare } from "lucide-react";
import { useNavigate } from "react-router-dom";
import type { SimulationRun } from "../../types/simulation";

interface CompareDropdownProps {
  currentSimId: string;
  prevSimulations: SimulationRun[];
  onLoadList: () => void;
}

export default function CompareDropdown({
  currentSimId,
  prevSimulations,
  onLoadList,
}: CompareDropdownProps) {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);

  const handleToggle = () => {
    setOpen((o) => !o);
    if (prevSimulations.length === 0) {
      onLoadList();
    }
  };

  const candidates = prevSimulations
    .filter((s) => s.simulation_id !== currentSimId)
    .slice(0, 10);

  return (
    <div className="relative">
      <button
        onClick={handleToggle}
        className="h-8 px-2.5 text-xs font-medium rounded-md border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors flex items-center gap-1"
      >
        <GitCompare className="w-3.5 h-3.5" />
        Compare
      </button>
      {open && (
        <div className="absolute left-0 top-9 z-50 w-64 rounded-md border border-[var(--border)] bg-[var(--card)] shadow-lg overflow-hidden">
          {candidates.length === 0 ? (
            <div className="px-3 py-2 text-xs text-[var(--muted-foreground)]">
              No other simulations to compare
            </div>
          ) : (
            candidates.map((s) => (
              <button
                key={s.simulation_id}
                onClick={() => {
                  navigate(`/compare/${s.simulation_id}`);
                  setOpen(false);
                }}
                className="w-full text-left px-3 py-2 text-xs hover:bg-[var(--secondary)] transition-colors border-b border-[var(--border)] last:border-0"
              >
                <span className="font-medium text-[var(--foreground)] block truncate">
                  {s.name}
                </span>
                <span className="text-[var(--muted-foreground)]">{s.status}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
