/**
 * SimulationReportModal regression tests.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#simulation-report
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => vi.fn() };
});

vi.mock('../api/client', () => ({
  apiClient: { simulations: { export: vi.fn() } },
}));

// Store mock — seeded per-test with steps fixture.
let mockSteps: unknown[] = [];
vi.mock('../store/simulationStore', () => ({
  useSimulationStore: (selector: (s: unknown) => unknown) =>
    selector({
      simulation: { simulation_id: 'test-sim' },
      steps: mockSteps,
    }),
}));

import SimulationReportModal from '@/components/shared/SimulationReportModal';

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return (
    <QueryClientProvider client={qc}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

function makeStep(step: number, events: Array<{ event_type: string; description: string }> = []) {
  return {
    step,
    adoption_rate: step / 50,
    mean_sentiment: 0,
    diffusion_rate: 0,
    sentiment_variance: 0,
    total_adoption: 0,
    community_metrics: {},
    action_distribution: {},
    llm_calls_this_step: 0,
    step_duration_ms: 0,
    emergent_events: events,
  };
}

describe('SimulationReportModal Key Events', () => {
  beforeEach(() => {
    mockSteps = [];
  });

  it('renders ALL emergent events, not just the first 5 (regression: prior 5-cap hid 90%+ of the timeline)', () => {
    // Seed 12 events across 4 steps.
    mockSteps = [
      makeStep(1, [
        { event_type: 'viral_cascade', description: 'Cascade A' },
        { event_type: 'polarization', description: 'Pol A' },
        { event_type: 'consensus', description: 'Con A' },
      ]),
      makeStep(2, [
        { event_type: 'viral_cascade', description: 'Cascade B' },
        { event_type: 'polarization', description: 'Pol B' },
        { event_type: 'consensus', description: 'Con B' },
      ]),
      makeStep(3, [
        { event_type: 'viral_cascade', description: 'Cascade C' },
        { event_type: 'polarization', description: 'Pol C' },
        { event_type: 'consensus', description: 'Con C' },
      ]),
      makeStep(4, [
        { event_type: 'viral_cascade', description: 'Cascade D' },
        { event_type: 'polarization', description: 'Pol D' },
        { event_type: 'consensus', description: 'Con D' },
      ]),
    ];
    render(wrap(<SimulationReportModal onClose={() => {}} />));
    // Every description visible — including items that would have been
    // trimmed by the old 5-cap (Con B onward).
    expect(screen.getByText('Cascade A')).toBeInTheDocument();
    expect(screen.getByText('Con B')).toBeInTheDocument();
    expect(screen.getByText('Cascade C')).toBeInTheDocument();
    expect(screen.getByText('Con D')).toBeInTheDocument();
    // Count in header label
    expect(screen.getByText('(12)')).toBeInTheDocument();
  });

  it('key-events-list is a scrollable container (regression: section used to push siblings)', () => {
    mockSteps = [makeStep(1, [{ event_type: 'viral_cascade', description: 'x' }])];
    render(wrap(<SimulationReportModal onClose={() => {}} />));
    const list = screen.getByTestId('key-events-list');
    expect(list.className).toMatch(/overflow-y-auto/);
    expect(list.className).toMatch(/max-h-/);
  });

  it('long descriptions are not clamped to one line (regression: line-clamp-1 hid content)', () => {
    const longDesc = 'A '.repeat(80).trim();
    mockSteps = [makeStep(1, [{ event_type: 'viral_cascade', description: longDesc }])];
    render(wrap(<SimulationReportModal onClose={() => {}} />));
    const desc = screen.getByText(longDesc);
    expect(desc.className).not.toMatch(/line-clamp-/);
    expect(desc.className).toMatch(/break-words/);
  });

  it('hides Key Events section entirely when there are no events', () => {
    mockSteps = [makeStep(1, [])];
    render(wrap(<SimulationReportModal onClose={() => {}} />));
    expect(screen.queryByTestId('key-events-list')).not.toBeInTheDocument();
  });
});
