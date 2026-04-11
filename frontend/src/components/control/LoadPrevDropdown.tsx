/**
 * "Load Previous" simulation dropdown in the Simulation Control Bar.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 */
import type { SimulationRun } from "../../types/simulation";

interface LoadPrevDropdownProps {
  open: boolean;
  onToggle: () => void;
  search: string;
  onSearchChange: (value: string) => void;
  items: SimulationRun[];
  onSelect: (simId: string) => void;
}

export default function LoadPrevDropdown({
  open,
  onToggle,
  search,
  onSearchChange,
  items,
  onSelect,
}: LoadPrevDropdownProps) {
  return (
    <div className="relative">
      <button
        data-testid="load-prev-btn"
        onClick={onToggle}
        className="h-8 px-2.5 text-xs font-medium rounded-md border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors"
      >
        Load Previous
      </button>
      {open && (
        <div className="absolute left-0 top-9 z-50 w-72 rounded-md border border-[var(--border)] bg-[var(--card)] shadow-lg overflow-hidden">
          <div className="px-2 py-1.5 border-b border-[var(--border)]">
            <input
              type="text"
              placeholder="Search simulations..."
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full h-7 px-2 text-xs rounded border border-[var(--border)] bg-[var(--background)]"
              autoFocus
            />
          </div>
          <div className="max-h-60 overflow-y-auto">
            {items.length === 0 ? (
              <div className="px-3 py-2 text-xs text-[var(--muted-foreground)]">
                No simulations found
              </div>
            ) : (
              items.map((sim) => (
                <button
                  key={sim.simulation_id}
                  onClick={() => onSelect(sim.simulation_id)}
                  className="w-full text-left px-3 py-2 text-xs hover:bg-[var(--secondary)] transition-colors border-b border-[var(--border)] last:border-0"
                >
                  <span className="font-medium text-[var(--foreground)] block truncate">
                    {sim.name}
                  </span>
                  <span className="text-[var(--muted-foreground)]">
                    {sim.status} · Step {sim.current_step}/{sim.max_steps}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
