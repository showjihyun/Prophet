/**
 * Tests for OverallOpinionPanel.
 *
 * @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis
 *
 * Mirrors EliteLLMNarrativePanel.test.tsx — same four visual states
 * (idle / pending / success / error) plus the per-community breakdown
 * section that only the cross-community panel has.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import OverallOpinionPanel from '@/components/community/OverallOpinionPanel';
import type { CommunityOpinion, OverallOpinion } from '@/types/api';

type MutationState = {
  mutate: ReturnType<typeof vi.fn>;
  data: OverallOpinion | undefined;
  isPending: boolean;
  isError: boolean;
  error: Error | null;
};

const mutationState: MutationState = {
  mutate: vi.fn(),
  data: undefined,
  isPending: false,
  isError: false,
  error: null,
};

vi.mock('@/api/queries', () => ({
  useOverallOpinionSynthesis: () => mutationState,
}));

const MOCK_COMMUNITY: CommunityOpinion = {
  opinion_id: 'op-c1',
  simulation_id: 'sim-1',
  community_id: 'early_adopters',
  step: 10,
  summary: 'Early adopters embraced the campaign immediately.',
  sentiment_trend: 'rising',
  themes: [],
  divisions: [],
  dominant_emotions: ['excitement'],
  key_quotes: [],
  source_step_count: 10,
  source_agent_count: 100,
  llm_provider: 'ollama',
  llm_model: 'llama3.2:1b',
  is_fallback_stub: false,
};

const MOCK_OVERALL: OverallOpinion = {
  overall: {
    opinion_id: 'op-overall',
    simulation_id: 'sim-1',
    community_id: '__overall__',
    step: 10,
    summary:
      'Early adopters drove a rapid cascade while skeptics resisted, leaving the campaign polarised.',
    sentiment_trend: 'polarising',
    themes: [
      {
        theme: 'rapid cascade in early adopters',
        weight: 0.6,
        evidence_step: 3,
      },
      {
        theme: 'resistance in skeptics',
        weight: 0.4,
        evidence_step: 7,
      },
    ],
    divisions: [
      {
        faction: 'early_adopters',
        share: 0.42,
        concerns: ['value'],
      },
      {
        faction: 'skeptics',
        share: 0.28,
        concerns: ['trust'],
      },
    ],
    dominant_emotions: ['excitement', 'skepticism'],
    key_quotes: [],
    source_step_count: 10,
    source_agent_count: 300,
    llm_provider: 'ollama',
    llm_model: 'llama3.2:1b',
    is_fallback_stub: false,
  },
  communities: [
    MOCK_COMMUNITY,
    {
      ...MOCK_COMMUNITY,
      opinion_id: 'op-c2',
      community_id: 'skeptics',
      summary: 'Skeptics pushed back against pricing and trust.',
      sentiment_trend: 'stable',
      dominant_emotions: ['skepticism'],
    },
  ],
};

beforeEach(() => {
  mutationState.mutate = vi.fn();
  mutationState.data = undefined;
  mutationState.isPending = false;
  mutationState.isError = false;
  mutationState.error = null;
});

describe('OverallOpinionPanel', () => {
  it('renders idle state with call-to-action button', () => {
    render(<OverallOpinionPanel simulationId="sim-1" />);
    expect(screen.getByText(/Whole-Simulation Narrative/)).toBeInTheDocument();
    expect(
      screen.getByRole('button', { name: /Synthesise Whole Simulation/ }),
    ).toBeEnabled();
  });

  it('invokes the mutation with no arguments when clicked', () => {
    render(<OverallOpinionPanel simulationId="sim-1" />);
    fireEvent.click(
      screen.getByRole('button', { name: /Synthesise Whole Simulation/ }),
    );
    expect(mutationState.mutate).toHaveBeenCalledTimes(1);
  });

  it('disables the button while synthesising', () => {
    mutationState.isPending = true;
    render(<OverallOpinionPanel simulationId="sim-1" />);
    expect(
      screen.getByRole('button', { name: /Synthesising/ }),
    ).toBeDisabled();
  });

  it('renders headline narrative, themes, divisions on success', () => {
    mutationState.data = MOCK_OVERALL;
    render(<OverallOpinionPanel simulationId="sim-1" />);
    expect(
      screen.getByText(/Early adopters drove a rapid cascade/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Polarising/)).toBeInTheDocument();
    expect(
      screen.getByText('rapid cascade in early adopters'),
    ).toBeInTheDocument();
    // 'early_adopters' appears both in the divisions list and in the
    // per-community card — at least one match is enough to prove
    // rendering worked.
    expect(screen.getAllByText('early_adopters').length).toBeGreaterThanOrEqual(
      1,
    );
  });

  it('renders per-community breakdown section with cards', () => {
    mutationState.data = MOCK_OVERALL;
    render(<OverallOpinionPanel simulationId="sim-1" />);
    expect(screen.getByText(/Per-Community Breakdown \(2\)/)).toBeInTheDocument();
    expect(
      screen.getByText(/Early adopters embraced the campaign/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Skeptics pushed back against pricing/),
    ).toBeInTheDocument();
  });

  it('shows fallback stub warning when is_fallback_stub is true', () => {
    mutationState.data = {
      ...MOCK_OVERALL,
      overall: { ...MOCK_OVERALL.overall, is_fallback_stub: true },
    };
    render(<OverallOpinionPanel simulationId="sim-1" />);
    expect(
      screen.getByText(/every configured LLM adapter failed/),
    ).toBeInTheDocument();
  });

  it('renders error message when mutation fails', () => {
    mutationState.isError = true;
    mutationState.error = new Error('backend unreachable');
    render(<OverallOpinionPanel simulationId="sim-1" />);
    expect(screen.getByText(/Synthesis failed/)).toBeInTheDocument();
    expect(screen.getByText(/backend unreachable/)).toBeInTheDocument();
  });

  it('disables button when simulationId is null', () => {
    render(<OverallOpinionPanel simulationId={null} />);
    expect(
      screen.getByRole('button', { name: /Synthesise Whole Simulation/ }),
    ).toBeDisabled();
  });
});
