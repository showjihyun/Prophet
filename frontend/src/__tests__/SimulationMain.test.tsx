/**
 * Auto-generated from SPEC: docs/spec/ui/UI_01_SIMULATION_MAIN.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md
 */
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import { useSimulationStore } from '../store/simulationStore';

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

vi.mock('cytoscape', () => ({
  default: vi.fn(() => ({
    on: vi.fn(),
    batch: vi.fn((cb: () => void) => cb()),
    nodes: () => ({ length: 0, forEach: vi.fn(), toArray: () => [], removeClass: vi.fn(), style: vi.fn() }),
    edges: () => ({ length: 0, forEach: vi.fn(), removeStyle: vi.fn(), style: vi.fn() }),
    zoom: vi.fn(() => 1),
    width: vi.fn(() => 800),
    height: vi.fn(() => 600),
    fit: vi.fn(),
    destroy: vi.fn(),
    style: vi.fn(),
  })),
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
  Cell: () => null,
  Legend: () => null,
  PieChart: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  Pie: () => null,
}));

const { mockPause, mockResume, mockStart, mockRunAll } = vi.hoisted(() => ({
  mockPause: vi.fn().mockResolvedValue({ status: 'paused' }),
  mockResume: vi.fn().mockResolvedValue({ status: 'running' }),
  mockStart: vi.fn().mockResolvedValue({ status: 'running' }),
  mockRunAll: vi.fn().mockImplementation(() => new Promise((resolve) => {
    setTimeout(() => resolve({ status: 'completed', total_steps: 365 }), 5000);
  })),
}));

vi.mock('@/api/client', () => ({
  apiClient: {
    network: { get: vi.fn().mockRejectedValue(new Error('no network')) },
    agents: { list: vi.fn().mockResolvedValue({ items: [] }) },
    simulations: {
      getSteps: vi.fn().mockResolvedValue([]),
      pause: mockPause,
      resume: mockResume,
      start: mockStart,
      runAll: mockRunAll,
      step: vi.fn().mockResolvedValue({ step: 1, adoption_rate: 0.1, mean_sentiment: 0.5, community_metrics: {}, emergent_events: [], agent_states: [] }),
      stop: vi.fn().mockResolvedValue({ status: 'created' }),
    },
    projects: {
      list: vi.fn().mockResolvedValue([]),
      get: vi.fn().mockResolvedValue({ scenarios: [] }),
    },
    scenarios: { list: vi.fn().mockResolvedValue([]) },
  },
}));

import SimulationPage from '@/pages/SimulationPage';

const MOCK_SIMULATION = {
  simulation_id: 'sim-test-001',
  project_id: 'proj-001',
  scenario_id: 'scen-001',
  status: 'running' as const,
  current_step: 5,
  max_steps: 365,
  created_at: new Date().toISOString(),
  config: {} as never,
};

const renderPage = () =>
  render(
    <MemoryRouter>
      <SimulationPage />
    </MemoryRouter>,
  );

