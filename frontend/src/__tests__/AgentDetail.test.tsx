/**
 * Auto-generated from SPEC: docs/spec/ui/UI_04_AGENT_DETAIL.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_04_AGENT_DETAIL.md
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
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

import AgentDetailPage from '@/pages/AgentDetailPage';

const renderPage = () =>
  render(
    <MemoryRouter initialEntries={['/agent/agent-001']}>
      <Routes>
        <Route path="/agent/:agentId" element={<AgentDetailPage />} />
      </Routes>
    </MemoryRouter>,
  );

describe('AgentDetail (UI-04)', () => {
  /** @spec UI_04_AGENT_DETAIL.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders back button', () => {
      renderPage();
      expect(screen.getByTestId('back-btn')).toBeInTheDocument();
    });

    it('renders breadcrumb with agent ID', () => {
      renderPage();
      expect(screen.getByTestId('agent-breadcrumb')).toBeInTheDocument();
    });

    it('renders "Intervene" primary button', () => {
      renderPage();
      expect(screen.getByRole('button', { name: /intervene/i })).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#left-panel-agent-profile */
  describe('Left Panel: Agent Profile', () => {
    it('renders agent avatar circle', () => {
      renderPage();
      expect(screen.getByTestId('agent-avatar')).toBeInTheDocument();
    });

    it('renders agent ID heading', () => {
      renderPage();
      expect(screen.getByTestId('agent-id-heading')).toBeInTheDocument();
    });

    it('renders community badge', () => {
      renderPage();
      expect(screen.getByTestId('community-badge')).toBeInTheDocument();
    });

    it('renders 4 quick stats (Influence, Connections, Subscribers, Trust)', () => {
      renderPage();
      expect(screen.getAllByText('Influence').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Connections').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Subscribers').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Trust Level').length).toBeGreaterThanOrEqual(1);
    });

    it('renders 5 personality trait bars', () => {
      renderPage();
      expect(screen.getByText('Openness')).toBeInTheDocument();
      expect(screen.getByText('Skepticism')).toBeInTheDocument();
      expect(screen.getByText('Adaptability')).toBeInTheDocument();
      expect(screen.getByText('Advocacy')).toBeInTheDocument();
      expect(screen.getByText('Trust/Safety')).toBeInTheDocument();
    });

    it('renders personality trait progress bars with percentages', () => {
      renderPage();
      const traitBars = screen.getAllByTestId(/trait-bar/);
      expect(traitBars.length).toBe(5);
    });

    it('renders memory summary card', () => {
      renderPage();
      expect(screen.getByTestId('memory-summary')).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#right-panel-tabs */
  describe('Right Panel: Tabs', () => {
    it('renders tab bar with Activity, Connections, Messages tabs', () => {
      renderPage();
      expect(screen.getByRole('tab', { name: /activity/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /connections/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /messages/i })).toBeInTheDocument();
    });

    it('Activity tab is active by default', () => {
      renderPage();
      const activityTab = screen.getByRole('tab', { name: /activity/i });
      expect(activityTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#activity-tab-content */
  describe('Activity Tab: Sentiment Chart', () => {
    it('renders "Sentiment Over Time" chart', () => {
      renderPage();
      expect(screen.getByTestId('sentiment-chart')).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#activity-tab-content */
  describe('Activity Tab: Recent Interactions', () => {
    it('renders interactions table with required columns', () => {
      renderPage();
      expect(screen.getByText('Target Agent')).toBeInTheDocument();
      expect(screen.getByText('Type')).toBeInTheDocument();
      expect(screen.getByText('Sentiment')).toBeInTheDocument();
      expect(screen.getByText('Message Preview')).toBeInTheDocument();
      expect(screen.getByText('Time')).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#intervention-modal */
  describe('Intervention Modal', () => {
    it('opens intervention modal when Intervene button is clicked', () => {
      renderPage();
      fireEvent.click(screen.getByRole('button', { name: /intervene/i }));
      expect(screen.getByTestId('intervention-modal')).toBeInTheDocument();
    });

    it('modal contains intervention type selector', () => {
      renderPage();
      fireEvent.click(screen.getByRole('button', { name: /intervene/i }));
      expect(screen.getByTestId('intervention-type-select')).toBeInTheDocument();
    });

    it('modal contains Apply and Cancel buttons', () => {
      renderPage();
      fireEvent.click(screen.getByRole('button', { name: /intervene/i }));
      expect(screen.getByRole('button', { name: /apply intervention/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });
  });
});
