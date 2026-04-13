/**
 * ScenarioOpinionsPage contract tests.
 *
 * @spec docs/spec/27_OPINIONS_SPEC.md#opinions-l1
 * SPEC Version: 0.1.0
 *
 * Originally auto-generated from the (IP-protected, off-disk)
 * docs/spec/ui/UI_13_SCENARIO_OPINIONS.md before implementation.
 * Now tracked under the on-disk SPEC 27.
 */
import { render, screen, within } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { MemoryRouter } from 'react-router-dom';
import { useSimulationStore } from '@/store/simulationStore';
import ScenarioOpinionsPage from '@/pages/ScenarioOpinionsPage';

vi.mock('@/api/queries', () => ({
  useSimulationSteps: () => ({ data: undefined, isLoading: false }),
  useOverallOpinionSynthesis: () => ({
    mutate: vi.fn(),
    data: undefined,
    isPending: false,
    isError: false,
    error: null,
  }),
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
      // HelpTooltip duplicates labels in DOM (anti-flicker design)
      expect(screen.getAllByText('Avg Sentiment').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Polarization').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Total Conversations').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Active Cascades').length).toBeGreaterThanOrEqual(1);
    });
  });

  /** @spec 27_OPINIONS_SPEC.md#opinions-l1 */
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
      expect(screen.getAllByText('Community Opinion Breakdown').length).toBeGreaterThanOrEqual(1);
    });
  });

  /** @spec 27_OPINIONS_SPEC.md#opinions-l1-stat — AC-L1-02 / AC-L1-03 */
  describe('Stat card delta contract', () => {
    it('AC-L1-02: with only one step in store, change line is absent on every stat card', () => {
      renderPage();
      // None of the hard-coded demo deltas should appear.
      expect(screen.queryByText(/from yesterday/)).not.toBeInTheDocument();
      expect(screen.queryByText(/124 today/)).not.toBeInTheDocument();
      expect(screen.queryByText(/12 new/)).not.toBeInTheDocument();
      // The literal "High" Polarization tag is also a hard-coded leftover.
      expect(screen.queryByText(/^High$/)).not.toBeInTheDocument();
    });

    it('AC-L1-02: with two steps in store, change line is computed from prev step', () => {
      const prevStep = {
        ...MOCK_STEP,
        step: 0,
        mean_sentiment: 0.1,           // 0.2 - 0.1 = +0.10
        sentiment_variance: 0.2,       // 0.1 - 0.2 = -0.10  (lower polarization is good → "positive")
        adoption_rate: 0.3,            // *1000 → 300; latest 400; diff = +100
        community_metrics: {
          ...MOCK_STEP.community_metrics,
          alpha: { ...MOCK_STEP.community_metrics.alpha, new_propagation_count: 10 },
        },
      };
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as never,
        steps: [prevStep as never, MOCK_STEP as never],
        latestStep: MOCK_STEP as never,
        status: 'completed',
      });
      renderPage();
      // Avg sentiment delta: +0.10 from prev step
      expect(screen.getByText(/\+0\.10 from prev step/)).toBeInTheDocument();
      // Active cascades delta: scaled adoption_rate diff = +100 (from prev step)
      expect(screen.getByText(/\+100 from prev step/)).toBeInTheDocument();
    });

    it('AC-L1-03: Polarization uses inverted changeType (a decrease is rendered as positive)', () => {
      const prevStep = {
        ...MOCK_STEP,
        step: 0,
        sentiment_variance: 0.2, // latest 0.1 → diff = -0.10, inverted = positive tone
      };
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as never,
        steps: [prevStep as never, MOCK_STEP as never],
        latestStep: MOCK_STEP as never,
        status: 'completed',
      });
      renderPage();
      const polLabel = screen.getByText('Polarization');
      // The card root holds the StatCard. Walk up to the card and look for the
      // sentiment-positive class on the change pill (inverted: decrease == good).
      const card = polLabel.closest('[data-testid="stat-card"]');
      expect(card).not.toBeNull();
      const pill = within(card as HTMLElement).getByText(/-0\.10 from prev step/);
      expect(pill.className).toContain('text-[var(--sentiment-positive)]');
    });
  });

  /** @spec 27_OPINIONS_SPEC.md#opinions-sentiment-color — AC-L1-04 */
  describe('Shared sentiment colour utility', () => {
    it('AC-L1-04: file imports sentimentTextClass from utils/sentiment', () => {
      const filePath = path.resolve(
        __dirname,
        '../pages/ScenarioOpinionsPage.tsx',
      );
      const src = readFileSync(filePath, 'utf-8');
      expect(src).toMatch(/from\s+["']\.\.\/utils\/sentiment["']/);
      expect(src).toContain('sentimentTextClass');
      // Inline ternaries on the threshold are forbidden.
      expect(src).not.toMatch(/avg_sentiment\s*>\s*0\.1/);
      expect(src).not.toMatch(/c\.avg_sentiment\s*<\s*-0\.1/);
    });
  });
});
