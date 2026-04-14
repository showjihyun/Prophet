/**
 * CommunityOpinionPage contract tests.
 *
 * @spec docs/spec/27_OPINIONS_SPEC.md#opinions-l2
 * SPEC Version: 0.1.0
 *
 * Originally auto-generated from the (IP-protected, off-disk)
 * docs/spec/ui/UI_14_COMMUNITY_OPINION.md before implementation.
 * Now tracked under the on-disk SPEC 27.
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { readFileSync } from 'node:fs';
import path from 'node:path';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { useSimulationStore } from '@/store/simulationStore';
import CommunityOpinionPage from '@/pages/CommunityOpinionPage';

// `useCommunityThreads` returns this — tests override per-case via mockReturnValue.
const useCommunityThreadsMock = vi.fn(() => ({
  data: undefined as undefined | { threads: unknown[] },
  isLoading: false,
}));

vi.mock('@/api/queries', () => ({
  useSimulationSteps: () => ({ data: undefined, isLoading: false }),
  useCommunityThreads: (...args: unknown[]) => useCommunityThreadsMock(...args as []),
  useCommunityOpinionSynthesis: () => ({
    mutate: vi.fn(),
    data: undefined,
    isPending: false,
    isError: false,
    error: null,
  }),
  useCommunityOpinionQuery: () => ({ data: null }),
}));

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
      adoption_rate: 0.4,
      adoption_count: 100,
      size: 250,
      community_id: 'A',
      new_propagation_count: 20,
    },
    beta: {
      mean_belief: 0.3,
      adoption_rate: 0.3,
      adoption_count: 75,
      size: 150,
      community_id: 'B',
      new_propagation_count: 15,
    },
    gamma: {
      mean_belief: -0.1,
      adoption_rate: 0.2,
      adoption_count: 40,
      size: 100,
      community_id: 'C',
      new_propagation_count: 10,
    },
  },
};

const MOCK_SIMULATION = {
  simulation_id: 'sim-001',
  project_id: 'proj-001',
  scenario_id: 'scen-001',
  status: 'completed' as const,
  current_step: 1,
  max_steps: 365,
  created_at: new Date().toISOString(),
  config: {} as never,
};

const renderPage = (communityId = 'alpha') =>
  render(
    <MemoryRouter initialEntries={[`/opinions/${communityId}`]}>
      <Routes>
        <Route path="/opinions/:communityId" element={<CommunityOpinionPage />} />
      </Routes>
    </MemoryRouter>,
  );

describe('CommunityOpinionPage (UI-14)', () => {
  beforeEach(() => {
    useSimulationStore.setState({
      simulation: MOCK_SIMULATION as never,
      steps: [MOCK_STEP as never],
      latestStep: MOCK_STEP as never,
      status: 'completed',
    });
    useCommunityThreadsMock.mockReturnValue({
      data: undefined,
      isLoading: false,
    });
  });

  /** @spec UI_14_COMMUNITY_OPINION.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders page-nav', () => {
      renderPage();
      expect(screen.getByTestId('page-nav')).toBeInTheDocument();
    });

    it('shows Level 2 Community badge', () => {
      renderPage();
      expect(screen.getByText('Level 2 Community')).toBeInTheDocument();
    });
  });

  /** @spec UI_14_COMMUNITY_OPINION.md#header-section */
  describe('Header', () => {
    it('renders community name', () => {
      renderPage();
      expect(screen.getByText('Community alpha')).toBeInTheDocument();
    });

    it('renders agent count derived from step data', () => {
      renderPage();
      // adoption_count / adoption_rate = 100 / 0.4 = 250
      const matches = screen.getAllByText(/250 agents/);
      expect(matches.length).toBeGreaterThanOrEqual(1);
    });
  });

  /** @spec UI_14_COMMUNITY_OPINION.md#opinion-clusters */
  describe('Opinion Clusters', () => {
    it('renders "Opinion Clusters" section title', () => {
      renderPage();
      // The HelpTooltip alongside the heading also renders the same label
      // text inside its (visually hidden) tooltip body, so query by role.
      expect(
        screen.getByRole('heading', { name: /Opinion Clusters/ }),
      ).toBeInTheDocument();
    });

    it('renders cluster cards derived from step data', () => {
      renderPage();
      // derivedClusters maps steps to "Step N Activity" topic_names
      expect(screen.getByText('Step 1 Activity')).toBeInTheDocument();
    });

    it('each cluster card shows stance breakdown', () => {
      renderPage();
      expect(screen.getAllByText(/Support/).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Oppose/).length).toBeGreaterThanOrEqual(1);
    });
  });

  /** @spec 27_OPINIONS_SPEC.md#opinions-l2-threads */
  describe('Recent Conversations', () => {
    it('renders "Recent Conversations" section', () => {
      renderPage();
      expect(
        screen.getByRole('heading', { name: /Recent Conversations/ }),
      ).toBeInTheDocument();
    });

    it('renders conversation items with message counts', () => {
      renderPage();
      const items = screen.getAllByText(/messages/);
      expect(items.length).toBeGreaterThanOrEqual(1);
    });

    /** AC-L2-02 */
    it('AC-L2-02: prefers API thread data over step-derived synthetic when API non-empty', () => {
      useCommunityThreadsMock.mockReturnValue({
        data: {
          threads: [
            {
              thread_id: 'thr-real-1',
              topic: 'Tax reform debate',
              participant_count: 7,
              message_count: 42,
              avg_sentiment: 0.3,
            },
            {
              thread_id: 'thr-real-2',
              topic: 'Climate accord',
              participant_count: 4,
              message_count: 11,
              avg_sentiment: -0.2,
            },
          ],
        },
        isLoading: false,
      });
      renderPage();
      expect(screen.getByText('Tax reform debate')).toBeInTheDocument();
      expect(screen.getByText('Climate accord')).toBeInTheDocument();
      // Real API message counts should win over the step-derived ones.
      expect(screen.getByText(/42 messages/)).toBeInTheDocument();
      expect(screen.getByText(/11 messages/)).toBeInTheDocument();
    });
  });

  /** @spec 27_OPINIONS_SPEC.md#opinions-sentiment-color — AC-L2-03 */
  describe('Shared sentiment colour utility', () => {
    it('AC-L2-03: file imports sentimentTextClass from utils/sentiment', () => {
      const filePath = path.resolve(
        __dirname,
        '../pages/CommunityOpinionPage.tsx',
      );
      const src = readFileSync(filePath, 'utf-8');
      expect(src).toMatch(/from\s+["']\.\.\/utils\/sentiment["']/);
      expect(src).toContain('sentimentTextClass');
      expect(src).not.toMatch(/meta\.sentiment\s*>\s*0\.1/);
      expect(src).not.toMatch(/meta\.sentiment\s*<\s*-0\.1/);
    });
  });
});
