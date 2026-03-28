/**
 * TimelinePanel — Timeline + Diffusion Wave (Zone 3 upper).
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-3-timeline-diffusion-wave
 *
 * Left: Play/Step buttons + "Day 47 of 365"
 * Right: Bar chart (div-based, 24 bars with varying heights and community colors)
 */
import { useMemo } from "react";
import { Play, SkipForward } from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";

const COMMUNITY_COLORS = [
  "var(--community-alpha)",
  "var(--community-beta)",
  "var(--community-gamma)",
  "var(--community-delta)",
  "var(--community-bridge)",
];

// Mock diffusion wave data: 24 bars with varying heights
const MOCK_WAVE_DATA = [
  12, 18, 25, 35, 42, 55, 48, 62, 70, 65, 78, 85,
  80, 72, 68, 75, 82, 90, 88, 78, 65, 55, 42, 30,
];

export default function TimelinePanel() {
  const currentStep = useSimulationStore((s) => s.currentStep);
  const steps = useSimulationStore((s) => s.steps);
  const simulation = useSimulationStore((s) => s.simulation);
  const maxSteps = simulation?.max_steps ?? 365;

  // Derive wave data from actual steps or use mock
  const waveData = useMemo(() => {
    if (steps.length === 0) return MOCK_WAVE_DATA;
    // Use diffusion_rate from each step as bar height (scale to 0-100)
    const rates = steps.map((s) => s.diffusion_rate * 100);
    const maxRate = Math.max(...rates, 1);
    return rates.map((r) => Math.round((r / maxRate) * 90));
  }, [steps]);

  return (
    <div
      data-testid="timeline-panel"
      className="flex items-center gap-4 px-4 border-t border-[var(--border)] bg-white"
      style={{ height: "var(--timeline-height)" }}
    >
      {/* Left: Controls + Day counter */}
      <div className="flex items-center gap-2 shrink-0">
        <button className="w-8 h-8 flex items-center justify-center rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity">
          <Play className="w-3.5 h-3.5" />
        </button>
        <button className="w-8 h-8 flex items-center justify-center rounded-md border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors">
          <SkipForward className="w-3.5 h-3.5" />
        </button>
        <span className="text-xs font-medium text-[var(--foreground)] whitespace-nowrap ml-1">
          Day {currentStep || 47} of {maxSteps}
        </span>
      </div>

      {/* Center: Diffusion Wave bars */}
      <div className="flex-1 flex flex-col min-w-0">
        <div className="text-[10px] text-[var(--muted-foreground)] font-medium mb-1">
          Diffusion Wave Timeline
        </div>
        <div className="flex items-end gap-[3px] h-16">
          {waveData.map((height, i) => {
            const colorIdx = i % COMMUNITY_COLORS.length;
            const normalizedHeight = (height / 90) * 100;
            const isCurrentStep = steps.length > 0 && i === steps.length - 1;
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
      <span className="shrink-0 text-[11px] font-medium px-2 py-1 rounded bg-[var(--secondary)] text-[var(--muted-foreground)]">
        5x Speed
      </span>
    </div>
  );
}
