/**
 * Simulation Control Bar — Zone 1.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar
 *
 * Left: Logo + status badge
 * Center: Global Insights link, Scenario dropdown, Speed buttons
 * Right: Play/Pause/Step/Reset/Replay + Settings + Avatar
 */
import { useNavigate } from "react-router-dom";
import { useState, useEffect, useRef, useMemo } from "react";
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
  BarChart3,
  Cpu,
  Plus,
  Copy,
  GitCompare,
  Zap,
} from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
import { apiClient } from '../../api/client';
import type { SimulationRun, SimulationStatus } from '../../types/simulation';
import type { ScenarioInfo, CreateSimulationConfig } from '../../api/client';
import {
  SIM_STATUS,
  TERMINAL_SIM_STATUSES,
  STARTABLE_SIM_STATUSES,
} from '@/config/constants';
import ThemeToggle from '../shared/ThemeToggle';
import InjectEventModal from '../shared/InjectEventModal';
import ReplayModal from '../shared/ReplayModal';
import MonteCarloModal from '../shared/MonteCarloModal';
import EngineControlPanel from './EngineControlPanel';

const SPEEDS = [1, 2, 5, 10] as const;

export default function ControlPanel() {
  const navigate = useNavigate();

  // State selectors — values used in render output
  const simulation = useSimulationStore((s) => s.simulation);
  const status = useSimulationStore((s) => s.status);
  const currentStep = useSimulationStore((s) => s.currentStep);
  const speed = useSimulationStore((s) => s.speed);
  const currentProjectId = useSimulationStore((s) => s.currentProjectId);
  const propagationAnimEnabled = useSimulationStore((s) => s.propagationAnimationsEnabled);
  const projects = useSimulationStore((s) => s.projects);
  const scenarios = useSimulationStore((s) => s.scenarios);

  // Action selectors used inside effects (stable references needed for dep array)
  const appendStep = useSimulationStore((s) => s.appendStep);
  const setStatus = useSimulationStore((s) => s.setStatus);

  // Action callbacks — use getState() inside handlers so these don't subscribe
  // to the store and won't trigger re-renders when action references change.
  const setSimulation = (sim: SimulationRun) => useSimulationStore.getState().setSimulation(sim);
  const setSpeed = (s: number) => useSimulationStore.getState().setSpeed(s);
  const setCurrentProject = (id: string | null) => useSimulationStore.getState().setCurrentProject(id);
  const setScenarios = (s: ScenarioInfo[]) => useSimulationStore.getState().setScenarios(s);
  const setCloneConfig = (c: CreateSimulationConfig | null) => useSimulationStore.getState().setCloneConfig(c);
  const togglePropagationAnimations = () => useSimulationStore.getState().togglePropagationAnimations();

  const [injectOpen, setInjectOpen] = useState(false);
  const [replayOpen, setReplayOpen] = useState(false);
  const [monteCarloOpen, setMonteCarloOpen] = useState(false);
  const [engineOpen, setEngineOpen] = useState(false);
  const [compareOpen, setCompareOpen] = useState(false);
  const [runAllLoading, setRunAllLoading] = useState(false);
  const [creating, setCreating] = useState(false);

  // Previous simulations list for the "Load Previous" dropdown
  const [prevSimulations, setPrevSimulations] = useState<SimulationRun[]>([]);
  const [prevSimSearch, setPrevSimSearch] = useState("");
  const filteredPrevSimulations = useMemo(() => {
    if (!prevSimSearch.trim()) return prevSimulations.slice(0, 20);
    const q = prevSimSearch.toLowerCase();
    return prevSimulations.filter((s) => s.name.toLowerCase().includes(q) || s.simulation_id.includes(q)).slice(0, 20);
  }, [prevSimulations, prevSimSearch]);
  const [prevSimOpen, setPrevSimOpen] = useState(false);
  const stepIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  // FE-PERF-10: prevent request pileup at high speeds (in-flight guard)
  const stepInFlightRef = useRef(false);

  // Stable refs for simulation ID and max_steps — updated on every render so the
  // interval callback always sees current values without being a dependency itself.
  const simIdRef = useRef(simulation?.simulation_id);
  const maxStepsRef = useRef(simulation?.max_steps ?? 365);
  useEffect(() => {
    simIdRef.current = simulation?.simulation_id;
    maxStepsRef.current = simulation?.max_steps ?? 365;
  });

  // Auto-step loop: runs steps automatically while status is RUNNING
  // Skip when runAll is active — the server handles all steps in that case.
  // Uses refs for simulation ID and max_steps to avoid interval teardown on
  // simulation object reference changes.
  useEffect(() => {
    if (status !== SIM_STATUS.RUNNING || !simIdRef.current || runAllLoading) {
      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current);
        stepIntervalRef.current = null;
      }
      return;
    }

    const runStep = async () => {
      const simId = simIdRef.current;
      if (!simId) return;
      // FE-PERF-10: skip tick if previous step request is still pending
      if (stepInFlightRef.current) return;
      stepInFlightRef.current = true;
      try {
        const result = await apiClient.simulations.step(simId);
        appendStep(result);
        // Check completion
        if (result.step + 1 >= maxStepsRef.current) {
          setStatus(SIM_STATUS.COMPLETED);
        }
      } catch {
        // Step failed — pause
        setStatus(SIM_STATUS.PAUSED);
      } finally {
        stepInFlightRef.current = false;
      }
    };

    stepIntervalRef.current = setInterval(runStep, 1000 / speed);

    return () => {
      if (stepIntervalRef.current) {
        clearInterval(stepIntervalRef.current);
        stepIntervalRef.current = null;
      }
    };
  }, [status, speed, appendStep, setStatus, runAllLoading]);

  // Load projects list on mount
  useEffect(() => {
    apiClient.projects.list()
      .then((res) => useSimulationStore.getState().setProjects(Array.isArray(res) ? res : []))
      .catch(() => {});
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-restore project from simulation and load scenarios on mount
  useEffect(() => {
    // If simulation has a project_id but currentProjectId is empty, restore it
    const simProjectId = (simulation as Record<string, unknown>)?.project_id as string | undefined;
    const effectiveProjectId = currentProjectId || simProjectId;
    if (!effectiveProjectId) return;
    if (!currentProjectId && simProjectId) {
      setCurrentProject(simProjectId);
    }
    // Load scenarios if empty
    if (scenarios.length === 0) {
      apiClient.projects.get(effectiveProjectId).then((detail) => {
        setScenarios(detail.scenarios ?? []);
      }).catch(() => {});
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentProjectId, simulation]);

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

  // Create new simulation inline — no page navigation
  const handleNewSimulation = async () => {
    if (!currentProjectId) {
      alert("Please select a project first.");
      return;
    }
    const name = window.prompt("Simulation name:", `Simulation ${new Date().toLocaleDateString()}`);
    if (!name?.trim()) return;
    setCreating(true);
    try {
      const sim = await apiClient.simulations.create({
        name: name.trim(),
        project_id: currentProjectId,
        campaign: {
          name: name.trim(),
          channels: ["social_media"],
          message: "Default campaign message",
          target_communities: [],
        },
        max_steps: 365,
      });
      setSimulation(sim);
      setStatus(SIM_STATUS.CONFIGURED);
    } catch (err) {
      alert(`Failed to create simulation: ${err instanceof Error ? err.message : "Unknown error"}`);
    } finally {
      setCreating(false);
    }
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
      // FE-PERF-03: single bulk update instead of O(n^2) per-step loop
      useSimulationStore.getState().setStepsBulk(stepsData);
    } catch { /* ignore */ }
  };

  // Clone: copy current sim config to setup page
  const handleClone = () => {
    if (!simulation) return;
    setCloneConfig({
      name: `${simulation.name} (clone)`,
      campaign: {
        name: `${simulation.name} (clone)`,
        channels: [],
        message: "",
        target_communities: [],
      },
      max_steps: simulation.max_steps,
    });
    navigate("/setup");
  };

  const isRunning = status === SIM_STATUS.RUNNING;

  const handlePlay = async () => {
    if (!simulation?.simulation_id) return;
    try {
      const simId = simulation.simulation_id;
      if (STARTABLE_SIM_STATUSES.includes(status)) {
        await apiClient.simulations.start(simId);
      } else if (TERMINAL_SIM_STATUSES.includes(status)) {
        // Recover from terminal state: reset → start
        await apiClient.simulations.stop(simId);
        await apiClient.simulations.start(simId);
      } else {
        await apiClient.simulations.resume(simId);
      }
      setStatus(SIM_STATUS.RUNNING);
    } catch { /* status unchanged on failure */ }
  };

  const handlePause = async () => {
    try {
      if (simulation?.simulation_id) {
        await apiClient.simulations.pause(simulation.simulation_id);
        setStatus(SIM_STATUS.PAUSED);
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
    if (!window.confirm("Reset simulation? This will stop the current run.")) return;
    try {
      if (simulation?.simulation_id) {
        await apiClient.simulations.stop(simulation.simulation_id);
        setStatus(SIM_STATUS.CREATED);
      }
    } catch { /* ignore */ }
  };

  const handleRunAll = async () => {
    if (!simulation?.simulation_id || runAllLoading) return;
    setRunAllLoading(true);
    setStatus(SIM_STATUS.RUNNING);
    try {
      const report = await apiClient.simulations.runAll(simulation.simulation_id);
      setStatus(report.status as SimulationStatus);
    } catch {
      // leave status unchanged on failure
    } finally {
      setRunAllLoading(false);
    }
  };

  // Keyboard shortcuts: Space=Play/Pause, ArrowRight=Step, Escape=Reset
  useEffect(() => {
    const handleKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
      switch (e.key) {
        case ' ':
          e.preventDefault();
          if (isRunning) handlePause(); else handlePlay();
          break;
        case 'ArrowRight':
          handleStep();
          break;
        case 'Escape':
          handleReset();
          break;
      }
    };
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isRunning]);

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
        <span data-testid="status-badge" className="inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--card)]">
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
            ? `Running`
            : status === SIM_STATUS.PAUSED
              ? "Paused"
              : status === SIM_STATUS.COMPLETED
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
          aria-label="Select project"
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
            aria-label="Select scenario"
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
            <div className="absolute left-0 top-9 z-50 w-72 rounded-md border border-[var(--border)] bg-[var(--card)] shadow-lg overflow-hidden">
              <div className="px-2 py-1.5 border-b border-[var(--border)]">
                <input
                  type="text"
                  placeholder="Search simulations..."
                  value={prevSimSearch}
                  onChange={(e) => setPrevSimSearch(e.target.value)}
                  className="w-full h-7 px-2 text-xs rounded border border-[var(--border)] bg-[var(--background)]"
                  autoFocus
                />
              </div>
              <div className="max-h-60 overflow-y-auto">
                {filteredPrevSimulations.length === 0 ? (
                  <div className="px-3 py-2 text-xs text-[var(--muted-foreground)]">No simulations found</div>
                ) : (
                  filteredPrevSimulations.map((sim) => (
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
            </div>
          )}
        </div>

        {/* Compare: opens dropdown of other simulations to compare */}
        {simulation && (
          <div className="relative">
            <button
              onClick={() => {
                setCompareOpen((open) => !open);
                if (prevSimulations.length === 0) {
                  apiClient.simulations.list().then((res) => setPrevSimulations(res.items ?? [])).catch(() => {});
                }
              }}
              className="h-8 px-2.5 text-xs font-medium rounded-md border border-[var(--border)] bg-[var(--card)] text-[var(--muted-foreground)] hover:bg-[var(--secondary)] transition-colors flex items-center gap-1"
            >
              <GitCompare className="w-3.5 h-3.5" />
              Compare
            </button>
            {compareOpen && (
              <div className="absolute left-0 top-9 z-50 w-64 rounded-md border border-[var(--border)] bg-[var(--card)] shadow-lg overflow-hidden">
                {prevSimulations.filter((s) => s.simulation_id !== simulation.simulation_id).length === 0 ? (
                  <div className="px-3 py-2 text-xs text-[var(--muted-foreground)]">No other simulations to compare</div>
                ) : (
                  prevSimulations
                    .filter((s) => s.simulation_id !== simulation.simulation_id)
                    .slice(0, 10)
                    .map((s) => (
                      <button
                        key={s.simulation_id}
                        onClick={() => { navigate(`/compare/${s.simulation_id}`); setCompareOpen(false); }}
                        className="w-full text-left px-3 py-2 text-xs hover:bg-[var(--secondary)] transition-colors border-b border-[var(--border)] last:border-0"
                      >
                        <span className="font-medium text-[var(--foreground)] block truncate">{s.name}</span>
                        <span className="text-[var(--muted-foreground)]">{s.status}</span>
                      </button>
                    ))
                )}
              </div>
            )}
          </div>
        )}

        {/* Clone: copies current sim config to setup page */}
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
          icon={runAllLoading ? <span className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" /> : <ChevronsRight className="w-4 h-4" />}
          label="Run All"
          onClick={handleRunAll}
          disabled={isRunning || runAllLoading || !simulation || (status !== SIM_STATUS.CONFIGURED && status !== SIM_STATUS.PAUSED)}
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
        <ControlButton
          testId="propagation-anim-toggle"
          icon={<Zap className={`w-4 h-4 ${propagationAnimEnabled ? "text-[var(--anim-share)]" : ""}`} />}
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
  disabled,
}: {
  icon: React.ReactNode;
  label: string;
  onClick: () => void;
  testId?: string;
  hidden?: boolean;
  disabled?: boolean;
}) {
  return (
    <button
      data-testid={testId}
      onClick={onClick}
      title={label}
      aria-label={label}
      aria-hidden={hidden || undefined}
      tabIndex={hidden ? -1 : undefined}
      disabled={disabled}
      className={`w-8 h-8 flex items-center justify-center rounded-md text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${hidden ? "invisible absolute" : ""}`}
    >
      {icon}
    </button>
  );
}
