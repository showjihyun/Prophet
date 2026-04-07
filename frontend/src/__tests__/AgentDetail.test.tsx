/**
 * Auto-generated from SPEC: docs/spec/ui/UI_04_AGENT_DETAIL.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_04_AGENT_DETAIL.md
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { useSimulationStore } from '@/store/simulationStore';

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

// AgentDetailPage now strictly renders real API data (no MOCK fallback).
// Provide a successful agent fetch so the body actually renders.
vi.mock('@/api/client', () => ({
  apiClient: {
    agents: {
      get: vi.fn().mockResolvedValue({
        agent_id: 'a1b2c3d4-0000-0000-0000-000000000001',
        community_id: 'A',
        agent_type: 'consumer',
        action: 'share',
        adopted: true,
        influence_score: 0.82,
        belief: 0.7,
        personality: {
          openness: 0.78,
          skepticism: 0.42,
          adaptability: 0.65,
          advocacy: 0.88,
          trust: 0.71,
        },
        emotion: { interest: 0.6, trust: 0.87, skepticism: 0.2, excitement: 0.5 },
        memories: [],
      }),
      getMemory: vi.fn().mockResolvedValue({ memories: [] }),
      modify: vi.fn().mockResolvedValue({}),
    },
    network: {
      get: vi.fn().mockResolvedValue({ nodes: [], edges: [] }),
    },
  },
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

vi.mock('@/components/graph/EgoGraph', () => ({
  default: () => <div data-testid="ego-graph" />,
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

// Seed the simulation store with a fake sim so AgentDetailPage doesn't hit
// the "No active simulation" gate. The agent fetch is mocked above to
// resolve immediately, so the loading gate also clears on first effect tick.
beforeEach(() => {
  useSimulationStore.setState({
    simulation: {
      simulation_id: 'sim-test-001',
      project_id: 'proj-001',
      scenario_id: 'scen-001',
      status: 'running',
      current_step: 5,
      max_steps: 365,
      created_at: new Date().toISOString(),
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
    } as any,
    status: 'running',
    currentStep: 5,
    steps: [],
    latestStep: null,
  });
});

// Render and wait for the agent loading gate to resolve. Every test needs
// this because AgentDetailPage now strictly renders real data.
const renderAndWait = async () => {
  const utils = renderPage();
  // The loading state has data-testid="agent-detail-page" with a spinner
  // that disappears once the fetch resolves. We wait for the breadcrumb
  // (only in the loaded body) to appear.
  await utils.findByTestId('agent-breadcrumb');
  return utils;
};

describe('AgentDetail (UI-04)', () => {
  /** @spec UI_04_AGENT_DETAIL.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders back button', async () => {
      await renderAndWait();
      expect(screen.getByTestId('back-btn')).toBeInTheDocument();
    });

    it('renders breadcrumb with agent ID', async () => {
      await renderAndWait();
      expect(screen.getByTestId('agent-breadcrumb')).toBeInTheDocument();
    });

    it('renders "Intervene" primary button', async () => {
      await renderAndWait();
      expect(screen.getByRole('button', { name: /intervene/i })).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#left-panel-agent-profile */
  describe('Left Panel: Agent Profile', () => {
    it('renders agent avatar circle', async () => {
      await renderAndWait();
      expect(screen.getByTestId('agent-avatar')).toBeInTheDocument();
    });

    it('renders agent ID heading', async () => {
      await renderAndWait();
      expect(screen.getByTestId('agent-id-heading')).toBeInTheDocument();
    });

    it('renders community badge', async () => {
      await renderAndWait();
      expect(screen.getByTestId('community-badge')).toBeInTheDocument();
    });

    it('renders 4 quick stats (Influence, Connections, Subscribers, Trust)', async () => {
      await renderAndWait();
      expect(screen.getAllByText('Influence').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Connections').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Subscribers').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Trust Level').length).toBeGreaterThanOrEqual(1);
    });

    it('renders 5 personality trait bars', async () => {
      await renderAndWait();
      // Trait labels come from the agent.personality keys (capitalized).
      // Mock provides: openness, skepticism, adaptability, advocacy, trust
      expect(screen.getByText('Openness')).toBeInTheDocument();
      expect(screen.getByText('Skepticism')).toBeInTheDocument();
      expect(screen.getByText('Adaptability')).toBeInTheDocument();
      expect(screen.getByText('Advocacy')).toBeInTheDocument();
      // 'Trust' (label) appears in multiple places (trait + quick stat)
      expect(screen.getAllByText('Trust').length).toBeGreaterThan(0);
    });

    it('renders personality trait progress bars with percentages', async () => {
      await renderAndWait();
      const traitBars = screen.getAllByTestId(/trait-bar/);
      expect(traitBars.length).toBe(5);
    });

    it('renders memory summary card', async () => {
      await renderAndWait();
      expect(screen.getByTestId('memory-summary')).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#right-panel-tabs */
  describe('Right Panel: Tabs', () => {
    it('renders tab bar with Activity, Connections, Messages tabs', async () => {
      await renderAndWait();
      expect(screen.getByRole('tab', { name: /activity/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /connections/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /messages/i })).toBeInTheDocument();
    });

    it('Activity tab is active by default', async () => {
      await renderAndWait();
      const activityTab = screen.getByRole('tab', { name: /activity/i });
      expect(activityTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#activity-tab-content */
  describe('Activity Tab: Sentiment Chart', () => {
    it('renders "Sentiment Over Time" chart', async () => {
      await renderAndWait();
      expect(screen.getByTestId('sentiment-chart')).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#activity-tab-content */
  describe('Activity Tab: Recent Interactions', () => {
    it('renders interactions table with required columns', async () => {
      await renderAndWait();
      expect(screen.getByText('Target Agent')).toBeInTheDocument();
      expect(screen.getByText('Type')).toBeInTheDocument();
      expect(screen.getByText('Sentiment')).toBeInTheDocument();
      expect(screen.getByText('Message Preview')).toBeInTheDocument();
      expect(screen.getByText('Time')).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#intervention-modal */
  describe('Intervention Modal', () => {
    beforeEach(() => {
      // The Intervene button is only enabled when simulation status is 'paused'
      useSimulationStore.setState({ status: 'paused' });
    });

    it('opens intervention modal when Intervene button is clicked', async () => {
      await renderAndWait();
      fireEvent.click(screen.getByRole('button', { name: /intervene/i }));
      expect(screen.getByTestId('intervention-modal')).toBeInTheDocument();
    });

    it('modal contains intervention type selector', async () => {
      await renderAndWait();
      fireEvent.click(screen.getByRole('button', { name: /intervene/i }));
      expect(screen.getByTestId('intervention-type-select')).toBeInTheDocument();
    });

    it('modal contains Apply and Cancel buttons', async () => {
      await renderAndWait();
      fireEvent.click(screen.getByRole('button', { name: /intervene/i }));
      expect(screen.getByRole('button', { name: /apply intervention/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });
  });
});
