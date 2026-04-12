/**
 * Zustand store for simulation state.
 * @spec docs/spec/07_FRONTEND_SPEC.md#state-management
 */
import { create } from "zustand";
import { LS_KEY_THEME, LS_KEY_SIMULATION_ID, LS_KEY_PROJECT_ID, DEFAULT_SLM_LLM_RATIO, DEFAULT_SIMULATION_SPEED, SIM_STATUS } from "@/config/constants";
import type {
  SimulationRun,
  SimulationStatus,
  StepResult,
  EmergentEvent,
  TierDistribution,
  EngineImpactReport,
} from "../types/simulation";
import type { ProjectSummary, ScenarioInfo, CreateSimulationConfig } from "../api/client";

export interface Toast {
  id: string;
  type: "info" | "success" | "warning" | "error";
  message: string;
}

interface SimulationStore {
  simulation: SimulationRun | null;
  status: SimulationStatus;
  currentStep: number;
  steps: StepResult[];
  latestStep: StepResult | null;
  emergentEvents: EmergentEvent[];

  /**
   * SPEC 26 §4.5.2 (v0.3.0) — Analytics deep-link step focus.
   * `null` = follow live; a number = user pinned a specific step (typically
   * from Analytics event-row deep-link). Orthogonal to `currentStep` —
   * `appendStep` must NOT mutate this field.
   */
  focusedStep: number | null;

  // WebSocket
  wsConnected: boolean;
  lastStepReceived: number;

  // UI state
  selectedAgentId: string | null;
  highlightedCommunity: string | null;
  isAgentInspectorOpen: boolean;
  isLLMDashboardOpen: boolean;

  // Engine control
  slmLlmRatio: number;
  tierDistribution: TierDistribution | null;
  impactAssessment: EngineImpactReport | null;

  // Speed
  speed: number;

  // Toast notifications
  toasts: Toast[];
  addToast: (toast: Omit<Toast, 'id'>) => void;
  removeToast: (id: string) => void;

  // Clone config (for cloning simulation to setup page)
  cloneConfig: CreateSimulationConfig | null;
  setCloneConfig: (config: CreateSimulationConfig | null) => void;

  // Theme
  theme: 'dark' | 'light';
  toggleTheme: () => void;

  // Project state
  currentProjectId: string | null;
  projects: ProjectSummary[];
  scenarios: ScenarioInfo[];
  setCurrentProject: (projectId: string | null) => void;
  setProjects: (projects: ProjectSummary[]) => void;
  setScenarios: (scenarios: ScenarioInfo[]) => void;

  // Actions
  setSimulation: (sim: SimulationRun) => void;
  appendStep: (step: StepResult) => void;
  setStepsBulk: (steps: StepResult[]) => void;
  appendEmergentEvent: (event: EmergentEvent) => void;
  setStatus: (status: SimulationStatus) => void;
  selectAgent: (agentId: string | null) => void;
  setSlmLlmRatio: (ratio: number) => void;
  setSpeed: (speed: number) => void;
  toggleLLMDashboard: () => void;
  setHighlightedCommunity: (communityId: string | null) => void;
  setFocusedStep: (step: number | null) => void;

  // Propagation animation (GAP-7)
  propagationAnimationsEnabled: boolean;
  togglePropagationAnimations: () => void;
}

export const useSimulationStore = create<SimulationStore>((set) => ({
  simulation: null,
  status: SIM_STATUS.CREATED,
  currentStep: 0,
  steps: [],
  latestStep: null,
  emergentEvents: [],
  focusedStep: null,
  wsConnected: false,
  lastStepReceived: 0,
  selectedAgentId: null,
  highlightedCommunity: null,
  isAgentInspectorOpen: false,
  isLLMDashboardOpen: false,
  slmLlmRatio: DEFAULT_SLM_LLM_RATIO,
  tierDistribution: null,
  impactAssessment: null,
  speed: DEFAULT_SIMULATION_SPEED,
  toasts: [],
  addToast: (toast) =>
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id: `${Date.now()}-${Math.random()}` }],
    })),
  removeToast: (id) =>
    set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
  cloneConfig: null,
  setCloneConfig: (config) => set({ cloneConfig: config }),
  theme: 'dark',
  currentProjectId: localStorage.getItem(LS_KEY_PROJECT_ID) || null,
  projects: [],
  scenarios: [],
  toggleTheme: () => set((state) => {
    const next = state.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    if (next === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
    localStorage.setItem(LS_KEY_THEME, next);
    return { theme: next };
  }),

  setCurrentProject: (projectId) => {
    if (projectId) {
      try { localStorage.setItem(LS_KEY_PROJECT_ID, projectId); } catch { /* quota */ }
    } else {
      localStorage.removeItem(LS_KEY_PROJECT_ID);
    }
    set({ currentProjectId: projectId });
  },
  setProjects: (projects) => set({ projects }),
  setScenarios: (scenarios) => set({ scenarios }),

  setSimulation: (sim) => {
    try { localStorage.setItem(LS_KEY_SIMULATION_ID, sim.simulation_id); } catch { /* quota exceeded */ }
    set({ simulation: sim, status: sim.status });
  },
  appendStep: (step) =>
    set((state) => {
      // FE-PERF-02: sliding window — cap at MAX_STEPS_IN_MEMORY
      const MAX_STEPS_IN_MEMORY = 100;
      const nextSteps = state.steps.length >= MAX_STEPS_IN_MEMORY
        ? [...state.steps.slice(-(MAX_STEPS_IN_MEMORY - 1)), step]
        : [...state.steps, step];
      return {
        steps: nextSteps,
        latestStep: step,
        currentStep: step.step,
        lastStepReceived: step.step,
      };
    }),
  // FE-PERF-03: bulk set — single store update for loading history
  setStepsBulk: (steps) =>
    set(() => {
      const MAX_STEPS_IN_MEMORY = 100;
      const trimmed = steps.length > MAX_STEPS_IN_MEMORY
        ? steps.slice(-MAX_STEPS_IN_MEMORY)
        : steps;
      const last = trimmed[trimmed.length - 1] ?? null;
      return {
        steps: trimmed,
        latestStep: last,
        currentStep: last?.step ?? 0,
        lastStepReceived: last?.step ?? 0,
      };
    }),
  appendEmergentEvent: (event) =>
    set((state) => {
      // FE-PERF-17: cap emergentEvents at 50 most recent
      const MAX_EMERGENT_EVENTS = 50;
      const nextEvents = state.emergentEvents.length >= MAX_EMERGENT_EVENTS
        ? [...state.emergentEvents.slice(-(MAX_EMERGENT_EVENTS - 1)), event]
        : [...state.emergentEvents, event];
      return { emergentEvents: nextEvents };
    }),
  setStatus: (status) => set({ status }),
  selectAgent: (agentId) =>
    set({ selectedAgentId: agentId, isAgentInspectorOpen: agentId !== null }),
  setSlmLlmRatio: (ratio) => set({ slmLlmRatio: ratio }),
  setSpeed: (speed) => set({ speed }),
  toggleLLMDashboard: () => set((state) => ({ isLLMDashboardOpen: !state.isLLMDashboardOpen })),
  setHighlightedCommunity: (communityId) => set({ highlightedCommunity: communityId }),
  // SPEC 26 §4.5.2 (v0.3.0) — pin/unpin a specific step from Analytics.
  setFocusedStep: (step) => set({ focusedStep: step }),
  propagationAnimationsEnabled: true,
  togglePropagationAnimations: () => set((state) => ({ propagationAnimationsEnabled: !state.propagationAnimationsEnabled })),
}));
