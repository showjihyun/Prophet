/**
 * Auto-generated from SPEC: docs/spec/ui/UI_01_SIMULATION_MAIN.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

vi.mock('cytoscape', () => ({
  default: vi.fn(() => ({
    on: vi.fn(),
    nodes: () => ({ length: 0, forEach: vi.fn() }),
    edges: () => ({ length: 0, forEach: vi.fn() }),
    zoom: vi.fn(() => 1),
    width: vi.fn(() => 800),
    height: vi.fn(() => 600),
    fit: vi.fn(),
    destroy: vi.fn(),
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

import SimulationPage from '@/pages/SimulationPage';

const renderPage = () =>
  render(
    <MemoryRouter>
      <SimulationPage />
    </MemoryRouter>,
  );

describe('SimulationMain (UI-01)', () => {
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
      expect(screen.getByText('Communities')).toBeInTheDocument();
    });

    it('renders 5 community items (Alpha, Beta, Gamma, Delta, Bridge)', () => {
      renderPage();
      expect(screen.getAllByText('Alpha').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Beta').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Gamma').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Delta').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Bridge').length).toBeGreaterThanOrEqual(1);
    });

    it('renders total agents count', () => {
      renderPage();
      expect(screen.getByText(/total.*agents/i)).toBeInTheDocument();
    });
  });

  /** @spec UI_01_SIMULATION_MAIN.md#zone-2-center-graph-engine */
  describe('Zone 2: AI Social World Graph Engine', () => {
    it('renders graph container with dark background', () => {
      renderPage();
      expect(screen.getByTestId('graph-panel')).toBeInTheDocument();
    });

    it('renders graph title overlay', () => {
      renderPage();
      expect(screen.getByText('AI Social World')).toBeInTheDocument();
    });

    it('renders zoom controls (+/-/maximize)', () => {
      renderPage();
      expect(screen.getByTestId('zoom-in-btn')).toBeInTheDocument();
      expect(screen.getByTestId('zoom-out-btn')).toBeInTheDocument();
      expect(screen.getByTestId('zoom-maximize-btn')).toBeInTheDocument();
    });

    it('renders network legend with community colors', () => {
      renderPage();
      expect(screen.getByTestId('network-legend')).toBeInTheDocument();
    });

    it('renders cascade badge', () => {
      renderPage();
      expect(screen.getByTestId('cascade-badge')).toBeInTheDocument();
    });

    it('renders status overlay with FPS and node/edge counts', () => {
      renderPage();
      expect(screen.getByTestId('status-overlay')).toBeInTheDocument();
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
});
