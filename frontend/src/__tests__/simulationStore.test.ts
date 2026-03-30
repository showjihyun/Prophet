/**
 * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md#state-management
 * SPEC Version: 0.1.0
 * Tests Zustand store actions and state transitions.
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useSimulationStore } from '../store/simulationStore';
import type { StepResult, EmergentEvent } from '../types/simulation';

describe('simulationStore', () => {
  beforeEach(() => {
    useSimulationStore.setState({
      simulation: null,
      status: 'created',
      currentStep: 0,
      steps: [],
      emergentEvents: [],
      selectedAgentId: null,
      highlightedCommunity: null,
      isAgentInspectorOpen: false,
      isLLMDashboardOpen: false,
      slmLlmRatio: 0.5,
      tierDistribution: null,
      impactAssessment: null,
      speed: 2,
      wsConnected: false,
      lastStepReceived: 0,
      currentProjectId: null,
      projects: [],
      scenarios: [],
    });
  });

  it('initializes with default state', () => {
    const state = useSimulationStore.getState();
    expect(state.status).toBe('created');
    expect(state.currentStep).toBe(0);
    expect(state.steps).toHaveLength(0);
    expect(state.slmLlmRatio).toBe(0.5);
    expect(state.speed).toBe(2);
  });

  it('setStatus updates status', () => {
    useSimulationStore.getState().setStatus('running');
    expect(useSimulationStore.getState().status).toBe('running');
  });

  it('appendStep adds step and updates currentStep', () => {
    const step: StepResult = {
      simulation_id: 'test',
      step: 5,
      total_adoption: 100,
      adoption_rate: 0.5,
      diffusion_rate: 10,
      mean_sentiment: 0.3,
      sentiment_variance: 0.1,
      community_metrics: {},
      emergent_events: [],
      action_distribution: {},
      llm_calls_this_step: 2,
      step_duration_ms: 150,
    };
    useSimulationStore.getState().appendStep(step);
    expect(useSimulationStore.getState().steps).toHaveLength(1);
    expect(useSimulationStore.getState().currentStep).toBe(5);
    expect(useSimulationStore.getState().lastStepReceived).toBe(5);
  });

  it('appendEmergentEvent adds event', () => {
    const event: EmergentEvent = {
      event_type: 'viral_cascade',
      step: 3,
      community_id: 'A',
      severity: 0.8,
      description: 'test cascade',
    };
    useSimulationStore.getState().appendEmergentEvent(event);
    expect(useSimulationStore.getState().emergentEvents).toHaveLength(1);
    expect(useSimulationStore.getState().emergentEvents[0].event_type).toBe('viral_cascade');
  });

  it('selectAgent opens inspector', () => {
    useSimulationStore.getState().selectAgent('agent-1');
    expect(useSimulationStore.getState().selectedAgentId).toBe('agent-1');
    expect(useSimulationStore.getState().isAgentInspectorOpen).toBe(true);
  });

  it('selectAgent(null) closes inspector', () => {
    useSimulationStore.getState().selectAgent('agent-1');
    useSimulationStore.getState().selectAgent(null);
    expect(useSimulationStore.getState().selectedAgentId).toBeNull();
    expect(useSimulationStore.getState().isAgentInspectorOpen).toBe(false);
  });

  it('setSlmLlmRatio updates ratio', () => {
    useSimulationStore.getState().setSlmLlmRatio(0.8);
    expect(useSimulationStore.getState().slmLlmRatio).toBe(0.8);
  });

  it('setSpeed updates speed', () => {
    useSimulationStore.getState().setSpeed(10);
    expect(useSimulationStore.getState().speed).toBe(10);
  });

  /** @spec 07_FRONTEND_SPEC.md#project-state */
  it('initializes with empty project state', () => {
    const state = useSimulationStore.getState();
    expect(state.currentProjectId).toBeNull();
    expect(state.projects).toHaveLength(0);
    expect(state.scenarios).toHaveLength(0);
  });

  it('setCurrentProject updates currentProjectId', () => {
    useSimulationStore.getState().setCurrentProject('proj-1');
    expect(useSimulationStore.getState().currentProjectId).toBe('proj-1');
  });

  it('setCurrentProject(null) clears currentProjectId', () => {
    useSimulationStore.getState().setCurrentProject('proj-1');
    useSimulationStore.getState().setCurrentProject(null);
    expect(useSimulationStore.getState().currentProjectId).toBeNull();
  });

  it('setProjects replaces projects list', () => {
    const mockProjects = [
      { project_id: 'p1', name: 'Test Project', description: '', status: 'active', scenario_count: 2, created_at: null },
    ];
    useSimulationStore.getState().setProjects(mockProjects);
    expect(useSimulationStore.getState().projects).toHaveLength(1);
    expect(useSimulationStore.getState().projects[0].project_id).toBe('p1');
  });

  it('setScenarios replaces scenarios list', () => {
    const mockScenarios = [
      { scenario_id: 's1', name: 'Test Scenario', description: '', status: 'draft', simulation_id: null, config: {}, created_at: null },
    ];
    useSimulationStore.getState().setScenarios(mockScenarios);
    expect(useSimulationStore.getState().scenarios).toHaveLength(1);
    expect(useSimulationStore.getState().scenarios[0].scenario_id).toBe('s1');
  });
});
