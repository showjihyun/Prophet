/**
 * Auto-generated from SPEC: docs/spec/ui/UI_15_CONVERSATION_THREAD.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_15_CONVERSATION_THREAD.md
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ConversationThreadPage from '@/pages/ConversationThreadPage';

const renderPage = (communityId = 'alpha', threadId = 't1') =>
  render(
    <MemoryRouter initialEntries={[`/opinions/${communityId}/thread/${threadId}`]}>
      <Routes>
        <Route
          path="/opinions/:communityId/thread/:threadId"
          element={<ConversationThreadPage />}
        />
      </Routes>
    </MemoryRouter>,
  );

describe('ConversationThreadPage (UI-15)', () => {
  /** @spec UI_15_CONVERSATION_THREAD.md#navigation-bar */
  describe('Navigation Bar', () => {
    it('renders page-nav', () => {
      renderPage();
      expect(screen.getByTestId('page-nav')).toBeInTheDocument();
    });

    it('shows Level 3 badge', () => {
      renderPage();
      expect(screen.getByText('Level 3')).toBeInTheDocument();
    });
  });

  /** @spec UI_15_CONVERSATION_THREAD.md#header-section */
  describe('Header', () => {
    it('renders thread topic title', () => {
      renderPage();
      expect(
        screen.getByText('Debate on progressive taxation reform impact'),
      ).toBeInTheDocument();
    });

    it('renders category tag', () => {
      renderPage();
      expect(screen.getByText('Election Reform')).toBeInTheDocument();
    });

    it('shows participant count', () => {
      renderPage();
      expect(screen.getAllByText(/Participants/).length).toBeGreaterThanOrEqual(1);
    });

    it('shows avg sentiment badge', () => {
      renderPage();
      expect(screen.getByText(/Avg Sentiment/)).toBeInTheDocument();
    });
  });

  /** @spec UI_15_CONVERSATION_THREAD.md#thread-messages */
  describe('Thread Messages', () => {
    it('renders messages with agent IDs', () => {
      renderPage();
      expect(screen.getAllByText('Agent-A042').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Agent-B091').length).toBeGreaterThanOrEqual(1);
    });

    it('renders stance badges', () => {
      renderPage();
      expect(screen.getAllByText('Progressive').length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText('Conservative').length).toBeGreaterThanOrEqual(1);
    });

    it('renders reaction counts (Agree, Disagree, Nuanced)', () => {
      renderPage();
      expect(screen.getAllByText(/Agree/).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Disagree/).length).toBeGreaterThanOrEqual(1);
      expect(screen.getAllByText(/Nuanced/).length).toBeGreaterThanOrEqual(1);
    });

    it('renders reply messages with indentation', () => {
      renderPage();
      const replies = document.querySelectorAll('[data-testid="thread-reply"]');
      expect(replies.length).toBeGreaterThanOrEqual(1);
    });
  });
});
