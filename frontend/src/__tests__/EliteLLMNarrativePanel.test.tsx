/**
 * Tests for EliteLLMNarrativePanel.
 *
 * @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis
 *
 * The panel has four visual states:
 *   1. Idle  — "Synthesise with EliteLLM" button, no narrative
 *   2. Pending — "Synthesising…" (button disabled)
 *   3. Success — narrative body rendered
 *   4. Error   — error message, button re-enabled
 *
 * The panel uses ``useCommunityOpinionSynthesis`` from ``@/api/queries``,
 * which we mock below. A shared ``mutationState`` object is mutated per
 * test so each ``render()`` picks up a different state without changing
 * the mock module itself.
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, beforeEach, vi } from 'vitest';
import EliteLLMNarrativePanel from '@/components/community/EliteLLMNarrativePanel';
import type { CommunityOpinion } from '@/types/api';

type MutationState = {
  mutate: ReturnType<typeof vi.fn>;
  data: CommunityOpinion | undefined;
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
  useCommunityOpinionSynthesis: () => mutationState,
}));

const MOCK_OPINION: CommunityOpinion = {
  opinion_id: 'op-1',
  simulation_id: 'sim-1',
  community_id: 'alpha',
  step: 5,
  summary: 'Community is polarising around the sustainability campaign.',
  sentiment_trend: 'polarising',
  themes: [
    { theme: 'rapid early adoption', weight: 0.6, evidence_step: 2 },
    { theme: 'resistance from long-time members', weight: 0.4, evidence_step: 4 },
  ],
  divisions: [
    { faction: 'enthusiasts', share: 0.55, concerns: ['value', 'convenience'] },
    { faction: 'holdouts', share: 0.45, concerns: ['trust'] },
  ],
  dominant_emotions: ['excitement', 'skepticism'],
  key_quotes: [
    {
      agent_id: 'abcdef1234567890',
      content: 'Finally a brand that gets it.',
      step: 3,
    },
  ],
  source_step_count: 5,
  source_agent_count: 80,
  llm_provider: 'ollama',
  llm_model: 'llama3.1:8b',
  is_fallback_stub: false,
};

beforeEach(() => {
  mutationState.mutate = vi.fn();
  mutationState.data = undefined;
  mutationState.isPending = false;
  mutationState.isError = false;
  mutationState.error = null;
});

describe('EliteLLMNarrativePanel', () => {
  it('renders idle state with call-to-action button', () => {
    render(<EliteLLMNarrativePanel simulationId="sim-1" communityId="alpha" />);
    expect(screen.getByText(/EliteLLM Opinion Narrative/)).toBeInTheDocument();
    const btn = screen.getByRole('button', { name: /Synthesise with EliteLLM/ });
    expect(btn).toBeEnabled();
  });

  it('calls the mutation with communityId when the button is clicked', () => {
    render(<EliteLLMNarrativePanel simulationId="sim-1" communityId="alpha" />);
    fireEvent.click(
      screen.getByRole('button', { name: /Synthesise with EliteLLM/ }),
    );
    expect(mutationState.mutate).toHaveBeenCalledWith('alpha');
  });

  it('disables the button while synthesising and shows pending label', () => {
    mutationState.isPending = true;
    render(<EliteLLMNarrativePanel simulationId="sim-1" communityId="alpha" />);
    const btn = screen.getByRole('button', { name: /Synthesising/ });
    expect(btn).toBeDisabled();
  });

  it('renders summary, themes, divisions, emotions, quotes on success', () => {
    mutationState.data = MOCK_OPINION;
    render(<EliteLLMNarrativePanel simulationId="sim-1" communityId="alpha" />);
    expect(
      screen.getByText(/Community is polarising around the sustainability campaign/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Polarising/)).toBeInTheDocument();
    expect(screen.getByText('rapid early adoption')).toBeInTheDocument();
    expect(screen.getByText('enthusiasts')).toBeInTheDocument();
    expect(screen.getByText('excitement')).toBeInTheDocument();
    expect(screen.getByText(/Finally a brand that gets it/)).toBeInTheDocument();
  });

  it('shows fallback warning when is_fallback_stub is true', () => {
    mutationState.data = { ...MOCK_OPINION, is_fallback_stub: true };
    render(<EliteLLMNarrativePanel simulationId="sim-1" communityId="alpha" />);
    expect(
      screen.getByText(/every configured LLM adapter failed/),
    ).toBeInTheDocument();
  });

  it('switches CTA label from "Synthesise" to "Refresh" after first success', () => {
    mutationState.data = MOCK_OPINION;
    render(<EliteLLMNarrativePanel simulationId="sim-1" communityId="alpha" />);
    expect(screen.getByRole('button', { name: /Refresh/ })).toBeInTheDocument();
  });

  it('renders error message when mutation fails', () => {
    mutationState.isError = true;
    mutationState.error = new Error('500 internal error');
    render(<EliteLLMNarrativePanel simulationId="sim-1" communityId="alpha" />);
    expect(screen.getByText(/Synthesis failed/)).toBeInTheDocument();
    expect(screen.getByText(/500 internal error/)).toBeInTheDocument();
  });

  it('disables button when simulationId or communityId is null', () => {
    render(<EliteLLMNarrativePanel simulationId={null} communityId="alpha" />);
    expect(
      screen.getByRole('button', { name: /Synthesise with EliteLLM/ }),
    ).toBeDisabled();
  });
});
