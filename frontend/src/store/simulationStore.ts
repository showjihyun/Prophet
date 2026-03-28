/**
 * Zustand store for simulation state.
 * @spec docs/spec/07_FRONTEND_SPEC.md#state-management
 */
import { create } from "zustand";
import type {
  SimulationRun,
  SimulationStatus,
  StepResult,
  EmergentEvent,
  TierDistribution,
  EngineImpactReport,
} from "../types/simulation";

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

  // Theme
  theme: 'dark' | 'light';
  toggleTheme: () => void;

  // Actions
  setSimulation: (sim: SimulationRun) => void;
  appendStep: (step: StepResult) => void;
  appendEmergentEvent: (event: EmergentEvent) => void;
  setStatus: (status: SimulationStatus) => void;
  selectAgent: (agentId: string | null) => void;
  setSlmLlmRatio: (ratio: number) => void;
  setSpeed: (speed: number) => void;
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
  slmLlmRatio: 0.5,
  tierDistribution: null,
  impactAssessment: null,
  speed: 2,
  theme: 'dark',
  toggleTheme: () => set((state) => {
    const next = state.theme === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    if (next === 'light') {
      document.documentElement.classList.add('light');
    } else {
      document.documentElement.classList.remove('light');
    }
    localStorage.setItem('prophet-theme', next);
    return { theme: next };
  }),

  setSimulation: (sim) => set({ simulation: sim, status: sim.status }),
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
}));
