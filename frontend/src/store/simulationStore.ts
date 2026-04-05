/**
 * Zustand store for simulation state.
 * @spec docs/spec/07_FRONTEND_SPEC.md#state-management
 */
import { create } from "zustand";
import { LS_KEY_THEME, LS_KEY_SIMULATION_ID, LS_KEY_PROJECT_ID, DEFAULT_SLM_LLM_RATIO, DEFAULT_SIMULATION_SPEED } from "@/config/constants";
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
  emergentEvents: EmergentEvent[];

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
  appendEmergentEvent: (event: EmergentEvent) => void;
  setStatus: (status: SimulationStatus) => void;
  selectAgent: (agentId: string | null) => void;
  setSlmLlmRatio: (ratio: number) => void;
  setSpeed: (speed: number) => void;
  toggleLLMDashboard: () => void;
  setHighlightedCommunity: (communityId: string | null) => void;
}

export const useSimulationStore = create<SimulationStore>((set) => ({
  simulation: null,
  status: "created",
  currentStep: 0,
  steps: [],
  emergentEvents: [],
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
    set((state) => ({
      steps: [...state.steps, step],
      currentStep: step.step,
      lastStepReceived: step.step,
    })),
  appendEmergentEvent: (event) =>
    set((state) => ({
      emergentEvents: [...state.emergentEvents, event],
    })),
  setStatus: (status) => set({ status }),
  selectAgent: (agentId) =>
    set({ selectedAgentId: agentId, isAgentInspectorOpen: agentId !== null }),
  setSlmLlmRatio: (ratio) => set({ slmLlmRatio: ratio }),
  setSpeed: (speed) => set({ speed }),
  toggleLLMDashboard: () => set((state) => ({ isLLMDashboardOpen: !state.isLLMDashboardOpen })),
  setHighlightedCommunity: (communityId) => set({ highlightedCommunity: communityId }),
}));
