/**
 * Auto-generated from SPEC: docs/spec/ui/UI_03_TOP_INFLUENCERS.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_03_TOP_INFLUENCERS.md
 */
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

vi.mock('recharts', () => ({
  ResponsiveContainer: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  LineChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Line: () => null,
  XAxis: () => null,
  YAxis: () => null,
  CartesianGrid: () => null,
  Tooltip: () => null,
  BarChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Bar: () => null,
  AreaChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Area: () => null,
  Cell: () => null,
  Legend: () => null,
  PieChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Pie: () => null,
}));

vi.mock('@/api/client', () => ({
  apiClient: {
    agents: {
      list: vi.fn().mockResolvedValue({
        items: [
          { agent_id: 'A-001', community_id: 'A', influence_score: 0.95, belief: 0.5, action: 'share', agent_type: 'influencer' },
          { agent_id: 'B-002', community_id: 'B', influence_score: 0.82, belief: -0.3, action: 'idle', agent_type: 'normal' },
          { agent_id: 'C-003', community_id: 'C', influence_score: 0.71, belief: 0.0, action: 'comment', agent_type: 'bridge' },
        ],
        total: 3,
      }),
    },
  },
}));

import TopInfluencersPage from '@/pages/TopInfluencersPage';
import { useSimulationStore } from '@/store/simulationStore';

const MOCK_SIMULATION = {
  simulation_id: 'sim-inf-1',
  name: 'Influencer Test Sim',
  status: 'completed',
  config: {},
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

const renderPage = (withSimulation = true) => {
  if (withSimulation) {
    useSimulationStore.setState({ simulation: MOCK_SIMULATION as any });
  } else {
    useSimulationStore.setState({ simulation: null });
  }
  return render(
    <MemoryRouter>
      <TopInfluencersPage />
    </MemoryRouter>,
  );
};

describe('TopInfluencers (UI-03)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /** @spec UI_03_TOP_INFLUENCERS.md#empty-state */
  describe('Empty State', () => {
    it('shows empty state when no simulation is active', () => {
      renderPage(false);
      expect(screen.getByText(/no active simulation/i)).toBeInTheDocument();
      expect(screen.getByText('Go to Projects')).toBeInTheDocument();
    });

    it('does not show table content when no simulation', () => {
      renderPage(false);
      expect(screen.queryByText('Agent ID')).not.toBeInTheDocument();
    });
  });

  /** @spec UI_03_TOP_INFLUENCERS.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders breadcrumb with "Home > Top Influencers"', () => {
      renderPage();
      expect(screen.getByText('Top Influencers')).toBeInTheDocument();
    });
  });

  /** @spec UI_03_TOP_INFLUENCERS.md#summary-stats */
  describe('Summary Stats', () => {
    it('renders 4 summary stat cards', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Influencers Tracked')).toBeInTheDocument();
      });
      expect(screen.getByText('Avg Influence Score')).toBeInTheDocument();
      expect(screen.getByText('Top Community')).toBeInTheDocument();
      expect(screen.getByText('Active Cascades')).toBeInTheDocument();
    });
  });

  /** @spec UI_03_TOP_INFLUENCERS.md#search-filter-bar */
  describe('Search + Filter Bar', () => {
    it('renders search input with placeholder', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/search agents/i)).toBeInTheDocument();
      });
    });

    it('renders filter button', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /filter/i })).toBeInTheDocument();
      });
    });
  });

  /** @spec UI_03_TOP_INFLUENCERS.md#data-table */
  describe('Data Table', () => {
    it('renders table with required column headers', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Agent ID')).toBeInTheDocument();
      });
      expect(screen.getByText('Community')).toBeInTheDocument();
      expect(screen.getByText('Influence Score')).toBeInTheDocument();
      expect(screen.getByText('Sentiment')).toBeInTheDocument();
      expect(screen.getByText('Chains')).toBeInTheDocument();
      expect(screen.getByText('Connections')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('renders influence score bars in score column', async () => {
      renderPage();
      await waitFor(() => {
        const scoreBars = screen.getAllByTestId(/influence-score-bar/);
        expect(scoreBars.length).toBeGreaterThan(0);
      });
    });

    it('renders community badges with colored dots', async () => {
      renderPage();
      await waitFor(() => {
        const communityBadges = screen.getAllByTestId(/community-badge/);
        expect(communityBadges.length).toBeGreaterThan(0);
      });
    });

    it('renders status badges (Active/Idle)', async () => {
      renderPage();
      await waitFor(() => {
        const statusBadges = screen.getAllByTestId(/status-badge/);
        expect(statusBadges.length).toBeGreaterThan(0);
      });
    });

    it('renders pagination controls', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByTestId('table-pagination')).toBeInTheDocument();
      });
    });
  });

  /** @spec UI_03_TOP_INFLUENCERS.md#right-sidebar */
  describe('Right Sidebar: Influence Distribution', () => {
    it('renders "Influence Distribution" chart title', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Influence Distribution')).toBeInTheDocument();
      });
    });

    it('renders horizontal bar chart with community bars', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByTestId('influence-distribution-chart')).toBeInTheDocument();
      });
    });
  });
});
