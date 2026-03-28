/**
 * Auto-generated from SPEC: docs/spec/ui/UI_05_GLOBAL_METRICS.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_05_GLOBAL_METRICS.md
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

describe('GlobalMetrics (UI-05)', () => {
  /** @spec UI_05_GLOBAL_METRICS.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders "Back to Simulation" button', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByRole('button', { name: /back to simulation/i })).toBeInTheDocument();
    });

    it('renders "Global Insight & Metrics" page title', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByText('Global Insight & Metrics')).toBeInTheDocument();
    });

    it('renders "Export Data" button', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByRole('button', { name: /export data/i })).toBeInTheDocument();
    });
  });

  /** @spec UI_05_GLOBAL_METRICS.md#summary-stats */
  describe('Summary Stats', () => {
    it('renders Total Agents card with delta indicator', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByText('Total Agents')).toBeInTheDocument();
      expect(screen.getByTestId('total-agents-delta')).toBeInTheDocument();
    });

    it('renders Active Cascades card with today delta', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByText('Active Cascades')).toBeInTheDocument();
      expect(screen.getByTestId('cascades-delta')).toBeInTheDocument();
    });

    it('renders Polarization card with delta from previous day', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByText('Polarization')).toBeInTheDocument();
      expect(screen.getByTestId('polarization-delta')).toBeInTheDocument();
    });

    it('renders Simulation Day card with progress bar', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByText('Simulation Day')).toBeInTheDocument();
      expect(screen.getByTestId('sim-day-progress')).toBeInTheDocument();
    });
  });

  /** @spec UI_05_GLOBAL_METRICS.md#charts-area */
  describe('Charts Area', () => {
    it('renders "Polarization Trend" bar chart', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByText('Polarization Trend')).toBeInTheDocument();
      expect(screen.getByTestId('polarization-trend-chart')).toBeInTheDocument();
    });

    it('renders "Sentiment by Community" stacked bar chart', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByText('Sentiment by Community')).toBeInTheDocument();
      expect(screen.getByTestId('sentiment-community-chart')).toBeInTheDocument();
    });
  });

  /** @spec UI_05_GLOBAL_METRICS.md#prophet-3-tier-cost-optimization */
  describe('Prophet 3-Tier Cost Optimization', () => {
    it('renders section title', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByText('Prophet 3-Tier Cost Optimization')).toBeInTheDocument();
    });

    it('renders Tier 1: Mass SLM card with agent count', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByTestId('tier1-card')).toBeInTheDocument();
      expect(screen.getByText(/mass slm/i)).toBeInTheDocument();
    });

    it('renders Tier 2: Semantic card with agent count', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByTestId('tier2-card')).toBeInTheDocument();
      expect(screen.getByText(/semantic/i)).toBeInTheDocument();
    });

    it('renders Tier 3: Elite LLM card with agent count', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByTestId('tier3-card')).toBeInTheDocument();
      expect(screen.getByText(/elite llm/i)).toBeInTheDocument();
    });
  });

  /** @spec UI_05_GLOBAL_METRICS.md#cascade-analytics */
  describe('Cascade Analytics', () => {
    it('renders section title', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByText('Cascade Analytics')).toBeInTheDocument();
    });

    it('renders Avg Cascade Depth stat', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByTestId('avg-cascade-depth')).toBeInTheDocument();
    });

    it('renders Max Cascade Width stat', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByTestId('max-cascade-width')).toBeInTheDocument();
    });

    it('renders Critical Path stat', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByTestId('critical-path')).toBeInTheDocument();
    });

    it('renders Decay Rate stat', () => {
      const { GlobalMetrics } = require('@/pages/GlobalMetrics');
      render(<GlobalMetrics />);
      expect(screen.getByTestId('decay-rate')).toBeInTheDocument();
    });
  });
});
