/**
 * Auto-generated from SPEC: docs/spec/ui/UI_12_SETTINGS.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_12_SETTINGS.md
 */
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter initialEntries={['/settings']}>{ui}</MemoryRouter>);
}

describe('SettingsPage (UI-12)', () => {
  /** @spec UI_12_SETTINGS.md#layout-structure */
  describe('Layout', () => {
    it('renders AppSidebar with Settings active', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    });

    it('renders Settings title', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByText('Settings')).toBeInTheDocument();
    });
  });

  /** @spec UI_12_SETTINGS.md#llm-provider-configuration */
  describe('LLM Provider Configuration', () => {
    it('renders Default Provider dropdown', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByTestId('default-provider-select')).toBeInTheDocument();
    });

    it('renders Ollama Base URL input', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByTestId('ollama-base-url')).toBeInTheDocument();
    });

    it('renders Ollama model dropdowns', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByTestId('ollama-default-model')).toBeInTheDocument();
      expect(screen.getByTestId('ollama-slm-model')).toBeInTheDocument();
      expect(screen.getByTestId('ollama-embed-model')).toBeInTheDocument();
    });

    it('renders Test Connection button', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByRole('button', { name: /test connection/i })).toBeInTheDocument();
    });

    it('renders Claude API Key input (masked)', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByTestId('anthropic-api-key')).toBeInTheDocument();
    });

    it('renders OpenAI API Key input (masked)', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByTestId('openai-api-key')).toBeInTheDocument();
    });
  });

  /** @spec UI_12_SETTINGS.md#simulation-defaults */
  describe('Simulation Defaults', () => {
    it('renders SLM/LLM Ratio slider', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByTestId('slm-llm-ratio')).toBeInTheDocument();
    });

    it('renders Tier 3 Ratio input', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByTestId('tier3-ratio')).toBeInTheDocument();
    });

    it('renders Cache TTL input', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByTestId('cache-ttl')).toBeInTheDocument();
    });
  });

  /** @spec UI_12_SETTINGS.md#save */
  describe('Save', () => {
    it('renders Save Settings button', () => {
      const SettingsPage = require('@/pages/SettingsPage').default;
      renderWithRouter(<SettingsPage />);
      expect(screen.getByRole('button', { name: /save settings/i })).toBeInTheDocument();
    });
  });
});
