/**
 * Test contract for AnalyticsPage.
 * SPEC: docs/spec/26_ANALYTICS_SPEC.md (as-built, v0.1.0)
 * Legacy:  docs/spec/07_FRONTEND_SPEC.md#simulationsidanalytics (IP-protected)
 *
 * The section-anchor comments below (`#analytics-layout` etc.) resolve to
 * headings in 26_ANALYTICS_SPEC.md §3–§5. Keep them in sync when the SPEC
 * changes.
 *
 * @spec docs/spec/26_ANALYTICS_SPEC.md
 */
import { render, screen, waitFor, within, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

const mockGetSteps = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    simulations: {
      getSteps: (...args: unknown[]) => mockGetSteps(...args),
    },
  },
}));

// Recharts uses ResizeObserver — provide a stub for jsdom
global.ResizeObserver = class {
  observe() {}
  unobserve() {}
  disconnect() {}
};

import AnalyticsPage from '@/pages/AnalyticsPage';
import { useSimulationStore } from '@/store/simulationStore';

const MOCK_SIMULATION = {
  simulation_id: 'sim-42',
  name: 'Test Analytics Sim',
  status: 'completed',
  config: {},
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
};

/**
 * Primary fixture. Enriched with diffusion_rate + total_adoption so the
 * Cascade Analytics (§4.6) derivation has real inputs:
 *   longestRun  = 2  (both steps have diffusion_rate > 0)
 *   peakDelta   = 300 (step 2 total_adoption - step 1 = 400 - 100)
 *   cascadeEvt  = 1  (viral_cascade in step 2)
 *   peakRate    = 0.20, latestRate = 0.20 → decay = 0.00
 */
const MOCK_STEPS = [
  {
    step: 1,
    adoption_rate: 0.1,
    mean_sentiment: 0.2,
    total_adoption: 100,
    diffusion_rate: 0.05,
    community_metrics: {
      alpha: { adoption_rate: 0.15, mean_sentiment: 0.3 },
      beta: { adoption_rate: 0.05, mean_sentiment: 0.1 },
    },
    emergent_events: [],
  },
  {
    step: 2,
    adoption_rate: 0.4,
    mean_sentiment: 0.5,
    total_adoption: 400,
    diffusion_rate: 0.20,
    community_metrics: {
      alpha: { adoption_rate: 0.5, mean_sentiment: 0.6 },
      beta: { adoption_rate: 0.3, mean_sentiment: 0.4 },
    },
    emergent_events: [
      {
        event_type: 'viral_cascade',
        step: 2,
        community_id: 'alpha',
        severity: 0.8,
        description: 'Rapid spread detected',
      },
    ],
  },
];

/**
 * Multi-event fixture for the v0.2.0 filter toolbar tests.
 * Two distinct event types so toggling filters produces observable changes.
 */
const MOCK_STEPS_MULTI_EVENT = [
  {
    step: 1,
    adoption_rate: 0.1,
    mean_sentiment: 0.2,
    total_adoption: 100,
    diffusion_rate: 0.05,
    community_metrics: {
      alpha: { adoption_rate: 0.15, mean_sentiment: 0.3 },
      beta: { adoption_rate: 0.05, mean_sentiment: 0.1 },
    },
    emergent_events: [],
  },
  {
    step: 2,
    adoption_rate: 0.4,
    mean_sentiment: 0.5,
    total_adoption: 400,
    diffusion_rate: 0.20,
    community_metrics: {
      alpha: { adoption_rate: 0.5, mean_sentiment: 0.6 },
      beta: { adoption_rate: 0.3, mean_sentiment: 0.4 },
    },
    emergent_events: [
      {
        event_type: 'viral_cascade',
        step: 2,
        community_id: 'alpha',
        severity: 0.8,
        description: 'Rapid spread detected',
      },
      {
        event_type: 'polarization',
        step: 2,
        community_id: 'beta',
        severity: 0.6,
        description: 'Population splitting into camps',
      },
    ],
  },
];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/analytics']}>
      <AnalyticsPage />
    </MemoryRouter>,
  );
}

