/**
 * Simulation Control Bar — Zone 1.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 *
 * Left: Logo + status badge
 * Center: Global Insights link, Scenario dropdown, Speed buttons
 * Right: Play/Pause/Step/Reset/Replay + Settings + Avatar
 */
import { useNavigate } from "react-router-dom";
import {
  Brain,
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  Rewind,
  Settings,
  User,
} from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
import { apiClient } from '../../api/client';

const SPEEDS = [1, 2, 5, 10] as const;

export default function ControlPanel() {
  const navigate = useNavigate();
  const simulation = useSimulationStore((s) => s.simulation);
  const status = useSimulationStore((s) => s.status);
  const currentStep = useSimulationStore((s) => s.currentStep);
  const setStatus = useSimulationStore((s) => s.setStatus);
  const appendStep = useSimulationStore((s) => s.appendStep);
  const speed = useSimulationStore((s) => s.speed);
  const setSpeed = useSimulationStore((s) => s.setSpeed);

  const isRunning = status === "running";

  const handlePlay = async () => {
    try {
      if (simulation?.simulation_id) {
        if (status === 'configured' || status === 'created') {
          await apiClient.simulations.start(simulation.simulation_id);
        } else {
          await apiClient.simulations.resume(simulation.simulation_id);
        }
        setStatus('running');
      }
    } catch { /* status unchanged on failure */ }
  };

  const handlePause = async () => {
    try {
      if (simulation?.simulation_id) {
        await apiClient.simulations.pause(simulation.simulation_id);
        setStatus('paused');
      }
    } catch { /* status unchanged */ }
  };

  const handleStep = async () => {
    try {
      if (simulation?.simulation_id) {
        const result = await apiClient.simulations.step(simulation.simulation_id);
        appendStep(result);
      }
    } catch { /* ignore */ }
  };

  const handleReset = async () => {
    try {
      if (simulation?.simulation_id) {
        await apiClient.simulations.stop(simulation.simulation_id);
        setStatus('created');
      }
    } catch { /* ignore */ }
  };

  return (
    <div
      data-testid="control-panel"
      className="shrink-0 flex items-center justify-between px-4 border-b border-[var(--border)] bg-[var(--card)]"
      style={{ height: "var(--control-bar-height)" }}
    >
      {/* Left: Logo + Status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-[var(--primary)]" />
          <span className="text-base font-bold text-[var(--primary)]">
            MCASP Prophet Engine
          </span>
        </div>
        <span className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--card)]">
          <span
            className={`w-2 h-2 rounded-full ${
              isRunning
                ? "bg-green-500 animate-pulse-dot"
                : status === "paused"
                  ? "bg-yellow-500"
                  : "bg-gray-400"
            }`}
          />
          {isRunning
            ? `Running`
            : status === "paused"
              ? "Paused"
              : status === "completed"
                ? "Completed"
                : "Ready"}
          <span className="text-[var(--muted-foreground)]">
            {" "}Day {currentStep}/365
          </span>
        </span>
      </div>

      {/* Center: Navigation + Scenario + Speed */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => navigate("/metrics")}
          className="h-8 px-3 text-xs font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity"
        >
          Global Insights
        </button>

        <select
          className="h-8 px-2 text-xs border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-1 focus:ring-gray-300"
          defaultValue="default"
        >
          <option value="default">Default Scenario</option>
          <option value="viral">Viral Campaign</option>
          <option value="polarized">Polarized Market</option>
        </select>

        <div className="flex items-center rounded-md border border-[var(--border)]">
          {SPEEDS.map((s) => (
            <button
              key={s}
              onClick={() => setSpeed(s)}
              className={`h-7 px-2.5 text-xs font-medium transition-colors ${
                speed === s
                  ? "bg-[var(--primary)] text-[var(--primary-foreground)]"
                  : "text-[var(--muted-foreground)] hover:bg-[var(--secondary)]"
              } ${s === 1 ? "rounded-l-md" : ""} ${s === 10 ? "rounded-r-md" : ""}`}
            >
              {s}x
            </button>
          ))}
        </div>
      </div>

      {/* Right: Playback controls + Settings + Avatar */}
      <div className="flex items-center gap-1">
        {isRunning ? (
          <ControlButton
            icon={<Pause className="w-4 h-4" />}
            label="Pause"
            onClick={handlePause}
          />
        ) : (
          <ControlButton
            icon={<Play className="w-4 h-4" />}
            label="Play"
            onClick={handlePlay}
          />
        )}
        <ControlButton
          icon={<SkipForward className="w-4 h-4" />}
          label="Step"
          onClick={handleStep}
        />
        <ControlButton
          icon={<RotateCcw className="w-4 h-4" />}
          label="Reset"
          onClick={handleReset}
        />
        <ControlButton
          icon={<Rewind className="w-4 h-4" />}
          label="Replay"
          onClick={() => {
            /* replay */
          }}
        />

        <div className="w-px h-6 bg-[var(--border)] mx-1" />

        <ControlButton
          icon={<Settings className="w-4 h-4" />}
          label="Settings"
          onClick={() => {
            /* open settings */
          }}
        />

        <button
          className="w-8 h-8 rounded-full bg-[var(--secondary)] flex items-center justify-center hover:bg-gray-200 transition-colors ml-1"
          title="User profile"
        >
          <User className="w-4 h-4 text-[var(--muted-foreground)]" />
        </button>
      </div>
    </div>
  );
}

function ControlButton({
  icon,
  label,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      title={label}
      className="w-8 h-8 flex items-center justify-center rounded-md text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors"
    >
      {icon}
    </button>
  );
}
