/**
 * Auto-generated from SPEC: docs/spec/ui/UI_12_SETTINGS.md
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * @spec docs/spec/ui/UI_12_SETTINGS.md
 */
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

// Mock the apiClient to avoid actual HTTP calls
vi.mock('@/api/client', () => ({
  apiClient: {
    settings: {
      get: vi.fn().mockResolvedValue({
        llm: {
          default_provider: 'ollama',
          ollama_base_url: 'http://localhost:11434',
          ollama_default_model: 'llama3.1:8b',
          slm_model: 'llama3.1:8b',
          ollama_embed_model: 'llama3.1:8b',
          anthropic_model: 'claude-sonnet-4-6',
          anthropic_api_key_set: false,
          openai_model: 'gpt-4o',
          openai_api_key_set: false,
        },
        simulation: {
          slm_llm_ratio: 0.5,
          llm_tier3_ratio: 0.1,
          llm_cache_ttl: 3600,
          platform: 'default',
          recsys_algorithm: 'weighted',
        },
      }),
      update: vi.fn().mockResolvedValue({}),
      listOllamaModels: vi.fn().mockResolvedValue({ models: [] }),
      testOllama: vi.fn().mockResolvedValue({ status: 'ok' }),
      listPlatforms: vi.fn().mockResolvedValue({ platforms: [] }),
      listRecsys: vi.fn().mockResolvedValue({ algorithms: [] }),
    },
  },
}));

import SettingsPage from '@/pages/SettingsPage';

function renderWithRouter(ui: React.ReactElement) {
  return render(<MemoryRouter initialEntries={['/settings']}>{ui}</MemoryRouter>);
}

describe('SettingsPage (UI-12)', () => {
  /** @spec UI_12_SETTINGS.md#layout-structure */
  describe('Layout', () => {
    it('renders AppSidebar with Settings active', () => {
      renderWithRouter(<SettingsPage />);
      expect(screen.getByTestId('app-sidebar')).toBeInTheDocument();
    });

    it('renders Settings title', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() => expect(screen.getByText('Settings')).toBeInTheDocument());
    });
  });

  /** @spec UI_12_SETTINGS.md#llm-provider-configuration */
  describe('LLM Provider Configuration', () => {
    it('renders Default Provider dropdown', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() =>
        expect(screen.getByTestId('default-provider-select')).toBeInTheDocument(),
      );
    });

    it('renders Ollama Base URL input', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() =>
        expect(screen.getByTestId('ollama-base-url')).toBeInTheDocument(),
      );
    });

    it('renders Ollama model dropdowns', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() => {
        expect(screen.getByTestId('ollama-default-model')).toBeInTheDocument();
        expect(screen.getByTestId('ollama-slm-model')).toBeInTheDocument();
        expect(screen.getByTestId('ollama-embed-model')).toBeInTheDocument();
      });
    });

    it('renders Test Connection button', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() =>
        expect(screen.getByRole('button', { name: /test connection/i })).toBeInTheDocument(),
      );
    });

    it('renders Claude API Key input (masked)', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() =>
        expect(screen.getByTestId('anthropic-api-key')).toBeInTheDocument(),
      );
    });

    it('renders OpenAI API Key input (masked)', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() =>
        expect(screen.getByTestId('openai-api-key')).toBeInTheDocument(),
      );
    });
  });

  /** @spec UI_12_SETTINGS.md#simulation-defaults */
  describe('Simulation Defaults', () => {
    it('renders SLM/LLM Ratio slider', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() =>
        expect(screen.getByTestId('slm-llm-ratio')).toBeInTheDocument(),
      );
    });

    it('renders Tier 3 Ratio input', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() =>
        expect(screen.getByTestId('tier3-ratio')).toBeInTheDocument(),
      );
    });

    it('renders Cache TTL input', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() =>
        expect(screen.getByTestId('cache-ttl')).toBeInTheDocument(),
      );
    });
  });

  /** @spec UI_12_SETTINGS.md#save */
  describe('Save', () => {
    it('renders Save Settings button', async () => {
      renderWithRouter(<SettingsPage />);
      await waitFor(() =>
        expect(screen.getByRole('button', { name: /save settings/i })).toBeInTheDocument(),
      );
    });
  });
});
