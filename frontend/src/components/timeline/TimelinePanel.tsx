/**
 * TimelinePanel — Timeline + Diffusion Wave (Zone 3 upper).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-3-timeline-diffusion-wave
 *
 * Compact sparkline of the cascade trajectory over the last 100 steps.
 * Previously a div-based bar chart that cycled through community colors
 * — which incorrectly implied a per-community breakdown when each bar
 * is actually one step. The replacement uses a single primary-color
 * area chart (recharts) for clean trajectory reading, with emergent
 * event markers overlaid as vertical pins so you can correlate the
 * shape with what the detector is firing.
 *
 * Playback controls live in ControlPanel to avoid duplication.
 */
import { useMemo } from "react";
import { Area, AreaChart, ResponsiveContainer, YAxis } from "recharts";
import { useSimulationStore } from "../../store/simulationStore";
import HelpTooltip from "../shared/HelpTooltip";
import { EVENT_TYPE_META } from "../emergent/emergentEventsUtils";
import { DEFAULT_MAX_STEPS } from "@/config/constants";

/** Window of recent steps plotted on the sparkline. */
const WAVE_WINDOW = 100;

/**
 * Compact sparkline + event markers for the diffusion cascade
 * trajectory. Source of truth is `steps[].diffusion_rate` — every
 * other per-step metric is already rendered elsewhere (MetricsPanel
 * right sidebar, CommunityPanel left sidebar), so this panel stays
 * focused on the *time-series shape* that no other panel can show.
 */
export default function TimelinePanel() {
  const currentStep = useSimulationStore((s) => s.currentStep);
  // FE-PERF-01: gate on latestStep + length, read array lazily
  const latestStep = useSimulationStore((s) => s.latestStep);
  const stepsLength = useSimulationStore((s) => s.steps.length);
  const simulation = useSimulationStore((s) => s.simulation);
  const speed = useSimulationStore((s) => s.speed);
  const emergentEvents = useSimulationStore((s) => s.emergentEvents);
  // SPEC 26 §4.5.2 (v0.3.0) — when Analytics pins a focused step, the
  // counter on the left of this panel shows "Step N (focused)" instead
  // of the live "Step {currentStep} of {maxSteps}".
  const focusedStep = useSimulationStore((s) => s.focusedStep);
  const maxSteps = simulation?.max_steps ?? DEFAULT_MAX_STEPS;

  // Real-data-only: derive wave data from actual steps (cap at
  // WAVE_WINDOW). Each data point carries the absolute `step` number
  // so the event marker overlay can position itself using the same
  // x-axis the chart is drawing.
  const waveData = useMemo(() => {
    const steps = useSimulationStore.getState().steps;
    if (steps.length === 0) return [];
    const recentSteps = steps.slice(-WAVE_WINDOW);
    return recentSteps.map((s) => ({
      step: s.step,
      rate: s.diffusion_rate,
    }));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [latestStep, stepsLength]);

  // First + last step numbers bound the rendered window. Used by the
  // event marker overlay to position each pin as a percentage across
  // the sparkline's width.
  const firstStep = waveData[0]?.step ?? 0;
  const lastStep = waveData[waveData.length - 1]?.step ?? 0;

  // Derive visible event markers. Only events whose step falls inside
  // the same window as the wave are shown. Multiple events at the
  // same step collapse to one marker (first wins) — the aria-label
  // carries the type so screen readers still get the detail.
  const eventMarkers = useMemo(() => {
    if (emergentEvents.length === 0 || waveData.length === 0) return [];
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
  }, [emergentEvents, waveData.length, firstStep, lastStep]);

  return (
    <div
      data-testid="timeline-panel"
      className="flex items-center gap-4 px-4 border-t border-[var(--border)] bg-[var(--card)]"
      style={{ height: "var(--timeline-height)" }}
    >
      {/* Left: Step counter. "Step" is the engine's unit — one tick
          of the simulation loop. The previous UI said "Day" as a
          marketer-friendly metaphor, but the engine doesn't model
          real time so the label was misleading. */}
      <div data-testid="timeline-controls" className="flex items-center gap-2 shrink-0">
        <span className="text-xs font-medium text-[var(--foreground)] whitespace-nowrap">
          {focusedStep !== null
            ? `Step ${focusedStep} (focused)`
            : `Step ${currentStep} of ${maxSteps}`}
        </span>
      </div>

      {/* Center: Diffusion Wave sparkline */}
      <div data-testid="diffusion-wave-chart" className="flex-1 flex flex-col min-w-0">
        <div className="text-[10px] text-[var(--muted-foreground)] font-medium mb-1 flex items-center gap-1">
          Diffusion Wave Timeline
          <HelpTooltip term="diffusionWaveTimeline" />
        </div>
        <div className="relative h-10">
          {waveData.length === 0 ? (
            <div className="absolute inset-0 flex items-center text-[10px] text-[var(--muted-foreground)] pl-1">
              No diffusion data yet — run the simulation to populate the wave.
            </div>
          ) : (
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={waveData}
                margin={{ top: 2, right: 0, bottom: 0, left: 0 }}
              >
                <defs>
                  <linearGradient id="diffusion-wave-fill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--primary)" stopOpacity={0.55} />
                    <stop offset="100%" stopColor="var(--primary)" stopOpacity={0.05} />
                  </linearGradient>
                </defs>
                {/* Hidden Y axis — we only need it so the Area scales
                    consistently without drawing ticks. Auto-domain so
                    a single step doesn't flatten to zero. */}
                <YAxis hide domain={[0, "dataMax"]} />
                <Area
                  type="monotone"
                  dataKey="rate"
                  stroke="var(--primary)"
                  strokeWidth={1.5}
                  fill="url(#diffusion-wave-fill)"
                  isAnimationActive={false}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}

          {/* Emergent event markers overlay — positioned on top of
              the sparkline using the same percentage geometry the
              chart already spans. Amber pin reads clearly against
              the muted primary-color sparkline underneath. */}
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
