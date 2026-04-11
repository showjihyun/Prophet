/**
 * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md
 * SPEC Version: 0.1.0
 * Tests the main simulation page renders all 4 zones.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { useSimulationStore } from '../store/simulationStore';

// Mock WebSocket hook
vi.mock('../hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

// Mock Cytoscape (not available in jsdom)
vi.mock('cytoscape', () => ({
  default: vi.fn(() => ({
    on: vi.fn(),
    batch: vi.fn((cb: () => void) => cb()),
    nodes: () => ({ length: 0, forEach: vi.fn(), toArray: () => [], removeClass: vi.fn(), style: vi.fn() }),
    edges: () => ({ length: 0, forEach: vi.fn(), removeStyle: vi.fn(), style: vi.fn() }),
    zoom: vi.fn(() => 1),
    width: vi.fn(() => 800),
    height: vi.fn(() => 600),
    fit: vi.fn(),
    destroy: vi.fn(),
    style: vi.fn(),
  })),
}));

vi.mock('../api/client', () => ({
  apiClient: {
    network: { get: vi.fn().mockRejectedValue(new Error('no network')) },
    agents: { list: vi.fn().mockResolvedValue({ items: [] }) },
    simulations: {
      getSteps: vi.fn().mockResolvedValue([]),
      run: vi.fn().mockRejectedValue(new Error('no sim')),
      pause: vi.fn().mockRejectedValue(new Error('no sim')),
      resume: vi.fn().mockRejectedValue(new Error('no sim')),
      reset: vi.fn().mockRejectedValue(new Error('no sim')),
      step: vi.fn().mockRejectedValue(new Error('no sim')),
    },
    projects: {
      list: vi.fn().mockResolvedValue([]),
      get: vi.fn().mockResolvedValue({ scenarios: [] }),
    },
    scenarios: { list: vi.fn().mockResolvedValue([]) },
  },
}));

import SimulationPage from '../pages/SimulationPage';

const MOCK_SIMULATION = {
  simulation_id: 'sim-test-001',
  project_id: 'proj-001',
  scenario_id: 'scen-001',
  name: 'Simulation Page Test',
  status: 'running' as const,
  current_step: 5,
  max_steps: 365,
  created_at: new Date().toISOString(),
  config: {} as never,
};

describe('SimulationPage', () => {
  beforeEach(() => {
    // Reset store and inject a mock simulation so the full layout renders
    useSimulationStore.setState({
      simulation: MOCK_SIMULATION,
      status: 'running',
      currentStep: 5,
      steps: [],
      emergentEvents: [],
      isLLMDashboardOpen: false,
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#simulation-dashboard */
  it('renders the simulation page with control panel', () => {
    render(
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('simulation-page')).toBeInTheDocument();
    expect(screen.getByTestId('control-panel')).toBeInTheDocument();
  });

  it('renders graph panel', async () => {
    // GraphPanel is lazy-loaded; await Suspense resolution
    render(
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>,
    );
    expect(await screen.findByTestId('graph-panel')).toBeInTheDocument();
  });

  it('renders timeline panel', () => {
    render(
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('timeline-panel')).toBeInTheDocument();
  });

  it('renders metrics panel', () => {
    render(
      <MemoryRouter>
        <SimulationPage />
      </MemoryRouter>,
    );
    expect(screen.getByTestId('metrics-panel')).toBeInTheDocument();
  });
});
