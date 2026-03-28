/**
 * Auto-generated from SPEC: docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_02_COMMUNITIES_DETAIL.md
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

describe('CommunitiesDetail (UI-02)', () => {
  /** @spec UI_02_COMMUNITIES_DETAIL.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders breadcrumb with "Home > Communities Overview"', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      expect(screen.getByText('Communities Overview')).toBeInTheDocument();
    });

    it('renders logo with "MCASP Prophet Engine"', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      expect(screen.getByText('MCASP Prophet Engine')).toBeInTheDocument();
    });
  });

  /** @spec UI_02_COMMUNITIES_DETAIL.md#summary-stats */
  describe('Summary Stats', () => {
    it('renders 4 summary stat cards', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      expect(screen.getByText('Total Communities')).toBeInTheDocument();
      expect(screen.getByText('Total Agents')).toBeInTheDocument();
      expect(screen.getByText('Active Interactions')).toBeInTheDocument();
      expect(screen.getByText('Avg Sentiment')).toBeInTheDocument();
    });
  });

  /** @spec UI_02_COMMUNITIES_DETAIL.md#community-cards-grid */
  describe('Community Cards Grid', () => {
    it('renders 5 community cards', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      expect(screen.getByTestId('community-card-alpha')).toBeInTheDocument();
      expect(screen.getByTestId('community-card-beta')).toBeInTheDocument();
      expect(screen.getByTestId('community-card-gamma')).toBeInTheDocument();
      expect(screen.getByTestId('community-card-delta')).toBeInTheDocument();
      expect(screen.getByTestId('community-card-bridge')).toBeInTheDocument();
    });

    it('each community card shows agent count badge', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      const alphaCard = screen.getByTestId('community-card-alpha');
      expect(alphaCard).toHaveTextContent(/agents/i);
    });

    it('each community card shows sentiment bar', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      const sentimentBars = screen.getAllByTestId(/sentiment-bar/);
      expect(sentimentBars.length).toBeGreaterThanOrEqual(5);
    });

    it('each community card shows key influencers', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      const influencerSections = screen.getAllByTestId(/key-influencers/);
      expect(influencerSections.length).toBeGreaterThanOrEqual(5);
    });

    it('each community card shows emotion distribution bar', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      const emotionBars = screen.getAllByTestId(/emotion-distribution/);
      expect(emotionBars.length).toBeGreaterThanOrEqual(5);
    });

    it('each community card shows activity status label', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      const statusLabels = screen.getAllByTestId(/activity-status/);
      expect(statusLabels.length).toBeGreaterThanOrEqual(5);
    });
  });

  /** @spec UI_02_COMMUNITIES_DETAIL.md#community-connections-matrix */
  describe('Community Connections Matrix', () => {
    it('renders "Community Connections" section', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      expect(screen.getByText('Community Connections')).toBeInTheDocument();
    });

    it('renders 5x5 matrix grid', () => {
      const { CommunitiesDetail } = require('@/pages/CommunitiesDetail');
      render(<CommunitiesDetail />);
      expect(screen.getByTestId('connections-matrix')).toBeInTheDocument();
    });
  });
});