describe('AnalyticsPage (26_ANALYTICS_SPEC)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
    // Reset store state
    useSimulationStore.setState({ simulation: null, steps: [] });
    mockGetSteps.mockResolvedValue([]);
  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-layout */
  describe('Layout', () => {
    it('renders the page with data-testid', () => {
      renderPage();
      expect(screen.getByTestId('analytics-page')).toBeInTheDocument();
    });

    it('renders the Post-Run Analytics header', () => {
      renderPage();
      expect(screen.getByRole('heading', { name: 'Post-Run Analytics' })).toBeInTheDocument();
    });

    it('renders a back button with aria-label', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /go back/i })).toBeInTheDocument();
    });

    it('clicking back button calls navigate(-1)', () => {
      renderPage();
      screen.getByRole('button', { name: /go back/i }).click();
      expect(mockNavigate).toHaveBeenCalledWith(-1);
    });
  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-empty-states */
  describe('Empty / No-Simulation State', () => {
    it('shows no-simulation message when store has no simulation', () => {
      renderPage();
      expect(
        screen.getByText(/No active simulation/i),
      ).toBeInTheDocument();
    });

    it('shows Go to Projects button when no simulation', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /go to projects/i })).toBeInTheDocument();
    });

    it('navigates to /projects when Go to Projects clicked', () => {
      renderPage();
      screen.getByRole('button', { name: /go to projects/i }).click();
      expect(mockNavigate).toHaveBeenCalledWith('/projects');
    });
  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-simulation-name */
  describe('Simulation Name Display', () => {
    it('shows simulation name in header when simulation exists', () => {
      useSimulationStore.setState({ simulation: MOCK_SIMULATION as any, steps: [] });
      renderPage();
      expect(screen.getByText('Test Analytics Sim')).toBeInTheDocument();
    });
  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-fetch */
  describe('Step Fetching', () => {
    it('calls getSteps when simulation is set but store has no steps', async () => {
      useSimulationStore.setState({ simulation: MOCK_SIMULATION as any, steps: [] });
      mockGetSteps.mockResolvedValue([]);
      renderPage();
      await waitFor(() => expect(mockGetSteps).toHaveBeenCalledWith('sim-42'));
    });

    it('does NOT call getSteps when store already has steps', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      // Give any potential async work time to run
      await waitFor(() => expect(mockGetSteps).not.toHaveBeenCalled());
    });

    it('shows loading state while fetching', async () => {
      useSimulationStore.setState({ simulation: MOCK_SIMULATION as any, steps: [] });
      // Return a never-resolving promise to keep loading state
      mockGetSteps.mockReturnValue(new Promise(() => {}));
      renderPage();
      await waitFor(() =>
        expect(screen.getByText(/loading analytics/i)).toBeInTheDocument(),
      );
    });

    it('shows error message when fetch fails', async () => {
      useSimulationStore.setState({ simulation: MOCK_SIMULATION as any, steps: [] });
      mockGetSteps.mockRejectedValue(new Error('Network error'));
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Network error')).toBeInTheDocument(),
      );
    });

    it('shows empty-steps message when fetch returns empty array', async () => {
      useSimulationStore.setState({ simulation: MOCK_SIMULATION as any, steps: [] });
      mockGetSteps.mockResolvedValue([]);
      renderPage();
      await waitFor(() =>
        expect(
          screen.getByText(/No step data available yet/i),
        ).toBeInTheDocument(),
      );
    });
  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-summary-cards */
  describe('Summary Cards', () => {
    it('renders Total Steps card', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() => expect(screen.getByText('Total Steps')).toBeInTheDocument());
    });

    it('renders Final Adoption card', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() => expect(screen.getByText('Final Adoption')).toBeInTheDocument());
    });

    it('renders Final Sentiment card', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() => expect(screen.getByText('Final Sentiment')).toBeInTheDocument());
    });

    it('renders Emergent Events card', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() => expect(screen.getByText('Emergent Events')).toBeInTheDocument());
    });

    it('shows correct final adoption percentage', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      // Last step adoption_rate=0.4 → 40.0%
      await waitFor(() => expect(screen.getByText('40.0%')).toBeInTheDocument());
    });

    /**
     * SPEC 26 §4.1 — Total Steps card value = `steps[last].step`.
     * Scoped with within() because bare "2" appears elsewhere (Step 2 event row,
     * chart axis, etc.).
     */
    it('Total Steps card shows the final step number', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      const label = await screen.findByText('Total Steps');
      const card = label.closest('div')!;
      expect(within(card).getByText('2')).toBeInTheDocument();
    });

    /** SPEC 26 §4.1 — Final Sentiment uses toFixed(3); 0.5 → "0.500". */
    it('Final Sentiment card shows value with 3-decimal formatting', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('0.500')).toBeInTheDocument(),
      );
    });

    /**
     * SPEC 26 §4.1 — Emergent Events card value = deduped count from
     * collectEmergentEvents(). MOCK_STEPS has exactly one event.
     */
    it('Emergent Events card shows deduped event count', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      const label = await screen.findByText('Emergent Events');
      const card = label.closest('div')!;
      expect(within(card).getByText('1')).toBeInTheDocument();
    });
  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-charts */
  describe('Chart Sections', () => {
    it('renders Adoption Rate Over Time section', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('heading', { name: 'Adoption Rate Over Time' })).toBeInTheDocument(),
      );
    });

    it('renders Mean Sentiment Over Time section', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('heading', { name: 'Mean Sentiment Over Time' })).toBeInTheDocument(),
      );
    });

    it('renders Community Adoption Comparison section', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('heading', { name: /Community Adoption Comparison/i })).toBeInTheDocument(),
      );
    });

    /**
     * SPEC 26 §4.2 — when any emergent event exists, the adoption chart must
     * render the caption explaining the dashed ReferenceLine markers.
     * MOCK_STEPS has one viral_cascade event, so the caption MUST be visible.
     */
    it('shows the dashed-line caption when emergent events exist', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(
          screen.getByText(/Dashed vertical lines indicate emergent events/i),
        ).toBeInTheDocument(),
      );
    });

    /**
     * SPEC 26 §4.2 — the caption is conditional on eventSteps.length > 0.
     * With events stripped, the caption MUST NOT render.
     */
    it('does NOT show the dashed-line caption when no emergent events', async () => {
      const stepsNoEvents = MOCK_STEPS.map((s) => ({ ...s, emergent_events: [] }));
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: stepsNoEvents as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('heading', { name: 'Adoption Rate Over Time' })).toBeInTheDocument(),
      );
      expect(
        screen.queryByText(/Dashed vertical lines indicate emergent events/i),
      ).not.toBeInTheDocument();
    });

  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-emergent-events */
  describe('Emergent Event Timeline', () => {
    it('renders Emergent Event Timeline section heading', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('heading', { name: 'Emergent Event Timeline' })).toBeInTheDocument(),
      );
    });

    it('shows emergent event type when events exist', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      // Since v0.2.0 the filter chip ALSO renders "viral cascade" text, so
      // assert the type appears inside the row specifically (anchored via
      // the description).
      const description = await screen.findByText('Rapid spread detected');
      const row = description.closest('[role="button"]') as HTMLElement | null;
      expect(row).not.toBeNull();
      expect(within(row!).getByText('viral cascade')).toBeInTheDocument();
    });

    it('shows event description', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Rapid spread detected')).toBeInTheDocument(),
      );
    });

    /**
     * SPEC 26 §4.5 — severity renders as `sev {toFixed(2)}`.
     * MOCK event has severity 0.8 → "sev 0.80".
     */
    it('shows severity formatted to 2 decimals', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('sev 0.80')).toBeInTheDocument(),
      );
    });

    /**
     * SPEC 26 §4.5 — community_id pill renders on an event row when set.
     * The chart legend also contains "alpha", so use within() scoped to the
     * event row (description anchors us to the row, pill is its sibling).
     */
    it('shows the community_id pill on the event row', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      const description = await screen.findByText('Rapid spread detected');
      // Walk up to the event row container (the px-4 py-3 flex row)
      const row = description.closest('div.flex.items-start') as HTMLElement | null;
      expect(row).not.toBeNull();
      expect(within(row!).getByText('alpha')).toBeInTheDocument();
    });

    /** SPEC 26 §4.5 — "Step {n}" prefix on event rows. */
    it('shows the "Step N" prefix on event rows', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Step 2')).toBeInTheDocument(),
      );
    });

    it('shows no-events message when steps have no emergent events', async () => {
      const stepsNoEvents = MOCK_STEPS.map((s) => ({ ...s, emergent_events: [] }));
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: stepsNoEvents as any,
      });
      renderPage();
      await waitFor(() =>
        expect(
          screen.getByText(/No emergent events detected/i),
        ).toBeInTheDocument(),
      );
    });
  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-emergent-events (v0.2.0 deep link) */
  describe('Event Row Deep Link (v0.2.0)', () => {
    it('event row exposes role=button with descriptive aria-label', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(
          screen.getByRole('button', { name: /view step 2 in simulation/i }),
        ).toBeInTheDocument(),
      );
    });

    it('clicking an event row navigates to /simulation/{id}?step={n}', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      const row = await screen.findByRole('button', {
        name: /view step 2 in simulation/i,
      });
      fireEvent.click(row);
      expect(mockNavigate).toHaveBeenCalledWith('/simulation/sim-42?step=2');
    });

    it('pressing Enter on an event row navigates as well', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      const row = await screen.findByRole('button', {
        name: /view step 2 in simulation/i,
      });
      fireEvent.keyDown(row, { key: 'Enter' });
      expect(mockNavigate).toHaveBeenCalledWith('/simulation/sim-42?step=2');
    });

    it('pressing Space on an event row navigates as well', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      const row = await screen.findByRole('button', {
        name: /view step 2 in simulation/i,
      });
      fireEvent.keyDown(row, { key: ' ' });
      expect(mockNavigate).toHaveBeenCalledWith('/simulation/sim-42?step=2');
    });
  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-emergent-events (v0.2.0 filter toolbar) */
  describe('Event Filter Toolbar (v0.2.0)', () => {
    it('renders an "All" filter chip by default pressed when events exist', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS_MULTI_EVENT as any,
      });
      renderPage();
      const allChip = await screen.findByTestId('event-filter-all');
      expect(allChip).toHaveAttribute('aria-pressed', 'true');
    });

    it('renders one type-specific chip per event type present', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS_MULTI_EVENT as any,
      });
      renderPage();
      await waitFor(() => {
        expect(screen.getByTestId('event-filter-viral_cascade')).toBeInTheDocument();
        expect(screen.getByTestId('event-filter-polarization')).toBeInTheDocument();
      });
    });

    it('does NOT render the filter toolbar when there are no events', async () => {
      const stepsNoEvents = MOCK_STEPS.map((s) => ({ ...s, emergent_events: [] }));
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: stepsNoEvents as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText(/No emergent events detected/i)).toBeInTheDocument(),
      );
      expect(screen.queryByTestId('event-filter-all')).not.toBeInTheDocument();
    });

    it('clicking a type chip hides events of other types', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS_MULTI_EVENT as any,
      });
      renderPage();
      // Sanity — both events visible at start
      await waitFor(() =>
        expect(screen.getByText('Rapid spread detected')).toBeInTheDocument(),
      );
      expect(screen.getByText('Population splitting into camps')).toBeInTheDocument();

      // Click the polarization chip
      fireEvent.click(screen.getByTestId('event-filter-polarization'));

      // Viral cascade row should be gone, polarization still there
      expect(screen.queryByText('Rapid spread detected')).not.toBeInTheDocument();
      expect(screen.getByText('Population splitting into camps')).toBeInTheDocument();
    });

    it('clicking "All" after a filter restores every event', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS_MULTI_EVENT as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Rapid spread detected')).toBeInTheDocument(),
      );
      fireEvent.click(screen.getByTestId('event-filter-polarization'));
      expect(screen.queryByText('Rapid spread detected')).not.toBeInTheDocument();
      fireEvent.click(screen.getByTestId('event-filter-all'));
      expect(screen.getByText('Rapid spread detected')).toBeInTheDocument();
      expect(screen.getByText('Population splitting into camps')).toBeInTheDocument();
    });

    it('filter narrows list only — Summary Card count stays based on all events', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS_MULTI_EVENT as any,
      });
      renderPage();
      const label = await screen.findByText('Emergent Events');
      const card = label.closest('div')!;
      // Unfiltered: 2 events
      expect(within(card).getByText('2')).toBeInTheDocument();
      // Filter to just polarization
      fireEvent.click(screen.getByTestId('event-filter-polarization'));
      // Summary card must NOT change
      expect(within(card).getByText('2')).toBeInTheDocument();
    });
  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-cascade (v0.2.0) */
  describe('Cascade Analytics (v0.2.0)', () => {
    it('renders the Cascade Analytics section title', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('heading', { name: 'Cascade Analytics' })).toBeInTheDocument(),
      );
    });

    it('renders Longest Cascade Run with value from buildCascadeStats', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      const card = await screen.findByTestId('cascade-depth');
      expect(within(card).getByText(/longest cascade run/i)).toBeInTheDocument();
      // Both steps have diffusion_rate > 0 → longestRun = 2
      expect(within(card).getByText('2')).toBeInTheDocument();
    });

    it('renders Peak Adoption Delta with value from buildCascadeStats', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      const card = await screen.findByTestId('cascade-width');
      expect(within(card).getByText(/peak adoption delta/i)).toBeInTheDocument();
      // peakDelta = max(100 - 0, 400 - 100) = 300
      expect(within(card).getByText('300')).toBeInTheDocument();
    });

    it('renders Viral/Cascade Events count', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      const card = await screen.findByTestId('cascade-paths');
      expect(within(card).getByText(/viral.*cascade events/i)).toBeInTheDocument();
      expect(within(card).getByText('1')).toBeInTheDocument();
    });

    it('renders Decay Rate with /step suffix', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      const card = await screen.findByTestId('cascade-decay');
      expect(within(card).getByText(/decay rate/i)).toBeInTheDocument();
      // peakRate = 0.20, latestRate = 0.20 → decay = 0.00
      expect(within(card).getByText('0.00/step')).toBeInTheDocument();
    });
  });

  /** @spec 26_ANALYTICS_SPEC.md#analytics-a11y (v0.2.0 chart a11y) */
  describe('Chart a11y (v0.2.0)', () => {
    it('wraps the adoption rate chart with role="img" + aria-label', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(
          screen.getByRole('img', { name: /adoption rate over time/i }),
        ).toBeInTheDocument(),
      );
    });

    it('wraps the sentiment chart with role="img" + aria-label', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(
          screen.getByRole('img', { name: /mean sentiment over time/i }),
        ).toBeInTheDocument(),
      );
    });

    it('wraps the community comparison chart with role="img" + aria-label', async () => {
      useSimulationStore.setState({
        simulation: MOCK_SIMULATION as any,
        steps: MOCK_STEPS as any,
      });
      renderPage();
      await waitFor(() =>
        expect(
          screen.getByRole('img', { name: /community adoption comparison/i }),
        ).toBeInTheDocument(),
      );
    });
  });
});
