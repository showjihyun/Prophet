/**
 * Simulation Control Bar — Zone 1.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 *
 * Left: Logo + status badge
 * Center: Global Insights link, Scenario dropdown, Speed buttons
 * Right: Play/Pause/Step/Reset/Replay + Settings + Avatar
 *
 * This component is intentionally a thin orchestrator. The heavy logic lives
 * in dedicated hooks so this file stays focused on layout and wiring:
 *   - useAutoStepLoop       — auto-step interval while status === RUNNING
 *   - usePlaybackControls   — play/pause/step/reset/runAll + keyboard shortcuts
 *   - useProjectScenarioSync — project/scenario loading + New/Clone handlers
 *   - usePrevSimulations    — Load Previous / Compare dropdown state
 */
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Brain,
  Play,
  Pause,
  SkipForward,
  ChevronsRight,
  RotateCcw,
  Rewind,
  Settings,
  User,
  AlertTriangle,
  Cpu,
  Plus,
  Copy,
  Zap,
} from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
import { SIM_STATUS } from "@/config/constants";
import ThemeToggle from "../shared/ThemeToggle";
import InjectEventModal from "../shared/InjectEventModal";
import ReplayModal from "../shared/ReplayModal";
import EngineControlPanel from "./EngineControlPanel";
import ControlButton from "./ControlButton";
import LoadPrevDropdown from "./LoadPrevDropdown";
import CompareDropdown from "./CompareDropdown";
import { useAutoStepLoop } from "./hooks/useAutoStepLoop";
import { usePlaybackControls } from "./hooks/usePlaybackControls";
import { useProjectScenarioSync } from "./hooks/useProjectScenarioSync";
import { usePrevSimulations } from "./hooks/usePrevSimulations";

const SPEEDS = [1, 2, 5, 10] as const;

