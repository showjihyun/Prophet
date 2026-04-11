/**
 * TimelinePanel — Timeline + Diffusion Wave (Zone 3 upper).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-3-timeline-diffusion-wave
 *
 * Day counter + bar chart (div-based, 24 bars with varying heights and community colors).
 * Playback controls live in ControlPanel to avoid duplication.
 */
import { useMemo } from "react";
import { useSimulationStore } from "../../store/simulationStore";
import HelpTooltip from "../shared/HelpTooltip";
import { EVENT_TYPE_META } from "../emergent/emergentEventsUtils";

const COMMUNITY_COLORS = [
  "var(--community-alpha)",
  "var(--community-beta)",
  "var(--community-gamma)",
  "var(--community-delta)",
  "var(--community-bridge)",
];

// MOCK_WAVE_DATA removed — the wave is purely derived from real
// `step.diffusion_rate` history. With no steps, the chart area is empty.

export default function TimelinePanel() {
  const currentStep = useSimulationStore((s) => s.currentStep);
  // FE-PERF-01: gate on latestStep + length, read array lazily
  const latestStep = useSimulationStore((s) => s.latestStep);
  const stepsLength = useSimulationStore((s) => s.steps.length);
  const simulation = useSimulationStore((s) => s.simulation);
  const speed = useSimulationStore((s) => s.speed);
  const emergentEvents = useSimulationStore((s) => s.emergentEvents);
  const maxSteps = simulation?.max_steps ?? 365;

  // Real-data-only: derive wave data from actual steps (cap at last 100
  // steps for perf). Empty array when there are no steps yet.
  const waveData = useMemo(() => {
    const steps = useSimulationStore.getState().steps;
    if (steps.length === 0) return [];
    const recentSteps = steps.slice(-100);
    const rates = recentSteps.map((s) => s.diffusion_rate * 100);
    const maxRate = Math.max(...rates, 1);
    return rates.map((r) => Math.round((r / maxRate) * 90));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestStep, stepsLength]);

  // Derive visible event markers. Only events whose step falls inside the
  // same 100-step window as the wave bars are shown, positioned as a
  // percentage across the wave. Multiple events at the same step share a
  // marker (first one wins for color).
  const eventMarkers = useMemo(() => {
    if (emergentEvents.length === 0 || stepsLength === 0) return [];
    const steps = useSimulationStore.getState().steps;
    const recentSteps = steps.slice(-100);
    if (recentSteps.length === 0) return [];
    const firstStep = recentSteps[0].step;
    const lastStep = recentSteps[recentSteps.length - 1].step;
    const range = Math.max(1, lastStep - firstStep);
    const seen = new Set<number>();
    const markers: Array<{ step: number; type: string; leftPct: number; label: string }> = [];
    for (const ev of emergentEvents) {
      if (ev.step < firstStep || ev.step > lastStep) continue;
      if (seen.has(ev.step)) continue;
      seen.add(ev.step);
      const leftPct = ((ev.step - firstStep) / range) * 100;
      const meta = EVENT_TYPE_META[ev.event_type];
      markers.push({
        step: ev.step,
        type: ev.event_type,
        leftPct,
        label: `${meta?.label ?? ev.event_type} · Step ${ev.step}`,
      });
    }
    return markers;
    // stepsLength is the recompute gate — the latest step arrives as
    // part of the same store update so we don't list it separately.
  }, [emergentEvents, stepsLength]);

  return (
    <div
      data-testid="timeline-panel"
      className="flex items-center gap-4 px-4 border-t border-[var(--border)] bg-[var(--card)]"
      style={{ height: "var(--timeline-height)" }}
    >
      {/* Left: Day counter */}
      <div data-testid="timeline-controls" className="flex items-center gap-2 shrink-0">
        <span className="text-xs font-medium text-[var(--foreground)] whitespace-nowrap">
          Day {currentStep} of {maxSteps}
        </span>
      </div>

      {/* Center: Diffusion Wave bars */}
      <div data-testid="diffusion-wave-chart" className="flex-1 flex flex-col min-w-0">
        <div className="text-[10px] text-[var(--muted-foreground)] font-medium mb-1 flex items-center gap-1">
          Diffusion Wave Timeline
          <HelpTooltip term="diffusionWaveTimeline" />
        </div>
        <div className="relative flex items-end gap-[3px] h-16">
          {waveData.length === 0 && (
            <div className="flex-1 flex items-center text-[10px] text-[var(--muted-foreground)] pl-1">
              No diffusion data yet — run the simulation to populate the wave.
            </div>
          )}
          {waveData.map((height, i) => {
            const colorIdx = i % COMMUNITY_COLORS.length;
            const normalizedHeight = (height / 90) * 100;
            const isCurrentStep = stepsLength > 0 && i === stepsLength - 1;
            return (
              <div
                key={i}
                className={`flex-1 rounded-t-sm transition-all duration-300 hover:opacity-80 cursor-pointer ${isCurrentStep ? "ring-1 ring-white" : ""}`}
                style={{
                  height: `${normalizedHeight}%`,
                  backgroundColor: COMMUNITY_COLORS[colorIdx],
                  opacity: isCurrentStep ? 1 : 0.8,
                }}
                title={`Day ${i + 1}: ${height} propagations`}
              />
            );
          })}

          {/* Emergent event markers overlay */}
          {eventMarkers.map((m) => (
            <div
              key={`marker-${m.step}-${m.type}`}
              data-testid={`timeline-event-marker-${m.step}`}
              aria-label={m.label}
              title={m.label}
              className="absolute top-0 bottom-0 w-[2px] bg-amber-400 pointer-events-auto cursor-help"
              style={{ left: `${m.leftPct}%` }}
            >
              <div className="absolute -top-1 -left-1 w-2 h-2 rounded-full bg-amber-400 ring-2 ring-amber-400/30" />
            </div>
          ))}
        </div>
      </div>

      {/* Right: Speed badge */}
      <span data-testid="speed-badge" className="shrink-0 text-[11px] font-medium px-2 py-1 rounded bg-[var(--secondary)] text-[var(--muted-foreground)]">
        {speed}x Speed
      </span>
    </div>
  );
}
