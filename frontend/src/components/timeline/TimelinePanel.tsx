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
        <div className="flex items-end gap-[3px] h-16">
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
        </div>
      </div>

      {/* Right: Speed badge */}
      <span data-testid="speed-badge" className="shrink-0 text-[11px] font-medium px-2 py-1 rounded bg-[var(--secondary)] text-[var(--muted-foreground)]">
        {speed}x Speed
      </span>
    </div>
  );
}
