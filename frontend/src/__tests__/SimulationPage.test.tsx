/**
 * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md
 * SPEC Version: 0.1.0
 * Tests the main simulation page renders all 4 zones.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
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
      focusedStep: null,
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

  /**
   * @spec 26_ANALYTICS_SPEC.md#analytics-emergent-events (v0.3.0)
   *
   * Round-trip contract: when SimulationPage receives `?step=N`, it must
   * pin `focusedStep` in the store and render a dismissable banner.
   */
  describe('Step focus from Analytics deep-link (v0.3.0)', () => {
    /** Render helper that uses a real Route so useSearchParams works. */
    function renderWithStep(stepParam?: string) {
      const initialPath = stepParam
        ? `/simulation/sim-test-001?step=${stepParam}`
        : '/simulation/sim-test-001';
      return render(
        <MemoryRouter initialEntries={[initialPath]}>
          <Routes>
            <Route path="/simulation/:simulationId" element={<SimulationPage />} />
          </Routes>
        </MemoryRouter>,
      );
    }

    it('arriving with ?step=47 pins focusedStep=47 in the store', async () => {
      renderWithStep('47');
      await waitFor(() =>
        expect(useSimulationStore.getState().focusedStep).toBe(47),
      );
    });

    it('arriving without ?step= leaves focusedStep null', async () => {
      renderWithStep();
      // Give effects time to run — any setFocusedStep(N) would have fired by now
      await screen.findByTestId('simulation-page');
      expect(useSimulationStore.getState().focusedStep).toBeNull();
    });

    it('renders a banner announcing the focused step', async () => {
      renderWithStep('47');
      const banner = await screen.findByTestId('step-focus-banner');
      // Banner carries the specific step number. The "47" is wrapped in a
      // <strong> for emphasis, so assert against the flattened textContent
      // rather than using getByText (which only matches single text nodes).
      expect(banner.textContent).toMatch(/viewing step 47/i);
    });

    it('does NOT render the banner when there is no focus', async () => {
      renderWithStep();
      await screen.findByTestId('simulation-page');
      expect(screen.queryByTestId('step-focus-banner')).not.toBeInTheDocument();
    });

    it('banner "Return to live" button clears focusedStep', async () => {
      renderWithStep('47');
      const returnBtn = await screen.findByRole('button', {
        name: /return to live/i,
      });
      fireEvent.click(returnBtn);
      await waitFor(() =>
        expect(useSimulationStore.getState().focusedStep).toBeNull(),
      );
    });

    it('invalid ?step= values are ignored (no pin, no banner)', async () => {
      renderWithStep('not-a-number');
      await screen.findByTestId('simulation-page');
      expect(useSimulationStore.getState().focusedStep).toBeNull();
      expect(screen.queryByTestId('step-focus-banner')).not.toBeInTheDocument();
    });
  });
});
