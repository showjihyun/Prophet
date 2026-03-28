/**
 * Auto-generated from SPEC: docs/spec/ui/UI_03_TOP_INFLUENCERS.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_03_TOP_INFLUENCERS.md
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

describe('TopInfluencers (UI-03)', () => {
  /** @spec UI_03_TOP_INFLUENCERS.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders breadcrumb with "Home > Top Influencers"', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      expect(screen.getByText('Top Influencers')).toBeInTheDocument();
    });
  });

  /** @spec UI_03_TOP_INFLUENCERS.md#summary-stats */
  describe('Summary Stats', () => {
    it('renders 4 summary stat cards', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      expect(screen.getByText('Influencers Tracked')).toBeInTheDocument();
      expect(screen.getByText('Avg Influence Score')).toBeInTheDocument();
      expect(screen.getByText('Top Community')).toBeInTheDocument();
      expect(screen.getByText('Active Cascades')).toBeInTheDocument();
    });
  });

  /** @spec UI_03_TOP_INFLUENCERS.md#search-filter-bar */
  describe('Search + Filter Bar', () => {
    it('renders search input with placeholder', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      expect(screen.getByPlaceholderText(/search agents/i)).toBeInTheDocument();
    });

    it('renders filter button', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      expect(screen.getByRole('button', { name: /filter/i })).toBeInTheDocument();
    });
  });

  /** @spec UI_03_TOP_INFLUENCERS.md#data-table */
  describe('Data Table', () => {
    it('renders table with required column headers', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      expect(screen.getByText('Agent ID')).toBeInTheDocument();
      expect(screen.getByText('Community')).toBeInTheDocument();
      expect(screen.getByText('Influence Score')).toBeInTheDocument();
      expect(screen.getByText('Sentiment')).toBeInTheDocument();
      expect(screen.getByText('Chains')).toBeInTheDocument();
      expect(screen.getByText('Connections')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('renders influence score bars in score column', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      const scoreBars = screen.getAllByTestId(/influence-score-bar/);
      expect(scoreBars.length).toBeGreaterThan(0);
    });

    it('renders community badges with colored dots', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      const communityBadges = screen.getAllByTestId(/community-badge/);
      expect(communityBadges.length).toBeGreaterThan(0);
    });

    it('renders status badges (Active/Idle)', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      const statusBadges = screen.getAllByTestId(/status-badge/);
      expect(statusBadges.length).toBeGreaterThan(0);
    });

    it('renders pagination controls', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      expect(screen.getByTestId('table-pagination')).toBeInTheDocument();
    });
  });

  /** @spec UI_03_TOP_INFLUENCERS.md#right-sidebar */
  describe('Right Sidebar: Influence Distribution', () => {
    it('renders "Influence Distribution" chart title', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      expect(screen.getByText('Influence Distribution')).toBeInTheDocument();
    });

    it('renders horizontal bar chart with 5 community bars', () => {
      const { TopInfluencers } = require('@/pages/TopInfluencers');
      render(<TopInfluencers />);
      expect(screen.getByTestId('influence-distribution-chart')).toBeInTheDocument();
    });
  });
});
