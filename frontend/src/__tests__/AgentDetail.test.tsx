/**
 * Auto-generated from SPEC: docs/spec/ui/UI_04_AGENT_DETAIL.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_04_AGENT_DETAIL.md
 */
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';

describe('AgentDetail (UI-04)', () => {
  /** @spec UI_04_AGENT_DETAIL.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders back button', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByTestId('back-btn')).toBeInTheDocument();
    });

    it('renders breadcrumb with agent ID', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByTestId('agent-breadcrumb')).toBeInTheDocument();
    });

    it('renders "Intervene" primary button', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByRole('button', { name: /intervene/i })).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#left-panel-agent-profile */
  describe('Left Panel: Agent Profile', () => {
    it('renders agent avatar circle', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByTestId('agent-avatar')).toBeInTheDocument();
    });

    it('renders agent ID heading', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByTestId('agent-id-heading')).toBeInTheDocument();
    });

    it('renders community badge', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByTestId('community-badge')).toBeInTheDocument();
    });

    it('renders 4 quick stats (Influence, Connections, Subscribers, Trust)', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByText('Influence')).toBeInTheDocument();
      expect(screen.getByText('Connections')).toBeInTheDocument();
      expect(screen.getByText('Subscribers')).toBeInTheDocument();
      expect(screen.getByText('Trust Level')).toBeInTheDocument();
    });

    it('renders 5 personality trait bars', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByText('Openness')).toBeInTheDocument();
      expect(screen.getByText('Skepticism')).toBeInTheDocument();
      expect(screen.getByText('Adaptability')).toBeInTheDocument();
      expect(screen.getByText('Advocacy')).toBeInTheDocument();
      expect(screen.getByText('Trust/Safety')).toBeInTheDocument();
    });

    it('renders personality trait progress bars with percentages', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      const traitBars = screen.getAllByTestId(/trait-bar/);
      expect(traitBars.length).toBe(5);
    });

    it('renders memory summary card', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByTestId('memory-summary')).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#right-panel-tabs */
  describe('Right Panel: Tabs', () => {
    it('renders tab bar with Activity, Connections, Messages tabs', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByRole('tab', { name: /activity/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /connections/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /messages/i })).toBeInTheDocument();
    });

    it('Activity tab is active by default', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      const activityTab = screen.getByRole('tab', { name: /activity/i });
      expect(activityTab).toHaveAttribute('aria-selected', 'true');
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#activity-tab-content */
  describe('Activity Tab: Sentiment Chart', () => {
    it('renders "Sentiment Over Time" chart', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      expect(screen.getByTestId('sentiment-chart')).toBeInTheDocument();
    });
  });

  /** @spec UI_04_AGENT_DETAIL.md#activity-tab-content */
  describe('Activity Tab: Recent Interactions', () => {
    it('renders interactions table with required columns', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
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
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      fireEvent.click(screen.getByRole('button', { name: /intervene/i }));
      expect(screen.getByTestId('intervention-modal')).toBeInTheDocument();
    });

    it('modal contains intervention type selector', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      fireEvent.click(screen.getByRole('button', { name: /intervene/i }));
      expect(screen.getByTestId('intervention-type-select')).toBeInTheDocument();
    });

    it('modal contains Apply and Cancel buttons', () => {
      const { AgentDetail } = require('@/pages/AgentDetail');
      render(<AgentDetail />);
      fireEvent.click(screen.getByRole('button', { name: /intervene/i }));
      expect(screen.getByRole('button', { name: /apply intervention/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();
    });
  });
});
