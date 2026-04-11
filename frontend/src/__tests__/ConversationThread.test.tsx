/**
 * Auto-generated from SPEC: docs/spec/ui/UI_15_CONVERSATION_THREAD.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_15_CONVERSATION_THREAD.md
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { useSimulationStore } from '@/store/simulationStore';
import ConversationThreadPage from '@/pages/ConversationThreadPage';

vi.mock('@/api/queries', () => ({
  useSimulationSteps: () => ({ data: undefined, isLoading: false }),
  useCommunityThread: () => ({ data: undefined, isLoading: false }),
}));

const makeStep = (step: number, sentiment: number) => ({
  step,
  adoption_rate: 0.4,
  mean_sentiment: sentiment,
  sentiment_variance: 0.1,
  total_adoption: step * 400,
  diffusion_rate: 0.05,
  action_distribution: { share: 200, comment: 100 },
  emergent_events: [],
  llm_calls_this_step: 5,
  step_duration_ms: 100,
  community_metrics: {
    alpha: {
      mean_belief: 0.5,
      adoption_rate: 0.4,
      adoption_count: 100,
      size: 250,
      community_id: 'A',
      new_propagation_count: 20,
      dominant_action: 'share',
    },
    beta: {
      mean_belief: 0.3,
      adoption_rate: 0.3,
      adoption_count: 75,
      size: 150,
      community_id: 'B',
      new_propagation_count: 15,
      dominant_action: 'comment',
    },
  },
});

// Two steps: step 1 positive sentiment (→ Progressive), step 2 negative (→ Conservative)
const MOCK_STEPS = [makeStep(1, 0.5), makeStep(2, -0.5)];

const MOCK_SIMULATION = {
  simulation_id: 'sim-thread-001',
  project_id: 'proj-001',
  scenario_id: 'scen-001',
  status: 'completed' as const,
  current_step: 2,
  max_steps: 365,
  created_at: new Date().toISOString(),
  config: {} as never,
};

const renderPage = (communityId = 'alpha', threadId = 't1') =>
  render(
    <MemoryRouter initialEntries={[`/opinions/${communityId}/thread/${threadId}`]}>
      <Routes>
        <Route
          path="/opinions/:communityId/thread/:threadId"
          element={<ConversationThreadPage />}
        />
      </Routes>
    </MemoryRouter>,
  );

describe('ConversationThreadPage (UI-15)', () => {
  beforeEach(() => {
    useSimulationStore.setState({
      simulation: MOCK_SIMULATION as never,
      steps: MOCK_STEPS as never[],
      latestStep: MOCK_STEPS[MOCK_STEPS.length - 1] as never,
      status: 'completed',
    });
  });

  /** @spec UI_15_CONVERSATION_THREAD.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders page-nav', () => {
      renderPage();
      expect(screen.getByTestId('page-nav')).toBeInTheDocument();
    });

    it('shows Level 3 badge', () => {
      renderPage();
      expect(screen.getByText('Level 3')).toBeInTheDocument();
    });
  });

  /** @spec UI_15_CONVERSATION_THREAD.md#header-section */
  describe('Header', () => {
    it('renders thread topic title derived from step data', () => {
      renderPage();
      // derivedThread uses latest step: "Step 2: share dominant — 40% adoption"
      const matches = screen.getAllByText(/Step 2/);
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });

    it('renders category tag from dominant action', () => {
      renderPage();
      // category_tag = cm.dominant_action ?? "simulation" = "share"
      expect(screen.getByText('share')).toBeInTheDocument();
    });

    it('shows participant count', () => {
      renderPage();
      expect(screen.getAllByText(/Participants/).length).toBeGreaterThanOrEqual(1);
    });

    it('shows avg sentiment badge', () => {
      renderPage();
      expect(screen.getByText(/Avg Sentiment/)).toBeInTheDocument();
    });
  });

  /** @spec UI_15_CONVERSATION_THREAD.md#thread-messages */
  describe('Thread Messages', () => {
    it('renders messages with step agent IDs', () => {
      renderPage();
      // derivedMessages produces agent_id = "Step-N"
      expect(screen.getAllByText('Step-1').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Step-2').length).toBeGreaterThanOrEqual(1);
    });

    it('renders stance badges', () => {
      renderPage();
      // Step 1: sentiment=0.5 → Progressive, Step 2: sentiment=-0.5 → Conservative
      expect(screen.getAllByText('Progressive').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Conservative').length).toBeGreaterThanOrEqual(1);
    });

    it('renders reaction counts (Agree, Disagree, Nuanced)', () => {
      renderPage();
      expect(screen.getAllByText(/Agree/).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Disagree/).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Nuanced/).length).toBeGreaterThanOrEqual(1);
    });

    it('renders reply messages with indentation', () => {
      renderPage();
      // idx > 0 → is_reply=true → data-testid="thread-reply"
      const replies = document.querySelectorAll('[data-testid="thread-reply"]');
      expect(replies.length).toBeGreaterThanOrEqual(1);
    });
  });
});
