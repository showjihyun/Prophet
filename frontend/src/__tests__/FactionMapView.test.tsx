/**
 * Auto-generated from SPEC: docs/spec/ui/UI_13_SCENARIO_OPINIONS.md#faction-view
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_13_SCENARIO_OPINIONS.md#faction-view
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// ---------------------------------------------------------------------------
// Cytoscape mock — must be hoisted before component import
// ---------------------------------------------------------------------------

const mockOn = vi.fn();
const mockFit = vi.fn();
const mockDestroy = vi.fn();
const mockElements = vi.fn(() => ({ length: 0 }));

vi.mock('cytoscape', () => ({
  default: vi.fn(() => ({
    on: mockOn,
    fit: mockFit,
    destroy: mockDestroy,
    elements: mockElements,
  })),
}));

// ---------------------------------------------------------------------------
// Import component AFTER mock is set up
// ---------------------------------------------------------------------------

import cytoscape from 'cytoscape';
import FactionMapView, { type FactionCommunity } from '@/components/graph/FactionMapView';

// ---------------------------------------------------------------------------
// Test fixtures
// ---------------------------------------------------------------------------

const makeCommunity = (overrides: Partial<FactionCommunity> = {}): FactionCommunity => ({
  community_id: 'alpha',
  community_name: 'Community Alpha',
  agent_count: 2148,
  avg_sentiment: 0.45,
  conversation_count: 312,
  dominant_stance: 'positive',
  dominant_pct: 0.72,
  color: 'var(--community-alpha)',
  ...overrides,
});

const COMMUNITIES: FactionCommunity[] = [
  makeCommunity({
    community_id: 'alpha',
    community_name: 'Community Alpha',
    avg_sentiment: 0.45,
    dominant_stance: 'positive',
  }),
  makeCommunity({
    community_id: 'beta',
    community_name: 'Community Beta',
    agent_count: 1808,
    avg_sentiment: -0.3,
    dominant_stance: 'negative',
    color: 'var(--community-beta)',
  }),
  makeCommunity({
    community_id: 'gamma',
    community_name: 'Community Gamma',
    agent_count: 980,
    avg_sentiment: 0.05,
    dominant_stance: 'mixed',
    color: 'var(--community-gamma)',
  }),
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const renderView = (
  communities: FactionCommunity[] = COMMUNITIES,
  onCommunityClick?: (id: string) => void,
) => render(<FactionMapView communities={communities} onCommunityClick={onCommunityClick} />);

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe('FactionMapView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#faction-view — axis labels */
  describe('Axis labels', () => {
    it('renders "Negative Belief" axis label', () => {
      renderView();
      expect(screen.getByText('Negative Belief')).toBeInTheDocument();
    });

    it('renders "Neutral" axis label', () => {
      renderView();
      expect(screen.getByText('Neutral')).toBeInTheDocument();
    });

    it('renders "Positive Belief" axis label', () => {
      renderView();
      expect(screen.getByText('Positive Belief')).toBeInTheDocument();
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#faction-view — legend */
  describe('Legend section', () => {
    it('renders the Legend label', () => {
      renderView();
      expect(screen.getByText('Legend')).toBeInTheDocument();
    });

    it('renders Positive stance legend entry', () => {
      renderView();
      expect(screen.getByText('Positive')).toBeInTheDocument();
    });

    it('renders Mixed stance legend entry', () => {
      renderView();
      expect(screen.getByText('Mixed')).toBeInTheDocument();
    });

    it('renders Negative stance legend entry', () => {
      renderView();
      expect(screen.getByText('Negative')).toBeInTheDocument();
    });

    it('renders node-size explanation text', () => {
      renderView();
      expect(screen.getByText(/Node size = agent count/)).toBeInTheDocument();
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#faction-view — stat overlay */
  describe('Stat overlay — faction count', () => {
    it('shows the correct faction count in the stat overlay', () => {
      renderView(COMMUNITIES);
      expect(screen.getByText(`${COMMUNITIES.length} factions . Cytoscape.js`)).toBeInTheDocument();
    });

    it('shows "0 factions . Cytoscape.js" for empty communities', () => {
      renderView([]);
      expect(screen.getByText('0 factions . Cytoscape.js')).toBeInTheDocument();
    });

    it('reflects a single-community array in the stat overlay', () => {
      renderView([makeCommunity()]);
      expect(screen.getByText('1 factions . Cytoscape.js')).toBeInTheDocument();
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#faction-view — cytoscape tap handler */
  describe('onCommunityClick callback', () => {
    it('registers a "tap" event listener on cytoscape', () => {
      const onClick = vi.fn();
      renderView(COMMUNITIES, onClick);

      // cy.on should have been called; verify "tap" was one of the registered events
      const tapCall = mockOn.mock.calls.find((args) => args[0] === 'tap');
      expect(tapCall).toBeDefined();
    });

    it('does not throw when onCommunityClick is not provided', () => {
      expect(() => renderView(COMMUNITIES)).not.toThrow();
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#faction-view — empty state */
  describe('Empty communities array', () => {
    it('renders without error when communities is empty', () => {
      expect(() => renderView([])).not.toThrow();
    });

    it('does NOT initialize cytoscape when communities is empty (no nodes to render)', () => {
      vi.clearAllMocks();
      renderView([]);
      // Cytoscape constructor should not be called — no elements to display
      expect(cytoscape).not.toHaveBeenCalled();
    });

    it('still renders the axis labels even with no communities', () => {
      renderView([]);
      expect(screen.getByText('Negative Belief')).toBeInTheDocument();
      expect(screen.getByText('Neutral')).toBeInTheDocument();
      expect(screen.getByText('Positive Belief')).toBeInTheDocument();
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#faction-view — cytoscape element count */
  describe('Cytoscape initialisation', () => {
    it('calls cytoscape constructor when communities are provided', () => {
      vi.clearAllMocks();
      renderView(COMMUNITIES);
      expect(cytoscape).toHaveBeenCalledTimes(1);
    });

    it('passes the correct number of node elements to cytoscape', () => {
      vi.clearAllMocks();
      renderView(COMMUNITIES);

      const call = (cytoscape as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0];
      // Each community maps to one node
      const nodeElements = (call.elements as unknown[]).filter(
        (el: unknown) => !(el as { data: { source?: string } }).data.source,
      );
      expect(nodeElements).toHaveLength(COMMUNITIES.length);
    });

    it('passes combined nodes and edges array to cytoscape', () => {
      vi.clearAllMocks();
      renderView(COMMUNITIES);

      const call = (cytoscape as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0];
      // Total elements = nodes + edges; at minimum there are as many entries as communities
      expect((call.elements as unknown[]).length).toBeGreaterThanOrEqual(COMMUNITIES.length);
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#faction-view — cleanup on unmount */
  describe('Cleanup on unmount', () => {
    it('calls cy.destroy() when the component unmounts', () => {
      vi.clearAllMocks();
      const { unmount } = renderView(COMMUNITIES);
      unmount();
      expect(mockDestroy).toHaveBeenCalledTimes(1);
    });

    it('does not call cy.destroy() when communities was empty (cytoscape never initialised)', () => {
      vi.clearAllMocks();
      const { unmount } = renderView([]);
      unmount();
      // destroy should not be called if cytoscape was never created
      expect(mockDestroy).not.toHaveBeenCalled();
    });
  });
});
