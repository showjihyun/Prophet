/**
 * ConversationThreadPage contract tests.
 *
 * @spec docs/spec/27_OPINIONS_SPEC.md#opinions-l3
 * SPEC Version: 0.1.0
 *
 * Originally auto-generated from the (IP-protected, off-disk)
 * docs/spec/ui/UI_15_CONVERSATION_THREAD.md before implementation.
 * Now tracked under the on-disk SPEC 27.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { useSimulationStore } from '@/store/simulationStore';
import ConversationThreadPage from '@/pages/ConversationThreadPage';

const useCommunityThreadMock = vi.fn(() => ({
  data: undefined as undefined | unknown,
  isLoading: false,
}));

vi.mock('@/api/queries', () => ({
  useSimulationSteps: () => ({ data: undefined, isLoading: false }),
  useCommunityThread: (...args: unknown[]) => useCommunityThreadMock(...args as []),
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
    useCommunityThreadMock.mockReturnValue({
      data: undefined,
      isLoading: false,
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

  /** @spec 27_OPINIONS_SPEC.md#opinions-l3 — AC-L3-01 */
  describe('API thread priority', () => {
    it('AC-L3-01: when API returns a thread, renders API topic + messages over derived', () => {
      useCommunityThreadMock.mockReturnValue({
        data: {
          thread_id: 't-api-1',
          topic: 'Universal basic income debate',
          participant_count: 5,
          message_count: 9,
          avg_sentiment: 0.42,
          messages: [
            {
              message_id: 'm-1',
              agent_id: 'agent-001',
              community_id: 'alpha',
              stance: 'Progressive',
              content: 'UBI would lift millions out of poverty.',
              reactions: { agree: 7, disagree: 1, nuanced: 2 },
              is_reply: false,
              reply_to_id: null,
            },
            {
              message_id: 'm-2',
              agent_id: 'agent-002',
              community_id: 'alpha',
              stance: 'Conservative',
              content: 'It would distort labour markets.',
              reactions: { agree: 4, disagree: 6, nuanced: 1 },
              is_reply: true,
              reply_to_id: 'm-1',
            },
          ],
        },
        isLoading: false,
      });
      renderPage();
      expect(screen.getByText('Universal basic income debate')).toBeInTheDocument();
      expect(screen.getByText('UBI would lift millions out of poverty.')).toBeInTheDocument();
      expect(screen.getByText('It would distort labour markets.')).toBeInTheDocument();
      // The synthetic step-derived "Step-1" / "Step-2" agent IDs MUST NOT appear.
      expect(screen.queryByText('Step-1')).not.toBeInTheDocument();
      expect(screen.queryByText('Step-2')).not.toBeInTheDocument();
    });
  });

  /** @spec 27_OPINIONS_SPEC.md#opinions-l3 — AC-L3-02 */
  describe('Breadcrumb derived from routed communityId', () => {
    it('AC-L3-02: middle breadcrumb entry contains the routed communityId, not a hard-coded label', () => {
      renderPage('gamma', 'thr-1');
      const nav = screen.getByTestId('page-nav');
      expect(nav.textContent).toContain('gamma');
      expect(nav.textContent).not.toContain('Alpha');
    });
  });

  /** @spec 27_OPINIONS_SPEC.md#opinions-sentiment-color — AC-L3-03 */
  describe('Shared sentiment colour utility', () => {
    it('AC-L3-03: file imports sentimentTextClass from utils/sentiment', () => {
      const filePath = path.resolve(
        __dirname,
        '../pages/ConversationThreadPage.tsx',
      );
      const src = readFileSync(filePath, 'utf-8');
      expect(src).toMatch(/from\s+["']\.\.\/utils\/sentiment["']/);
      expect(src).toContain('sentimentTextClass');
      expect(src).not.toMatch(/t\.avg_sentiment\s*>\s*0\.1/);
      expect(src).not.toMatch(/t\.avg_sentiment\s*<\s*-0\.1/);
    });
  });
});
