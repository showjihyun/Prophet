/**
 * Simulation Control Bar — Zone 1.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 *
 * Left: Logo + status badge
 * Center: Global Insights link, Scenario dropdown, Speed buttons
 * Right: Play/Pause/Step/Reset/Replay + Settings + Avatar
 */
import { useNavigate } from "react-router-dom";
import { useState, useEffect, useRef } from "react";
import {
  Brain,
  Play,
  Pause,
  SkipForward,
  RotateCcw,
  Rewind,
  Settings,
  User,
  AlertTriangle,
  BarChart3,
  Cpu,
  Plus,
} from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
import { apiClient } from '../../api/client';
import type { SimulationRun } from '../../types/simulation';
import ThemeToggle from '../shared/ThemeToggle';
import InjectEventModal from '../shared/InjectEventModal';
import ReplayModal from '../shared/ReplayModal';
import MonteCarloModal from '../shared/MonteCarloModal';
import EngineControlPanel from './EngineControlPanel';

const SPEEDS = [1, 2, 5, 10] as const;

export default function ControlPanel() {
  const navigate = useNavigate();
  const simulation = useSimulationStore((s) => s.simulation);
  const status = useSimulationStore((s) => s.status);
  const currentStep = useSimulationStore((s) => s.currentStep);
  const setStatus = useSimulationStore((s) => s.setStatus);
  const appendStep = useSimulationStore((s) => s.appendStep);
  const setSimulation = useSimulationStore((s) => s.setSimulation);
  const speed = useSimulationStore((s) => s.speed);
  const setSpeed = useSimulationStore((s) => s.setSpeed);
  const currentProjectId = useSimulationStore((s) => s.currentProjectId);
  const projects = useSimulationStore((s) => s.projects);
  const scenarios = useSimulationStore((s) => s.scenarios);
  const setCurrentProject = useSimulationStore((s) => s.setCurrentProject);
  const setProjects = useSimulationStore((s) => s.setProjects);
  const setScenarios = useSimulationStore((s) => s.setScenarios);

  const [injectOpen, setInjectOpen] = useState(false);
  const [replayOpen, setReplayOpen] = useState(false);
  const [monteCarloOpen, setMonteCarloOpen] = useState(false);
  const [engineOpen, setEngineOpen] = useState(false);

  // Previous simulations list for the "Load Previous" dropdown
  const [prevSimulations, setPrevSimulations] = useState<SimulationRun[]>([]);
  const [prevSimOpen, setPrevSimOpen] = useState(false);
  const setSteps = useSimulationStore((s) => s.appendStep);

  const stepIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Auto-step loop: runs steps automatically while status is "running"
  useEffect(() => {
    if (status !== "running" || !simulation?.simulation_id) {
      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current);
        stepIntervalRef.current = null;
      }
      return;
    }

    const runStep = async () => {
      try {
        const result = await apiClient.simulations.step(simulation.simulation_id);
        appendStep(result);
        // Check completion
        if (result.step + 1 >= (simulation.max_steps ?? 50)) {
          setStatus("completed");
        }
      } catch {
        // Step failed — pause
        setStatus("paused");
      }
    };

    stepIntervalRef.current = setInterval(runStep, 1000 / speed);

    return () => {
      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current);
        stepIntervalRef.current = null;
      }
    };
  }, [status, speed, simulation?.simulation_id]);

  // Load projects list on mount
  useEffect(() => {
    apiClient.projects.list().then((res) => setProjects(Array.isArray(res) ? res : [])).catch(() => {});
  }, [setProjects]);

  // When project changes, load its scenarios
  const handleProjectChange = async (projectId: string) => {
    setCurrentProject(projectId || null);
    if (!projectId) {
      setScenarios([]);
      return;
    }
    try {
      const detail = await apiClient.projects.get(projectId);
      setScenarios(detail.scenarios);
    } catch { /* ignore */ }
  };

  // When scenario changes, load its simulation if it has one
  const handleScenarioChange = async (scenarioId: string) => {
    const scenario = scenarios.find((s) => s.scenario_id === scenarioId);
    if (scenario?.simulation_id) {
      try {
        const sim = await apiClient.simulations.get(scenario.simulation_id);
        setSimulation(sim);
      } catch { /* ignore */ }
    }
  };

  // Create new scenario via prompt
  const handleNewScenario = async () => {
    if (!currentProjectId) return;
    const name = window.prompt("New scenario name:");
    if (!name?.trim()) return;
    try {
      const scenario = await apiClient.projects.createScenario(currentProjectId, { name: name.trim() });
      setScenarios([...scenarios, scenario]);
    } catch { /* ignore */ }
  };

  // Load list of previous simulations when dropdown is opened
  const handleOpenPrevSimulations = async () => {
    setPrevSimOpen((open) => !open);
    if (prevSimulations.length === 0) {
      try {
        const res = await apiClient.simulations.list();
        setPrevSimulations(res.items ?? []);
      } catch { /* ignore */ }
    }
  };

  // Load a previous simulation into the store
  const handleLoadPrevSimulation = async (simId: string) => {
    setPrevSimOpen(false);
    try {
      const sim = await apiClient.simulations.get(simId);
      setSimulation(sim);
      const stepsData = await apiClient.simulations.getSteps(simId);
      for (const step of stepsData) {
        setSteps(step);
      }
    } catch { /* ignore */ }
  };

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
      className="shrink-0 relative flex items-center justify-between px-4 border-b border-[var(--border)] bg-[var(--card)]"
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
        <span data-testid="status-badge" className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--card)]">
          <span
            className={`w-2 h-2 rounded-full ${
              isRunning
                ? "bg-[var(--sentiment-positive)] animate-pulse-dot"
                : status === "paused"
                  ? "bg-[var(--sentiment-warning)]"
                  : "bg-[var(--muted-foreground)]"
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

        {/* Project selector */}
        <select
          data-testid="project-select"
          className="h-8 px-2 text-xs border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-1 focus:ring-gray-300"
          value={currentProjectId ?? ""}
          onChange={(e) => handleProjectChange(e.target.value)}
        >
          <option value="">-- Project --</option>
          {projects.map((p) => (
            <option key={p.project_id} value={p.project_id}>{p.name}</option>
          ))}
        </select>

        {/* Scenario selector + add button */}
        <div className="flex items-center gap-1">
          <select
            data-testid="scenario-select"
            className="h-8 px-2 text-xs border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-1 focus:ring-gray-300"
            defaultValue=""
            onChange={(e) => handleScenarioChange(e.target.value)}
          >
            <option value="">-- Scenario --</option>
            {scenarios.map((s) => (
              <option key={s.scenario_id} value={s.scenario_id}>{s.name}</option>
            ))}
          </select>
          <button
            onClick={handleNewScenario}
            title="New scenario"
            disabled={!currentProjectId}
            className="h-8 w-8 flex items-center justify-center rounded-md border border-[var(--border)] bg-[var(--card)] hover:bg-[var(--secondary)] disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            <Plus className="w-3.5 h-3.5" />
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

        {/* Load Previous simulation dropdown */}
        <div className="relative">
          <button
            data-testid="load-prev-btn"
            onClick={handleOpenPrevSimulations}
            className="h-8 px-2.5 text-xs font-medium rounded-md border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors"
          >
            Load Previous
          </button>
          {prevSimOpen && (
            <div className="absolute left-0 top-9 z-50 w-64 rounded-md border border-[var(--border)] bg-[var(--card)] shadow-lg overflow-hidden">
              {prevSimulations.length === 0 ? (
                <div className="px-3 py-2 text-xs text-[var(--muted-foreground)]">No simulations found</div>
              ) : (
                prevSimulations.slice(0, 10).map((sim) => (
                  <button
                    key={sim.simulation_id}
                    onClick={() => handleLoadPrevSimulation(sim.simulation_id)}
                    className="w-full text-left px-3 py-2 text-xs hover:bg-[var(--secondary)] transition-colors border-b border-[var(--border)] last:border-0"
                  >
                    <span className="font-medium text-[var(--foreground)] block truncate">{sim.name}</span>
                    <span className="text-[var(--muted-foreground)]">
                      {sim.status} · Step {sim.current_step}/{sim.max_steps}
                    </span>
                  </button>
                ))
              )}
            </div>
          )}
        </div>
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
          icon={<BarChart3 className="w-4 h-4" />}
          label="Monte Carlo"
          onClick={() => setMonteCarloOpen(true)}
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
        >
          <User className="w-4 h-4 text-[var(--muted-foreground)]" />
        </button>
      </div>

      {/* Modals */}
      <InjectEventModal isOpen={injectOpen} onClose={() => setInjectOpen(false)} />
      <ReplayModal isOpen={replayOpen} onClose={() => setReplayOpen(false)} />
      <MonteCarloModal isOpen={monteCarloOpen} onClose={() => setMonteCarloOpen(false)} />

      {/* Engine Control dropdown */}
      {engineOpen && (
        <div className="absolute right-16 top-14 z-40 w-72">
          <EngineControlPanel />
        </div>
      )}
    </div>
  );
}

function ControlButton({
  icon,
  label,
  onClick,
  testId,
  hidden,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  testId?: string;
  hidden?: boolean;
}) {
  return (
    <button
      data-testid={testId}
      onClick={onClick}
      title={label}
      aria-hidden={hidden}
      className={`w-8 h-8 flex items-center justify-center rounded-md text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors ${hidden ? "invisible absolute" : ""}`}
    >
      {icon}
    </button>
  );
}
