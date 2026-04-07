/**
 * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md
 * SPEC Version: 0.1.0
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#simulationsidanalytics
 */
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

const mockGetSteps = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    simulations: {
      getSteps: (...args: unknown[]) => mockGetSteps(...args),
    },
  },
}));

// Recharts uses ResizeObserver — provide a stub for jsdom
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

import AnalyticsPage from '@/pages/AnalyticsPage';
import { useSimulationStore } from '@/store/simulationStore';

const MOCK_SIMULATION = {
  simulation_id: 'sim-42',
  name: 'Test Analytics Sim',
  status: 'completed',
  config: {},
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const MOCK_STEPS = [
  {
    step: 1,
    adoption_rate: 0.1,
    mean_sentiment: 0.2,
    community_metrics: {
      alpha: { adoption_rate: 0.15, mean_sentiment: 0.3 },
      beta: { adoption_rate: 0.05, mean_sentiment: 0.1 },
    },
    emergent_events: [],
  },
  {
    step: 2,
    adoption_rate: 0.4,
    mean_sentiment: 0.5,
    community_metrics: {
      alpha: { adoption_rate: 0.5, mean_sentiment: 0.6 },
      beta: { adoption_rate: 0.3, mean_sentiment: 0.4 },
    },
    emergent_events: [
      {
        event_type: 'viral_cascade',
        step: 2,
        community_id: 'alpha',
        severity: 0.8,
        description: 'Rapid spread detected',
      },
    ],
  },
];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/analytics']}>
      <AnalyticsPage />
    </MemoryRouter>,
  );
}

describe('AnalyticsPage (07_FRONTEND_SPEC)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
    // Reset store state
    useSimulationStore.setState({ simulation: null, steps: [] });
    mockGetSteps.mockResolvedValue([]);
  });

  /** @spec 07_FRONTEND_SPEC.md#analytics-layout */
  describe('Layout', () => {
    it('renders the page with data-testid', () => {
      renderPage();
      expect(screen.getByTestId('analytics-page')).toBeInTheDocument();
    });

    it('renders the Post-Run Analytics header', () => {
      renderPage();
      expect(screen.getByText('Post-Run Analytics')).toBeInTheDocument();
    });

    it('renders a back button with aria-label', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /go back/i })).toBeInTheDocument();
    });

    it('clicking back button calls navigate(-1)', () => {
      renderPage();
      screen.getByRole('button', { name: /go back/i }).click();
      expect(mockNavigate).toHaveBeenCalledWith(-1);
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#analytics-empty-states */
  describe('Empty / No-Simulation State', () => {
    it('shows no-simulation message when store has no simulation', () => {
      renderPage();
      expect(
        screen.getByText(/No active simulation/i),
      ).toBeInTheDocument();
    });

    it('shows Go to Projects button when no simulation', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /go to projects/i })).toBeInTheDocument();
    });

    it('navigates to /projects when Go to Projects clicked', () => {
      renderPage();
      screen.getByRole('button', { name: /go to projects/i }).click();
      expect(mockNavigate).toHaveBeenCalledWith('/projects');
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#analytics-simulation-name */
  describe('Simulation Name Display', () => {
    it('shows simulation name in header when simulation exists', () => {
      useSimulationStore.setState({ simulation: MOCK_SIMULATION as any, steps: [] });
      renderPage();
      expect(screen.getByText('Test Analytics Sim')).toBeInTheDocument();
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#analytics-fetch */
  describe('Step Fetching', () => {
    it('calls getSteps when simulation is set but store has no steps', async () => {
      useSimulationStore.setState({ simulation: MOCK_SIMULATION as any, steps: [] });
      mockGetSteps.mockResolvedValue([]);
      renderPage();
      await waitFor(() => expect(mockGetSteps).toHaveBeenCalledWith('sim-42'));
    });

    it('does NOT call getSteps when store already has steps', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      // Give any potential async work time to run
      await waitFor(() => expect(mockGetSteps).not.toHaveBeenCalled());
    });

    it('shows loading state while fetching', async () => {
      useSimulationStore.setState({ simulation: MOCK_SIMULATION as any, steps: [] });
      // Return a never-resolving promise to keep loading state
      mockGetSteps.mockReturnValue(new Promise(() => {}));
      renderPage();
      await waitFor(() =>
        expect(screen.getByText(/loading analytics/i)).toBeInTheDocument(),
      );
    });

    it('shows error message when fetch fails', async () => {
      useSimulationStore.setState({ simulation: MOCK_SIMULATION as any, steps: [] });
      mockGetSteps.mockRejectedValue(new Error('Network error'));
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Network error')).toBeInTheDocument(),
      );
    });

    it('shows empty-steps message when fetch returns empty array', async () => {
      useSimulationStore.setState({ simulation: MOCK_SIMULATION as any, steps: [] });
      mockGetSteps.mockResolvedValue([]);
      renderPage();
      await waitFor(() =>
        expect(
          screen.getByText(/No step data available yet/i),
        ).toBeInTheDocument(),
      );
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#analytics-summary-cards */
  describe('Summary Cards', () => {
    it('renders Total Steps card', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() => expect(screen.getByText('Total Steps')).toBeInTheDocument());
    });

    it('renders Final Adoption card', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() => expect(screen.getByText('Final Adoption')).toBeInTheDocument());
    });

    it('renders Final Sentiment card', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() => expect(screen.getByText('Final Sentiment')).toBeInTheDocument());
    });

    it('renders Emergent Events card', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() => expect(screen.getByText('Emergent Events')).toBeInTheDocument());
    });

    it('shows correct final adoption percentage', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      // Last step adoption_rate=0.4 → 40.0%
      await waitFor(() => expect(screen.getByText('40.0%')).toBeInTheDocument());
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#analytics-charts */
  describe('Chart Sections', () => {
    it('renders Adoption Rate Over Time section', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Adoption Rate Over Time')).toBeInTheDocument(),
      );
    });

    it('renders Mean Sentiment Over Time section', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Mean Sentiment Over Time')).toBeInTheDocument(),
      );
    });

    it('renders Community Adoption Comparison section', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText(/Community Adoption Comparison/i)).toBeInTheDocument(),
      );
    });

    it('renders Monte Carlo Results section', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Monte Carlo Results')).toBeInTheDocument(),
      );
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#analytics-emergent-events */
  describe('Emergent Event Timeline', () => {
    it('renders Emergent Event Timeline section heading', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Emergent Event Timeline')).toBeInTheDocument(),
      );
    });

    it('shows emergent event type when events exist', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        // event_type viral_cascade becomes "viral cascade" after replace
        expect(screen.getByText('viral cascade')).toBeInTheDocument(),
      );
    });

    it('shows event description', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Rapid spread detected')).toBeInTheDocument(),
      );
    });

    it('shows no-events message when steps have no emergent events', async () => {
      const stepsNoEvents = MOCK_STEPS.map((s) => ({ ...s, emergent_events: [] }));
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: stepsNoEvents as any,
      });
      renderPage();
      await waitFor(() =>
        expect(
          screen.getByText(/No emergent events detected/i),
        ).toBeInTheDocument(),
      );
    });
  });
});
