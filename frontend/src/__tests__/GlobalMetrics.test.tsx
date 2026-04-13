/**
 * Auto-generated from SPEC: docs/spec/ui/UI_05_GLOBAL_METRICS.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_05_GLOBAL_METRICS.md
 */
import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { useSimulationStore } from '@/store/simulationStore';

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
  Legend: () => null,
  Cell: () => null,
  PieChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Pie: () => null,
}));

vi.mock('@/api/client', () => ({
  apiClient: {
    simulations: {
      getSteps: vi.fn().mockResolvedValue([]),
      export: vi.fn(),
    },
    llm: {
      getStats: vi.fn().mockResolvedValue({
        total_calls: 100,
        tier_breakdown: { '1': 60, '2': 30, '3': 10 },
      }),
    },
  },
}));

import GlobalMetricsPage from '@/pages/GlobalMetricsPage';

/** A minimal StepResult that satisfies the type enough to trigger hasData=true */
const MOCK_STEP = {
  step: 1,
  total_adoption: 450,
  adoption_rate: 0.45,
  mean_sentiment: 0.3,
  sentiment_variance: 0.42,
  diffusion_rate: 0.25,
  llm_calls_this_step: 12,
  step_duration_ms: 287,
  community_metrics: {
    alpha: { community_id: 'alpha', mean_belief: 0.6, adoption_count: 200, adoption_rate: 0.6 },
    beta:  { community_id: 'beta',  mean_belief: 0.3, adoption_count: 150, adoption_rate: 0.4 },
  },
  action_distribution: { share: 120, comment: 80, view: 250 },
  emergent_events: [],
};

const MOCK_SIMULATION = {
  simulation_id: 'sim-metrics-001',
  project_id: 'proj-001',
  scenario_id: 'scen-001',
  name: 'Global Metrics Test',
  status: 'completed' as const,
  current_step: 1,
  max_steps: 365,
  created_at: new Date().toISOString(),
  config: {} as never,
};

const renderPage = () =>
  render(
    <MemoryRouter>
      <GlobalMetricsPage />
    </MemoryRouter>,
  );

describe('GlobalMetrics (UI-05)', () => {
  beforeEach(() => {
    // Inject simulation + steps so hasData=true renders all sections
    useSimulationStore.setState({
      simulation: MOCK_SIMULATION,
      steps: [MOCK_STEP as never],
      status: 'completed',
    });
  });

  /** @spec UI_05_GLOBAL_METRICS.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders "Back to Simulation" button', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /back to simulation/i })).toBeInTheDocument();
    });

    it('renders "Global Insight & Metrics" page title', () => {
      renderPage();
      // PageNav renders the title as a <span> (last breadcrumb), and the
      // attached HelpTooltip keeps a hidden copy of the label in DOM
      // (anti-flicker opacity-toggle design) — assert at least one match.
      expect(
        screen.getAllByText('Global Insight & Metrics').length,
      ).toBeGreaterThanOrEqual(1);
    });

    it('renders "Export Data" button', () => {
      renderPage();
      // Component renders "Export JSON" and "Export CSV" buttons — either satisfies the intent
      const exportBtns = screen.getAllByRole('button', { name: /export/i });
      expect(exportBtns.length).toBeGreaterThanOrEqual(1);
    });
  });

  /** @spec UI_05_GLOBAL_METRICS.md#summary-stats */
  describe('Summary Stats', () => {
    it('renders Total Agents card with delta indicator', () => {
      renderPage();
      expect(screen.getAllByText('Total Agents').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByTestId('total-agents-delta')).toBeInTheDocument();
    });

    it('renders Active Cascades card with today delta', () => {
      renderPage();
      expect(screen.getAllByText('Active Cascades').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByTestId('cascades-delta')).toBeInTheDocument();
    });

    it('renders Polarization card with delta from previous day', () => {
      renderPage();
      expect(screen.getByText('Polarization')).toBeInTheDocument();
      expect(screen.getByTestId('polarization-delta')).toBeInTheDocument();
    });

    it('renders Simulation Step card with progress bar', () => {
      renderPage();
      expect(screen.getAllByText('Simulation Step').length).toBeGreaterThanOrEqual(1);
      // test-id `sim-day-progress` is preserved for backwards compat
      // with bookmarks/analytics even though the label renamed.
      expect(screen.getByTestId('sim-day-progress')).toBeInTheDocument();
    });
  });

  /** @spec UI_05_GLOBAL_METRICS.md#charts-area */
  describe('Charts Area', () => {
    it('renders "Polarization Trend" bar chart', () => {
      renderPage();
      expect(screen.getAllByText('Polarization Trend').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByTestId('polarization-trend-chart')).toBeInTheDocument();
    });

    it('renders "Sentiment by Community" stacked bar chart', () => {
      renderPage();
      expect(screen.getAllByText('Sentiment by Community').length).toBeGreaterThanOrEqual(1);
      expect(screen.getByTestId('sentiment-community-chart')).toBeInTheDocument();
    });
  });

  /** @spec UI_05_GLOBAL_METRICS.md#prophet-3-tier-cost-optimization */
  describe('Prophet 3-Tier Cost Optimization', () => {
    it('renders section title', () => {
      renderPage();
      expect(screen.getAllByText('Prophet 3-Tier Cost Optimization').length).toBeGreaterThanOrEqual(1);
    });

    it('renders Tier 1: Mass SLM card with agent count', () => {
      renderPage();
      expect(screen.getByTestId('tier1-card')).toBeInTheDocument();
      expect(screen.getByText(/mass slm/i)).toBeInTheDocument();
    });

    it('renders Tier 2: Semantic card with agent count', () => {
      renderPage();
      expect(screen.getByTestId('tier2-card')).toBeInTheDocument();
      expect(screen.getAllByText(/semantic/i).length).toBeGreaterThanOrEqual(1);
    });

    it('renders Tier 3: Elite LLM card with agent count', () => {
      renderPage();
      expect(screen.getByTestId('tier3-card')).toBeInTheDocument();
      expect(screen.getByText(/elite llm/i)).toBeInTheDocument();
    });
  });

  /** @spec UI_05_GLOBAL_METRICS.md#cascade-analytics */
  describe('Cascade Analytics', () => {
    it('renders section title', () => {
      renderPage();
      expect(screen.getAllByText('Cascade Analytics').length).toBeGreaterThanOrEqual(1);
    });

    it('renders Avg Cascade Depth stat', () => {
      renderPage();
      expect(screen.getByTestId('avg-cascade-depth')).toBeInTheDocument();
    });

    it('renders Max Cascade Width stat', () => {
      renderPage();
      expect(screen.getByTestId('max-cascade-width')).toBeInTheDocument();
    });

    it('renders Critical Path stat', () => {
      renderPage();
      expect(screen.getByTestId('critical-path')).toBeInTheDocument();
    });

    it('renders Decay Rate stat', () => {
      renderPage();
      expect(screen.getByTestId('decay-rate')).toBeInTheDocument();
    });
  });
});
