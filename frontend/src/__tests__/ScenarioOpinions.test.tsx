/**
 * Auto-generated from SPEC: docs/spec/ui/UI_13_SCENARIO_OPINIONS.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_13_SCENARIO_OPINIONS.md
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';
import ScenarioOpinionsPage from '@/pages/ScenarioOpinionsPage';

const renderPage = () =>
  render(
    <MemoryRouter>
      <ScenarioOpinionsPage />
    </MemoryRouter>,
  );

describe('ScenarioOpinionsPage (UI-13)', () => {
  /** @spec UI_13_SCENARIO_OPINIONS.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders page-nav with breadcrumb', () => {
      renderPage();
      expect(screen.getByTestId('page-nav')).toBeInTheDocument();
    });

    it('shows Level 1 badge', () => {
      renderPage();
      expect(screen.getByText('Level 1')).toBeInTheDocument();
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#header-section */
  describe('Header Section', () => {
    it('renders title "Scenario Opinion Landscape"', () => {
      renderPage();
      expect(screen.getByText('Scenario Opinion Landscape')).toBeInTheDocument();
    });

    it('renders 4 stat cards', () => {
      renderPage();
      expect(screen.getByText('Avg Sentiment')).toBeInTheDocument();
      expect(screen.getByText('Polarization')).toBeInTheDocument();
      expect(screen.getByText('Total Conversations')).toBeInTheDocument();
      expect(screen.getByText('Active Cascades')).toBeInTheDocument();
    });
  });

  /** @spec UI_13_SCENARIO_OPINIONS.md#community-opinion-cards */
  describe('Community Opinion Cards', () => {
    it('renders 5 community opinion cards', () => {
      renderPage();
      expect(screen.getByText('Community Alpha')).toBeInTheDocument();
      expect(screen.getByText('Community Beta')).toBeInTheDocument();
      expect(screen.getByText('Community Gamma')).toBeInTheDocument();
      expect(screen.getByText('Community Delta')).toBeInTheDocument();
      expect(screen.getByText('Bridge Agents')).toBeInTheDocument();
    });

    it('each card shows agent count', () => {
      renderPage();
      expect(screen.getByText(/2,148 agents/)).toBeInTheDocument();
      expect(screen.getByText(/1,808 agents/)).toBeInTheDocument();
    });

    it('each card has View Community link', () => {
      renderPage();
      const links = screen.getAllByText('View Community');
      expect(links.length).toBe(5);
    });

    it('renders section title "Community Opinion Breakdown"', () => {
      renderPage();
      expect(screen.getByText('Community Opinion Breakdown')).toBeInTheDocument();
    });
  });
});
