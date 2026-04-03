/**
 * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md#scenario-comparison
 * SPEC Version: 0.1.0
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#scenario-comparison
 * @spec docs/spec/06_API_SPEC.md#get-simulationssimulation_idcompareother_simulation_id
 */
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ otherId: 'sim-other-456' }),
  };
});

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

const mockCompare = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    simulations: {
      compare: (...args: unknown[]) => mockCompare(...args),
    },
  },
}));

import ComparisonPage from '@/pages/ComparisonPage';
import { useSimulationStore } from '@/store/simulationStore';

const MOCK_COMPARISON_DATA = {
  simulation_a: 'sim-abc-123',
  simulation_b: 'sim-other-456',
  comparison: {
    adoption_rate_a: 0.42,
    adoption_rate_b: 0.31,
    mean_sentiment_a: 0.75,
    mean_sentiment_b: 0.55,
    total_propagation_a: 1500,
    total_propagation_b: 1200,
    viral_cascades_a: 5,
    viral_cascades_b: 3,
    winner: 'sim-abc-123',
  },
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/compare/sim-other-456']}>
      <ComparisonPage />
    </MemoryRouter>,
  );
}

describe('ComparisonPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
    // Set an active simulation in the store
    useSimulationStore.getState().setSimulation({
      simulation_id: 'sim-abc-123',
      status: 'completed',
      current_step: 10,
      max_steps: 10,
      config: {} as any,
    } as any);
  });

  /** @spec 07_FRONTEND_SPEC.md#scenario-comparison-layout */
  describe('Layout', () => {
    it('renders the page header with Scenario Comparison title', async () => {
      mockCompare.mockResolvedValue(MOCK_COMPARISON_DATA);
      renderPage();
      expect(screen.getByText('Scenario Comparison')).toBeInTheDocument();
    });

    it('renders back navigation button', async () => {
      mockCompare.mockResolvedValue(MOCK_COMPARISON_DATA);
      renderPage();
      // The ArrowLeft button is a back button
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#scenario-comparison-loading */
  describe('Loading State', () => {
    it('shows loading text while fetching comparison data', () => {
      mockCompare.mockReturnValue(new Promise(() => {})); // never resolves
      renderPage();
      expect(screen.getByText('Loading comparison...')).toBeInTheDocument();
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#scenario-comparison-data */
  describe('Comparison Data', () => {
    it('calls compare API with correct simulation IDs', async () => {
      mockCompare.mockResolvedValue(MOCK_COMPARISON_DATA);
      renderPage();
      await waitFor(() => expect(mockCompare).toHaveBeenCalledWith('sim-abc-123', 'sim-other-456'));
    });

    it('shows VS label between the two scenario panels', async () => {
      mockCompare.mockResolvedValue(MOCK_COMPARISON_DATA);
      renderPage();
      await waitFor(() => expect(screen.getByText('VS')).toBeInTheDocument());
    });

    it('shows Scenario A and Scenario B labels', async () => {
      mockCompare.mockResolvedValue(MOCK_COMPARISON_DATA);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Scenario A')).toBeInTheDocument();
        expect(screen.getByText('Scenario B')).toBeInTheDocument();
      });
    });

    it('renders all four metric comparison rows', async () => {
      mockCompare.mockResolvedValue(MOCK_COMPARISON_DATA);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Adoption Rate')).toBeInTheDocument();
        expect(screen.getByText('Mean Sentiment')).toBeInTheDocument();
        expect(screen.getByText('Total Propagation')).toBeInTheDocument();
        expect(screen.getByText('Viral Cascades')).toBeInTheDocument();
      });
    });

    it('shows winner banner when comparison has a winner', async () => {
      mockCompare.mockResolvedValue(MOCK_COMPARISON_DATA);
      renderPage();
      await waitFor(() => expect(screen.getByText(/Winner:/)).toBeInTheDocument());
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#scenario-comparison-empty */
  describe('Empty / Error State', () => {
    it('shows error message when no active simulation exists', () => {
      // Clear simulation from store by directly setting state
      useSimulationStore.setState({ simulation: null as any, status: null as any });
      mockCompare.mockResolvedValue(MOCK_COMPARISON_DATA);
      renderPage();
      expect(
        screen.getByText('No active simulation. Go back and select one.'),
      ).toBeInTheDocument();
    });

    it('shows error message on API failure', async () => {
      // Restore simulation
      useSimulationStore.getState().setSimulation({
        simulation_id: 'sim-abc-123',
        status: 'completed',
        current_step: 10,
        max_steps: 10,
        config: {} as any,
      } as any);
      mockCompare.mockRejectedValue(new Error('Network error'));
      renderPage();
      await waitFor(() => expect(screen.getByText('Network error')).toBeInTheDocument());
    });
  });
});