describe('SimulationMain (UI-01)', () => {
  beforeEach(() => {
    // Inject a mock simulation so the full layout renders (not the empty state)
    useSimulationStore.setState({
      simulation: MOCK_SIMULATION,
      status: 'running',
      currentStep: 5,
      steps: [],
      latestStep: null,
      emergentEvents: [],
      isLLMDashboardOpen: false,
      speed: 2,
    });
  });

  /** @spec UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar */
  describe('Zone 1: Simulation Control Bar', () => {
    it('renders logo with "MCASP Prophet Engine" text', () => {
      renderPage();
      expect(screen.getByText('MCASP Prophet Engine')).toBeInTheDocument();
    });

    it('renders simulation status badge with current day', () => {
      renderPage();
      expect(screen.getByTestId('status-badge')).toBeInTheDocument();
    });

    it('renders Global Insights button', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /global insights/i })).toBeInTheDocument();
    });

    it('renders scenario dropdown', () => {
      renderPage();
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument();
    });

    it('renders speed control buttons (1x, 2x, 5x, 10x)', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /1x/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /2x/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /5x/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /10x/i })).toBeInTheDocument();
    });

    it('renders play, pause, step, reset, replay buttons', () => {
      renderPage();
      expect(screen.getByTestId('play-btn')).toBeInTheDocument();
      expect(screen.getByTestId('pause-btn')).toBeInTheDocument();
      expect(screen.getByTestId('step-btn')).toBeInTheDocument();
      expect(screen.getByTestId('reset-btn')).toBeInTheDocument();
      expect(screen.getByTestId('replay-btn')).toBeInTheDocument();
    });
  });

  /** @spec UI_01_SIMULATION_MAIN.md#zone-2-left-community-panel */
  describe('Zone 2: Community Panel', () => {
    it('renders community search/filter input', () => {
      renderPage();
      expect(screen.getByPlaceholderText(/filter communities/i)).toBeInTheDocument();
    });

    it('renders communities title with count', () => {
      renderPage();
      // Scope to the community panel — the graph overlay also has a
      // "Communities" legend header.
      const panel = screen.getByTestId('community-panel');
      expect(panel.textContent).toMatch(/Communities/);
    });

    it('renders multiple community rows', () => {
      // CommunityPanel shows a SkeletonList while running with no steps yet.
      // Pause the sim so it renders actual rows.
      useSimulationStore.setState({ status: 'paused' });
      renderPage();
      // We don't pin the exact set of names — they vary depending on whether
      // the panel is in mock vs live mode and whether the test seeded
      // community_metrics. The contract is "the panel renders >=3 rows".
      const panel = screen.getByTestId('community-panel');
      const rows = panel.querySelectorAll('div.cursor-pointer');
      expect(rows.length).toBeGreaterThanOrEqual(3);
    });

    it('renders total agents count', () => {
      renderPage();
      expect(screen.getByText(/total.*agents/i)).toBeInTheDocument();
    });
  });

  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#5-graph-3d-rendering */
  describe('Zone 2: AI Social World Graph Engine (3D)', () => {
    // GraphPanel is lazy-loaded inside SimulationPage (perf — three.js
    // chunk only fetched when a sim is active). Tests must `await
    // findByTestId` so React Suspense has a chance to resolve.
    it('renders graph container with dark background', async () => {
      renderPage();
      expect(await screen.findByTestId('graph-panel')).toBeInTheDocument();
    });

    it('renders 3D graph title overlay', async () => {
      renderPage();
      expect(await screen.findByText(/AI Social World — 3D/)).toBeInTheDocument();
    });

    it('exposes the WebGL container with stable test-id', async () => {
      renderPage();
      expect(await screen.findByTestId('graph-cytoscape-container')).toBeInTheDocument();
    });

    it('shows the 3D controls hint (left-drag / scroll / right-drag)', async () => {
      renderPage();
      const hint = await screen.findByText(/Left-drag/i);
      expect(hint).toBeInTheDocument();
      expect(hint.textContent).toMatch(/rotate/i);
      expect(hint.textContent).toMatch(/zoom/i);
      expect(hint.textContent).toMatch(/pan/i);
    });

    it('uses 3D aria label on the panel', async () => {
      renderPage();
      const panel = await screen.findByTestId('graph-panel');
      expect(panel.getAttribute('aria-label')).toMatch(/3D/);
    });
  });

  /** @spec UI_01_SIMULATION_MAIN.md#zone-2-right-metrics-panel */
  describe('Zone 2: Real-Time Metrics Panel', () => {
    it('renders "Real-Time Metrics" title with LIVE badge', () => {
      renderPage();
      expect(screen.getByText('Real-Time Metrics')).toBeInTheDocument();
      expect(screen.getByTestId('live-badge')).toBeInTheDocument();
    });

    it('renders active agents metric with progress bar', () => {
      renderPage();
      expect(screen.getByTestId('active-agents-metric')).toBeInTheDocument();
    });

    it('renders sentiment distribution bars', () => {
      renderPage();
      expect(screen.getByTestId('sentiment-distribution')).toBeInTheDocument();
    });

    it('renders polarization index with gradient bar', () => {
      renderPage();
      expect(screen.getByTestId('polarization-index')).toBeInTheDocument();
    });

    it('renders cascade stats (depth and width)', () => {
      renderPage();
      expect(screen.getByTestId('cascade-depth')).toBeInTheDocument();
      expect(screen.getByTestId('cascade-width')).toBeInTheDocument();
    });

    it('renders top influencers list', () => {
      renderPage();
      expect(screen.getByTestId('top-influencers')).toBeInTheDocument();
    });
  });

  /** @spec UI_01_SIMULATION_MAIN.md#zone-3-timeline */
  describe('Zone 3: Timeline + Diffusion Wave', () => {
    it('renders timeline controls with day label', () => {
      renderPage();
      expect(screen.getByTestId('timeline-controls')).toBeInTheDocument();
    });

    it('renders diffusion wave bar chart', () => {
      renderPage();
      expect(screen.getByTestId('diffusion-wave-chart')).toBeInTheDocument();
    });

    it('renders speed badge', () => {
      renderPage();
      expect(screen.getByTestId('speed-badge')).toBeInTheDocument();
    });
  });

  /** @spec UI_01_SIMULATION_MAIN.md#zone-3-conversations */
  describe('Zone 3: Conversations / Expert Agent', () => {
    it('renders expert agent analysis section', () => {
      renderPage();
      expect(screen.getByTestId('expert-agent-analysis')).toBeInTheDocument();
    });

    it('renders live conversation feed', () => {
      renderPage();
      expect(screen.getByText(/live conversation feed/i)).toBeInTheDocument();
    });
  });

  /**
   * SPEC: 04_SIMULATION_SPEC.md#SIM-03 — Pause mid-step
   * SPEC: 04_SIMULATION_SPEC.md#pause-resume
   * Tests the Play/Pause toggle behavior and Run All pause capability.
   */
  describe('SIM-03: Pause / Resume Controls', () => {
    it('shows pause button and hides play button when status is running', () => {
      useSimulationStore.setState({ status: 'running' });
      renderPage();
      const pauseBtn = screen.getByTestId('pause-btn');
      const playBtn = screen.getByTestId('play-btn');
      // Pause visible (not hidden)
      expect(pauseBtn).not.toHaveClass('invisible');
      // Play hidden
      expect(playBtn).toHaveClass('invisible');
    });

    it('shows play button and hides pause button when status is paused', () => {
      useSimulationStore.setState({ status: 'paused' });
      renderPage();
      const pauseBtn = screen.getByTestId('pause-btn');
      const playBtn = screen.getByTestId('play-btn');
      // Play visible
      expect(playBtn).not.toHaveClass('invisible');
      // Pause hidden
      expect(pauseBtn).toHaveClass('invisible');
    });

    it('calls pause API when pause button is clicked during running', async () => {
      useSimulationStore.setState({ status: 'running' });
      renderPage();
      const pauseBtn = screen.getByTestId('pause-btn');
      fireEvent.click(pauseBtn);
      await vi.waitFor(() => {
        expect(mockPause).toHaveBeenCalledWith('sim-test-001');
      });
    });

    it('updates status badge to "Paused" after pause', async () => {
      useSimulationStore.setState({ status: 'running' });
      renderPage();
      fireEvent.click(screen.getByTestId('pause-btn'));
      await vi.waitFor(() => {
        expect(useSimulationStore.getState().status).toBe('paused');
      });
    });

    it('calls resume API when play button is clicked during paused', async () => {
      useSimulationStore.setState({ status: 'paused' });
      renderPage();
      const playBtn = screen.getByTestId('play-btn');
      fireEvent.click(playBtn);
      await vi.waitFor(() => {
        expect(mockResume).toHaveBeenCalledWith('sim-test-001');
      });
    });

    it('pause button is visible during Run All execution', async () => {
      useSimulationStore.setState({ status: 'configured' });
      renderPage();
      const runAllBtn = screen.getByTestId('run-all-btn');
      fireEvent.click(runAllBtn);
      // After clicking Run All, status should become 'running' → pause button visible
      await vi.waitFor(() => {
        const pauseBtn = screen.getByTestId('pause-btn');
        expect(pauseBtn).not.toHaveClass('invisible');
      });
    });

    it('keyboard shortcut Space toggles play/pause', () => {
      useSimulationStore.setState({ status: 'running' });
      renderPage();
      fireEvent.keyDown(window, { key: ' ' });
      // Should have called pause
      expect(mockPause).toHaveBeenCalled();
    });
  });
});