export default function ControlPanel() {
  const navigate = useNavigate();

  // Render-subscribed store state
  const simulation = useSimulationStore((s) => s.simulation);
  const status = useSimulationStore((s) => s.status);
  const currentStep = useSimulationStore((s) => s.currentStep);
  const speed = useSimulationStore((s) => s.speed);
  const currentProjectId = useSimulationStore((s) => s.currentProjectId);
  const propagationAnimEnabled = useSimulationStore((s) => s.propagationAnimationsEnabled);
  const projects = useSimulationStore((s) => s.projects);
  const scenarios = useSimulationStore((s) => s.scenarios);

  // Stable action references from Zustand (no re-render subscription needed)
  const setSpeed = useSimulationStore((s) => s.setSpeed);
  const togglePropagationAnimations = useSimulationStore((s) => s.togglePropagationAnimations);

  // Feature hooks
  const {
    isRunning,
    runAllLoading,
    runAllLoadingRef,
    handlePlay,
    handlePause,
    handleStep,
    handleReset,
    handleRunAll,
  } = usePlaybackControls();

  useAutoStepLoop(runAllLoading, runAllLoadingRef);

  const {
    creating,
    activeScenarioId,
    handleProjectChange,
    handleScenarioChange,
    handleNewScenario,
    handleNewSimulation,
    handleClone,
  } = useProjectScenarioSync();

  const {
    prevSimulations,
    prevSimOpen,
    prevSimSearch,
    setPrevSimSearch,
    filteredPrevSimulations,
    ensureLoaded,
    handleOpenPrevSimulations,
    handleLoadPrevSimulation,
  } = usePrevSimulations();

  const [injectOpen, setInjectOpen] = useState(false);
  const [replayOpen, setReplayOpen] = useState(false);
  const [engineOpen, setEngineOpen] = useState(false);

  return (
    <div
      data-testid="control-panel"
      className="shrink-0 relative flex items-center justify-between px-4 border-b border-[var(--border)] bg-[var(--card)] overflow-x-auto"
      style={{ minHeight: "var(--control-bar-height)" }}
    >
      {/* Left: Logo + Status */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2">
          <Brain className="w-5 h-5 text-[var(--primary)]" aria-hidden="true" />
          <span className="text-base font-bold text-[var(--primary)]">
            MCASP Prophet Engine
          </span>
        </div>
        {!simulation && (
          <button
            onClick={handleNewSimulation}
            disabled={creating}
            className="h-8 px-3 text-xs font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity flex items-center gap-1.5 disabled:opacity-50"
          >
            <Plus className="w-3.5 h-3.5" aria-hidden="true" />
            {creating ? "Creating\u2026" : "New Simulation"}
          </button>
        )}
        <span
          data-testid="status-badge"
          className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--card)]"
        >
          <span
            className={`w-2 h-2 rounded-full ${
              isRunning
                ? "bg-[var(--sentiment-positive)] animate-pulse-dot"
                : status === SIM_STATUS.PAUSED
                  ? "bg-[var(--sentiment-warning)]"
                  : "bg-[var(--muted-foreground)]"
            }`}
          />
          {isRunning
            ? "Running"
            : status === SIM_STATUS.PAUSED
              ? "Paused"
              : status === SIM_STATUS.COMPLETED
                ? "Completed"
                : "Ready"}
          <span className="text-[var(--muted-foreground)]"> Day {currentStep}/365</span>
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

        {/* Project selector */}
        <select
          data-testid="project-select"
          aria-label="Select project"
          className="h-8 px-2 text-xs border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-1 focus:ring-gray-300"
          value={currentProjectId ?? ""}
          onChange={(e) => handleProjectChange(e.target.value)}
        >
          <option value="">-- Project --</option>
          {projects.map((p) => (
            <option key={p.project_id} value={p.project_id}>
              {p.name}
            </option>
          ))}
        </select>

        {/* Scenario selector. Controlled via `activeScenarioId` so that direct
            `/simulation/:id` navigation reflects the right scenario once the
            list is loaded (derived inside useProjectScenarioSync). */}
        <div className="flex items-center gap-1">
          <select
            data-testid="scenario-select"
            aria-label="Select scenario"
            className="h-8 px-2 text-xs border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-1 focus:ring-gray-300"
            value={activeScenarioId}
            onChange={(e) => handleScenarioChange(e.target.value)}
          >
            <option value="">-- Scenario --</option>
            {scenarios.map((s) => (
              <option key={s.scenario_id} value={s.scenario_id}>
                {s.name}
              </option>
            ))}
          </select>
          <button
            onClick={handleNewScenario}
            title="New scenario"
            aria-label="New scenario"
            disabled={!currentProjectId}
            className="h-8 w-8 flex items-center justify-center rounded-md border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--secondary)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Plus className="w-3.5 h-3.5" aria-hidden="true" />
          </button>
        </div>

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

        <LoadPrevDropdown
          open={prevSimOpen}
          onToggle={handleOpenPrevSimulations}
          search={prevSimSearch}
          onSearchChange={setPrevSimSearch}
          items={filteredPrevSimulations}
          onSelect={handleLoadPrevSimulation}
        />

        {simulation && (
          <CompareDropdown
            currentSimId={simulation.simulation_id}
            prevSimulations={prevSimulations}
            onLoadList={ensureLoaded}
          />
        )}

        {simulation && (
          <button
            onClick={handleClone}
            className="h-8 px-2.5 text-xs font-medium rounded-md border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors flex items-center gap-1"
          >
            <Copy className="w-3.5 h-3.5" />
            Clone
          </button>
        )}
      </div>

      {/* Right: Playback controls + Settings + Avatar */}
      <div className="flex items-center gap-1">
        <ControlButton
          testId="play-btn"
          icon={<Play className="w-4 h-4" />}
          label="Play"
          onClick={handlePlay}
          hidden={isRunning}
        />
        <ControlButton
          testId="pause-btn"
          icon={<Pause className="w-4 h-4" />}
          label="Pause"
          onClick={handlePause}
          hidden={!isRunning}
        />
        <ControlButton
          testId="run-all-btn"
          icon={
            runAllLoading ? (
              <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
            ) : (
              <ChevronsRight className="w-4 h-4" />
            )
          }
          label="Run All"
          onClick={handleRunAll}
          disabled={
            isRunning ||
            runAllLoading ||
            !simulation ||
            (status !== SIM_STATUS.CONFIGURED && status !== SIM_STATUS.PAUSED)
          }
        />
        <ControlButton
          testId="step-btn"
          icon={<SkipForward className="w-4 h-4" />}
          label="Step"
          onClick={handleStep}
        />
        <ControlButton
          testId="reset-btn"
          icon={<RotateCcw className="w-4 h-4" />}
          label="Reset"
          onClick={handleReset}
        />
        <ControlButton
          testId="replay-btn"
          icon={<Rewind className="w-4 h-4" />}
          label="Replay"
          onClick={() => setReplayOpen(true)}
        />

        <div className="w-px h-6 bg-[var(--border)] mx-1" />

        <ControlButton
          icon={<AlertTriangle className="w-4 h-4" />}
          label="Inject Event"
          onClick={() => setInjectOpen(true)}
        />
        <ControlButton
          icon={<Cpu className="w-4 h-4" />}
          label="Engine Control"
          onClick={() => setEngineOpen(!engineOpen)}
        />
        <ControlButton
          icon={<Brain className="w-4 h-4" />}
          label="LLM Dashboard"
          onClick={() => useSimulationStore.getState().toggleLLMDashboard()}
        />
        <ControlButton
          testId="propagation-anim-toggle"
          icon={
            <Zap
              className={`w-4 h-4 ${propagationAnimEnabled ? "text-[var(--anim-share)]" : ""}`}
            />
          }
          label={propagationAnimEnabled ? "Animations ON" : "Animations OFF"}
          onClick={togglePropagationAnimations}
        />

        <div className="w-px h-6 bg-[var(--border)] mx-1" />

        <ThemeToggle />

        <ControlButton
          icon={<Settings className="w-4 h-4" />}
          label="Settings"
          onClick={() => navigate("/settings")}
        />

        <button
          className="w-8 h-8 rounded-full bg-[var(--secondary)] flex items-center justify-center hover:bg-[var(--secondary)] transition-colors ml-1"
          title="User profile"
          aria-label="User profile"
        >
          <User className="w-4 h-4 text-[var(--muted-foreground)]" aria-hidden="true" />
        </button>
      </div>

      {/* Modals */}
      <InjectEventModal isOpen={injectOpen} onClose={() => setInjectOpen(false)} />
      <ReplayModal isOpen={replayOpen} onClose={() => setReplayOpen(false)} />

      {/* Engine Control modal */}
      <EngineControlPanel isOpen={engineOpen} onClose={() => setEngineOpen(false)} />
    </div>
  );
}
