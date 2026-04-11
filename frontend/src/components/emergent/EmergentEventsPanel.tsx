/**
 * EmergentEventsPanel — Step 4 "Detect" feature surface.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#emergent-events-panel
 *
 * Before this panel, emergent events (viral cascades, polarization, echo
 * chambers, collapse, slow adoption) were only announced via 5-second
 * auto-dismiss toasts — users had no way to review them after the fact.
 * This panel is the persistent record.
 *
 * Pure helpers live in ``./emergentEventsUtils`` to keep this file
 * component-only (Vite react-refresh rule).
 */
import { memo, useMemo, useState } from "react";
import { AlertTriangle, Sparkles } from "lucide-react";
import type { EmergentEvent } from "@/types/simulation";
import { useSimulationStore } from "../../store/simulationStore";
import {
  EVENT_TYPE_META,
  EVENT_TYPE_ORDER,
  UNKNOWN_EVENT_META,
  filterAndSortEvents,
  severityToWidth,
  type EventType,
  type FilterValue,
} from "./emergentEventsUtils";

// --------------------------------------------------------------------------- //
// Component                                                                   //
// --------------------------------------------------------------------------- //

function EventRow({ event }: { event: EmergentEvent }) {
  const meta = EVENT_TYPE_META[event.event_type] ?? UNKNOWN_EVENT_META;
  const Icon = meta.icon;

  return (
    <li
      data-testid={`emergent-event-row-${event.step}-${event.event_type}`}
      className="flex items-start gap-3 px-3 py-2 border-b border-[var(--border)] hover:bg-[var(--secondary)]/50 transition-colors"
    >
      <Icon className={`w-4 h-4 shrink-0 mt-0.5 ${meta.color}`} aria-hidden="true" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-medium text-[var(--foreground)]">
            {meta.label}
          </span>
          <span className="text-[10px] text-[var(--muted-foreground)] shrink-0">
            Step {event.step}
          </span>
        </div>
        <p className="text-[11px] text-[var(--muted-foreground)] truncate">
          {event.description || meta.description}
        </p>
        <div className="mt-1 flex items-center gap-2">
          <div
            className="h-1 flex-1 bg-[var(--secondary)] rounded-full overflow-hidden"
            role="progressbar"
            aria-valuenow={Math.round(event.severity * 100)}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-label={`Severity ${Math.round(event.severity * 100)}%`}
          >
            <div
              className={`h-full ${meta.color.replace("text-", "bg-")}`}
              style={{ width: severityToWidth(event.severity) }}
            />
          </div>
          <span className="text-[10px] text-[var(--muted-foreground)] tabular-nums shrink-0 w-8 text-right">
            {Math.round(event.severity * 100)}%
          </span>
        </div>
      </div>
    </li>
  );
}

function FilterBar({
  active,
  counts,
  onChange,
}: {
  active: FilterValue;
  counts: Record<FilterValue, number>;
  onChange: (f: FilterValue) => void;
}) {
  const options: FilterValue[] = ["all", ...EVENT_TYPE_ORDER];
  return (
    <div className="flex items-center gap-1 px-3 py-2 border-b border-[var(--border)] overflow-x-auto">
      {options.map((opt) => {
        const isActive = opt === active;
        const label = opt === "all" ? "All" : EVENT_TYPE_META[opt as EventType].label;
        return (
          <button
            key={opt}
            type="button"
            onClick={() => onChange(opt)}
            data-testid={`emergent-filter-${opt}`}
            aria-pressed={isActive}
            className={`shrink-0 px-2 py-1 rounded text-[10px] font-medium transition-colors ${
              isActive
                ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                : "bg-[var(--secondary)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)]/70"
            }`}
          >
            {label}
            <span className="ml-1 opacity-70">({counts[opt] ?? 0})</span>
          </button>
        );
      })}
    </div>
  );
}

function EmergentEventsPanel() {
  const emergentEvents = useSimulationStore((s) => s.emergentEvents);
  const [filter, setFilter] = useState<FilterValue>("all");

  const counts = useMemo<Record<FilterValue, number>>(() => {
    const base: Record<FilterValue, number> = {
      all: emergentEvents.length,
      viral_cascade: 0,
      polarization: 0,
      echo_chamber: 0,
      collapse: 0,
      slow_adoption: 0,
    };
    for (const ev of emergentEvents) {
      base[ev.event_type] = (base[ev.event_type] ?? 0) + 1;
    }
    return base;
  }, [emergentEvents]);

  const visibleEvents = useMemo(
    () => filterAndSortEvents(emergentEvents, filter),
    [emergentEvents, filter],
  );

  return (
    <section
      data-testid="emergent-events-panel"
      aria-label="Emergent events detected during simulation"
      className="flex flex-col h-full bg-[var(--card)] border-l border-[var(--border)]"
    >
      <header className="flex items-center gap-2 px-3 py-2 border-b border-[var(--border)]">
        <AlertTriangle className="w-4 h-4 text-amber-400" />
        <h3 className="text-sm font-semibold text-[var(--foreground)]">
          Emergent Events
        </h3>
        <span className="ml-auto text-[10px] text-[var(--muted-foreground)] tabular-nums">
          {emergentEvents.length} detected
        </span>
      </header>

      <FilterBar active={filter} counts={counts} onChange={setFilter} />

      {visibleEvents.length === 0 ? (
        <div
          data-testid="emergent-events-empty"
          className="flex-1 flex flex-col items-center justify-center gap-2 p-4 text-center"
        >
          <Sparkles className="w-8 h-8 text-[var(--muted-foreground)]/40" />
          <p className="text-xs text-[var(--muted-foreground)]">
            {emergentEvents.length === 0
              ? "No emergent events yet. Run the simulation to detect cascades, polarization, echo chambers, and collapse."
              : `No events of type "${filter}" in the current window.`}
          </p>
        </div>
      ) : (
        <ul
          data-testid="emergent-events-list"
          className="flex-1 overflow-y-auto"
        >
          {visibleEvents.map((ev, idx) => (
            <EventRow key={`${ev.step}-${ev.event_type}-${idx}`} event={ev} />
          ))}
        </ul>
      )}
    </section>
  );
}

export default memo(EmergentEventsPanel);
