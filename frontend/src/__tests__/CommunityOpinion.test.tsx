/**
 * Auto-generated from SPEC: docs/spec/ui/UI_14_COMMUNITY_OPINION.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_14_COMMUNITY_OPINION.md
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import CommunityOpinionPage from '@/pages/CommunityOpinionPage';

const renderPage = (communityId = 'alpha') =>
  render(
    <MemoryRouter initialEntries={[`/opinions/${communityId}`]}>
      <Routes>
        <Route path="/opinions/:communityId" element={<CommunityOpinionPage />} />
      </Routes>
    </MemoryRouter>,
  );

describe('CommunityOpinionPage (UI-14)', () => {
  /** @spec UI_14_COMMUNITY_OPINION.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders page-nav', () => {
      renderPage();
      expect(screen.getByTestId('page-nav')).toBeInTheDocument();
    });

    it('shows Level 2 Community badge', () => {
      renderPage();
      expect(screen.getByText('Level 2 Community')).toBeInTheDocument();
    });
  });

  /** @spec UI_14_COMMUNITY_OPINION.md#header-section */
  describe('Header', () => {
    it('renders community name', () => {
      renderPage();
      expect(screen.getByText('Community Alpha')).toBeInTheDocument();
    });

    it('renders agent count', () => {
      renderPage();
      expect(screen.getByText(/2,148 agents/)).toBeInTheDocument();
    });
  });

  /** @spec UI_14_COMMUNITY_OPINION.md#opinion-clusters */
  describe('Opinion Clusters', () => {
    it('renders "Opinion Clusters" section title', () => {
      renderPage();
      expect(screen.getByText('Opinion Clusters')).toBeInTheDocument();
    });

    it('renders cluster cards with topic names', () => {
      renderPage();
      expect(screen.getByText('Election Reform Policy')).toBeInTheDocument();
      expect(screen.getByText('Economic Inequality')).toBeInTheDocument();
      expect(screen.getByText('Climate & Energy Policy')).toBeInTheDocument();
    });

    it('each cluster card shows stance breakdown', () => {
      renderPage();
      expect(screen.getAllByText(/Support/).length).toBeGreaterThanOrEqual(3);
      expect(screen.getAllByText(/Oppose/).length).toBeGreaterThanOrEqual(3);
    });
  });

  /** @spec UI_14_COMMUNITY_OPINION.md#recent-conversations */
  describe('Recent Conversations', () => {
    it('renders "Recent Conversations" section', () => {
      renderPage();
      expect(screen.getByText('Recent Conversations')).toBeInTheDocument();
    });

    it('renders conversation items with message counts', () => {
      renderPage();
      const items = screen.getAllByText(/messages/);
      expect(items.length).toBeGreaterThanOrEqual(1);
    });
  });
});
