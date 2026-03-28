/**
 * Auto-generated from SPEC: docs/spec/ui/UI_01_SIMULATION_MAIN.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';

describe('SimulationMain (UI-01)', () => {
  /** @spec UI_01_SIMULATION_MAIN.md#zone-1-simulation-control-bar */
  describe('Zone 1: Simulation Control Bar', () => {
    it('renders logo with "MCASP Prophet Engine" text', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByText('MCASP Prophet Engine')).toBeInTheDocument();
    });

    it('renders simulation status badge with current day', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('status-badge')).toBeInTheDocument();
    });

    it('renders Global Insights button', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByRole('button', { name: /global insights/i })).toBeInTheDocument();
    });

    it('renders scenario dropdown', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('scenario-select')).toBeInTheDocument();
    });

    it('renders speed control buttons (1x, 2x, 5x, 10x)', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByRole('button', { name: /1x/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /2x/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /5x/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /10x/i })).toBeInTheDocument();
    });

    it('renders play, pause, step, reset, replay buttons', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
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
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByPlaceholderText(/filter communities/i)).toBeInTheDocument();
    });

    it('renders communities title with count', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByText('Communities')).toBeInTheDocument();
    });

    it('renders 5 community items (Alpha, Beta, Gamma, Delta, Bridge)', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByText('Alpha')).toBeInTheDocument();
      expect(screen.getByText('Beta')).toBeInTheDocument();
      expect(screen.getByText('Gamma')).toBeInTheDocument();
      expect(screen.getByText('Delta')).toBeInTheDocument();
      expect(screen.getByText('Bridge')).toBeInTheDocument();
    });

    it('renders total agents count', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByText(/total.*agents/i)).toBeInTheDocument();
    });
  });

  /** @spec UI_01_SIMULATION_MAIN.md#zone-2-center-graph-engine */
  describe('Zone 2: AI Social World Graph Engine', () => {
    it('renders graph container with dark background', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('graph-panel')).toBeInTheDocument();
    });

    it('renders graph title overlay', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByText('AI Social World')).toBeInTheDocument();
    });

    it('renders zoom controls (+/-/maximize)', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('zoom-in-btn')).toBeInTheDocument();
      expect(screen.getByTestId('zoom-out-btn')).toBeInTheDocument();
      expect(screen.getByTestId('zoom-maximize-btn')).toBeInTheDocument();
    });

    it('renders network legend with community colors', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('network-legend')).toBeInTheDocument();
    });

    it('renders cascade badge', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('cascade-badge')).toBeInTheDocument();
    });

    it('renders status overlay with FPS and node/edge counts', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('status-overlay')).toBeInTheDocument();
    });
  });

  /** @spec UI_01_SIMULATION_MAIN.md#zone-2-right-metrics-panel */
  describe('Zone 2: Real-Time Metrics Panel', () => {
    it('renders "Real-Time Metrics" title with LIVE badge', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByText('Real-Time Metrics')).toBeInTheDocument();
      expect(screen.getByTestId('live-badge')).toBeInTheDocument();
    });

    it('renders active agents metric with progress bar', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('active-agents-metric')).toBeInTheDocument();
    });

    it('renders sentiment distribution bars', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('sentiment-distribution')).toBeInTheDocument();
    });

    it('renders polarization index with gradient bar', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('polarization-index')).toBeInTheDocument();
    });

    it('renders cascade stats (depth and width)', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('cascade-depth')).toBeInTheDocument();
      expect(screen.getByTestId('cascade-width')).toBeInTheDocument();
    });

    it('renders top influencers list', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('top-influencers')).toBeInTheDocument();
    });
  });

  /** @spec UI_01_SIMULATION_MAIN.md#zone-3-timeline */
  describe('Zone 3: Timeline + Diffusion Wave', () => {
    it('renders timeline controls with day label', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('timeline-controls')).toBeInTheDocument();
    });

    it('renders diffusion wave bar chart', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('diffusion-wave-chart')).toBeInTheDocument();
    });

    it('renders speed badge', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('speed-badge')).toBeInTheDocument();
    });
  });

  /** @spec UI_01_SIMULATION_MAIN.md#zone-3-conversations */
  describe('Zone 3: Conversations / Expert Agent', () => {
    it('renders expert agent analysis section', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByTestId('expert-agent-analysis')).toBeInTheDocument();
    });

    it('renders live conversation feed', () => {
      const { SimulationMain } = require('@/pages/SimulationMain');
      render(<SimulationMain />);
      expect(screen.getByText(/live conversation feed/i)).toBeInTheDocument();
    });
  });
});
