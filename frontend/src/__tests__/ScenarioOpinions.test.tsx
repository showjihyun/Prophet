/**
 * Auto-generated from SPEC: docs/spec/ui/UI_13_SCENARIO_OPINIONS.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_13_SCENARIO_OPINIONS.md
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { useSimulationStore } from '@/store/simulationStore';
import ScenarioOpinionsPage from '@/pages/ScenarioOpinionsPage';

vi.mock('@/api/queries', () => ({
  useSimulationSteps: () => ({ data: undefined, isLoading: false }),
}));

// 5 communities: alpha, beta, gamma, delta, bridge
// community_name is derived as `Community ${cid}` — e.g. "Community alpha"
// agent_count = adoption_count / adoption_rate
// alpha: 2148 / 1 = 2148 (adoption_rate ~1 so use exact ratio)
// beta:  1808 / 1 = 1808
// Use exact: adoption_count=2148, adoption_rate=1.0 → 2148 agents
//            adoption_count=1808, adoption_rate=1.0 → 1808 agents
const MOCK_STEP = {
  step: 1,
  adoption_rate: 0.4,
  mean_sentiment: 0.2,
  sentiment_variance: 0.1,
  total_adoption: 400,
  diffusion_rate: 0.05,
  action_distribution: { share: 200, comment: 100 },
  emergent_events: [],
  llm_calls_this_step: 5,
  step_duration_ms: 100,
  community_metrics: {
    alpha: {
      mean_belief: 0.5,
      adoption_rate: 1.0,
      adoption_count: 2148,
      size: 2148,
      community_id: 'alpha',
      new_propagation_count: 20,
    },
    beta: {
      mean_belief: 0.3,
      adoption_rate: 1.0,
      adoption_count: 1808,
      size: 1808,
      community_id: 'beta',
      new_propagation_count: 15,
    },
    gamma: {
      mean_belief: -0.1,
      adoption_rate: 0.5,
      adoption_count: 500,
      size: 1000,
      community_id: 'gamma',
      new_propagation_count: 10,
    },
    delta: {
      mean_belief: 0.2,
      adoption_rate: 0.6,
      adoption_count: 600,
      size: 1000,
      community_id: 'delta',
      new_propagation_count: 8,
    },
    bridge: {
      mean_belief: 0.0,
      adoption_rate: 0.3,
      adoption_count: 300,
      size: 1000,
      community_id: 'bridge',
      new_propagation_count: 5,
    },
  },
};

const MOCK_SIMULATION = {
  simulation_id: 'sim-opinions-001',
  project_id: 'proj-001',
  scenario_id: 'scen-001',
  status: 'completed' as const,
  current_step: 1,
  max_steps: 365,
  created_at: new Date().toISOString(),
  config: {} as never,
};

const renderPage = () =>
  render(
    <MemoryRouter>
      <ScenarioOpinionsPage />
    </MemoryRouter>,
  );

describe('ScenarioOpinionsPage (UI-13)', () => {
  beforeEach(() => {
    useSimulationStore.setState({
      simulation: MOCK_SIMULATION as never,
      steps: [MOCK_STEP as never],
      latestStep: MOCK_STEP as never,
      status: 'completed',
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders page-nav with breadcrumb', () => {
      renderPage();
      expect(screen.getByTestId('page-nav')).toBeInTheDocument();
    });

    it('shows Level 1 badge', () => {
      renderPage();
      expect(screen.getByText('Level 1')).toBeInTheDocument();
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#header-section */
  describe('Header Section', () => {
    it('renders title "Scenario Opinion Landscape"', () => {
      renderPage();
      expect(screen.getByText('Scenario Opinion Landscape')).toBeInTheDocument();
    });

    it('renders 4 stat cards', () => {
      renderPage();
      expect(screen.getByText('Avg Sentiment')).toBeInTheDocument();
      expect(screen.getByText('Polarization')).toBeInTheDocument();
      expect(screen.getByText('Total Conversations')).toBeInTheDocument();
      expect(screen.getByText('Active Cascades')).toBeInTheDocument();
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#community-opinion-cards */
  describe('Community Opinion Cards', () => {
    it('renders 5 community opinion cards', () => {
      renderPage();
      expect(screen.getByText('Community alpha')).toBeInTheDocument();
      expect(screen.getByText('Community beta')).toBeInTheDocument();
      expect(screen.getByText('Community gamma')).toBeInTheDocument();
      expect(screen.getByText('Community delta')).toBeInTheDocument();
      expect(screen.getByText('Community bridge')).toBeInTheDocument();
    });

    it('each card shows agent count', () => {
      renderPage();
      // alpha: 2148/1.0 = 2148, beta: 1808/1.0 = 1808
      expect(screen.getByText(/2,148 agents/)).toBeInTheDocument();
      expect(screen.getByText(/1,808 agents/)).toBeInTheDocument();
    });

    it('each card has View Community link', () => {
      renderPage();
      const links = screen.getAllByText('View Community');
      expect(links.length).toBe(5);
    });

    it('renders section title "Community Opinion Breakdown"', () => {
      renderPage();
      expect(screen.getByText('Community Opinion Breakdown')).toBeInTheDocument();
    });
  });
});
