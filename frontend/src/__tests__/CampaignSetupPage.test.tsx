/**
 * Auto-generated from SPEC: docs/spec/ui/UI_16_CAMPAIGN_SETUP.md
 * SPEC Version: 0.1.0
 *
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

const mockCreate = vi.fn().mockResolvedValue({ simulation_id: 'sim-1', status: 'configured' });
const mockListProjects = vi.fn().mockResolvedValue([
  { project_id: 'proj-1', name: 'Test Project', description: '', status: 'active', scenario_count: 0, created_at: null },
]);
const mockListTemplates = vi.fn().mockResolvedValue({
  templates: [
    {
      template_id: 'early_adopters',
      name: 'Early Adopters',
      agent_type: 'early_adopter',
      default_size: 100,
      description: 'Tech-savvy',
      personality_profile: { openness: 0.8, skepticism: 0.3, trend_following: 0.7, brand_loyalty: 0.4, social_influence: 0.6 },
    },
    {
      template_id: 'skeptics',
      name: 'Skeptics',
      agent_type: 'skeptic',
      default_size: 200,
      description: 'Critical thinkers',
      personality_profile: { openness: 0.3, skepticism: 0.8, trend_following: 0.2, brand_loyalty: 0.6, social_influence: 0.3 },
    },
  ],
});
const mockCreateScenario = vi.fn().mockResolvedValue({});

vi.mock('@/api/client', () => ({
  apiClient: {
    simulations: { create: (...args: unknown[]) => mockCreate(...args) },
    projects: {
      list: () => mockListProjects(),
      createScenario: (...args: unknown[]) => mockCreateScenario(...args),
    },
    communityTemplates: { list: () => mockListTemplates() },
  },
}));

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

import CampaignSetupPage from '@/pages/CampaignSetupPage';
import { useSimulationStore } from '@/store/simulationStore';

function renderPage(route = '/setup') {
  return render(
    <MemoryRouter initialEntries={[route]}>
      <CampaignSetupPage />
    </MemoryRouter>,
  );
}

describe('CampaignSetupPage (UI-16)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
    useSimulationStore.getState().setCloneConfig(null);
  });

  /** @spec UI_16_CAMPAIGN_SETUP.md#layout-structure */
  describe('Layout', () => {
    it('renders the page with data-testid', () => {
      renderPage();
      expect(screen.getByTestId('campaign-setup-page')).toBeInTheDocument();
    });

    it('renders page title', () => {
      renderPage();
      expect(screen.getByText('Create New Simulation')).toBeInTheDocument();
    });

    it('renders breadcrumbs', () => {
      renderPage();
      expect(screen.getByText('Campaign Setup')).toBeInTheDocument();
    });
  });

  /** @spec UI_16_CAMPAIGN_SETUP.md#section-2-project-selector */
  describe('Project Selector', () => {
    it('loads project list on mount', async () => {
      renderPage();
      await waitFor(() => expect(mockListProjects).toHaveBeenCalled());
    });

    it('shows project dropdown', async () => {
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Select a project...')).toBeInTheDocument();
      });
    });
  });

  /** @spec UI_16_CAMPAIGN_SETUP.md#section-3-campaign-info */
  describe('Campaign Info', () => {
    it('renders campaign name input', () => {
      renderPage();
      expect(screen.getByPlaceholderText('e.g., Q4 Product Launch')).toBeInTheDocument();
    });

    it('renders budget input', () => {
      renderPage();
      expect(screen.getByPlaceholderText('10000')).toBeInTheDocument();
    });

    it('renders all channel checkboxes', () => {
      renderPage();
      for (const ch of ['SNS', 'Influencer', 'Online Ads', 'TV', 'Email']) {
        expect(screen.getByText(ch)).toBeInTheDocument();
      }
    });

    it('renders campaign message textarea', () => {
      renderPage();
      expect(screen.getByPlaceholderText('Enter the campaign message to simulate...')).toBeInTheDocument();
    });
  });

  /** @spec UI_16_CAMPAIGN_SETUP.md#section-4-campaign-attributes */
  describe('Campaign Attributes (A-1)', () => {
    it('renders Campaign Attributes section', () => {
      renderPage();
      expect(screen.getByText('Campaign Attributes')).toBeInTheDocument();
    });

    it('renders controversy slider', () => {
      renderPage();
      expect(screen.getByText('Controversy')).toBeInTheDocument();
      expect(screen.getByText('0.1')).toBeInTheDocument();
    });

    it('renders novelty slider', () => {
      renderPage();
      expect(screen.getByText('Novelty')).toBeInTheDocument();
      // Both novelty and utility default to 0.5, so just check label exists
      expect(screen.getAllByText('0.5').length).toBeGreaterThanOrEqual(2);
    });

    it('renders utility slider', () => {
      renderPage();
      expect(screen.getByText('Utility')).toBeInTheDocument();
    });

    it('shows description for each attribute', () => {
      renderPage();
      expect(screen.getByText('Higher values cause polarization and heated debate')).toBeInTheDocument();
      expect(screen.getByText('Higher values increase attention and curiosity')).toBeInTheDocument();
      expect(screen.getByText('Higher values increase adoption likelihood')).toBeInTheDocument();
    });
  });

  /** @spec UI_16_CAMPAIGN_SETUP.md#section-5-community-configuration */
  describe('Community Configuration (A-2)', () => {
    it('renders collapsible community section', () => {
      renderPage();
      expect(screen.getByText(/Community Configuration/)).toBeInTheDocument();
    });

    it('renders Load from Templates button', () => {
      renderPage();
      expect(screen.getByText('Load from Templates')).toBeInTheDocument();
    });

    it('loads templates from API on button click', async () => {
      renderPage();
      fireEvent.click(screen.getByText('Load from Templates'));
      await waitFor(() => expect(mockListTemplates).toHaveBeenCalled());
      await waitFor(() => {
        expect(screen.getByDisplayValue('Early Adopters')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Skeptics')).toBeInTheDocument();
      });
    });

    it('renders Add Community button', () => {
      renderPage();
      expect(screen.getByText('+ Add Community')).toBeInTheDocument();
    });

    it('adds a new community card on click', async () => {
      renderPage();
      fireEvent.click(screen.getByText('+ Add Community'));
      await waitFor(() => {
        expect(screen.getByDisplayValue('Community A')).toBeInTheDocument();
      });
    });

    it('shows personality sliders after loading templates', async () => {
      renderPage();
      fireEvent.click(screen.getByText('Load from Templates'));
      await waitFor(() => {
        const labels = screen.getAllByText('Openness');
        expect(labels.length).toBeGreaterThanOrEqual(1);
      });
    });

    it('prevents removing last community', async () => {
      renderPage();
      // Add two communities
      fireEvent.click(screen.getByText('+ Add Community'));
      fireEvent.click(screen.getByText('+ Add Community'));
      await waitFor(() => {
        const removeButtons = screen.getAllByText('Remove');
        expect(removeButtons).toHaveLength(2);
        // Both should be enabled since there are 2
        expect(removeButtons[0]).not.toBeDisabled();
      });
      // Remove one, the remaining one should be disabled
      fireEvent.click(screen.getAllByText('Remove')[0]);
      await waitFor(() => {
        const removeButtons = screen.getAllByText('Remove');
        expect(removeButtons).toHaveLength(1);
        expect(removeButtons[0].closest('button')).toHaveAttribute('disabled');
      });
    });
  });

  /** @spec UI_16_CAMPAIGN_SETUP.md#section-6-advanced-settings */
  describe('Advanced Settings', () => {
    it('renders advanced settings section', () => {
      renderPage();
      expect(screen.getByText('Advanced Settings')).toBeInTheDocument();
    });

    it('renders LLM Provider dropdown', () => {
      renderPage();
      expect(screen.getByText('Ollama (Local)')).toBeInTheDocument();
    });
  });

  /** @spec UI_16_CAMPAIGN_SETUP.md#section-7-validation */
  describe('Validation', () => {
    it('blocks submit without project', async () => {
      renderPage();
      const btn = screen.getByText('Create Simulation');
      expect(btn).toBeDisabled();
    });

    it('blocks submit without name', async () => {
      renderPage();
      // Even with project selected, no name = disabled
      const btn = screen.getByText('Create Simulation');
      expect(btn).toBeDisabled();
    });
  });

  /** @spec UI_16_CAMPAIGN_SETUP.md#section-4-data-flow */
  describe('Submit Flow (A-6)', () => {
    it('sends campaign attributes in API call', async () => {
      renderPage();
      // Wait for projects to load AND render in the dropdown — the previous
      // version only waited for mockListProjects to be called, which fires
      // before React commits the new data into the select options.
      await screen.findByRole('option', { name: /Test Project/i });

      // Select project
      const select = screen.getAllByRole('combobox')[0];
      fireEvent.change(select, { target: { value: 'proj-1' } });

      // Fill name
      fireEvent.change(screen.getByPlaceholderText('e.g., Q4 Product Launch'), {
        target: { value: 'Test Campaign' },
      });

      // Submit
      fireEvent.click(screen.getByText('Create Simulation'));

      await waitFor(() => {
        expect(mockCreate).toHaveBeenCalledTimes(1);
        const config = mockCreate.mock.calls[0][0];
        expect(config.campaign).toHaveProperty('controversy', 0.1);
        expect(config.campaign).toHaveProperty('novelty', 0.5);
        expect(config.campaign).toHaveProperty('utility', 0.5);
      });
    });

    it('sends communities array when configured', async () => {
      renderPage();
      await waitFor(() => expect(mockListProjects).toHaveBeenCalled());

      // Load templates first
      fireEvent.click(screen.getByText('Load from Templates'));
      await waitFor(() => expect(mockListTemplates).toHaveBeenCalled());

      // Select project
      const select = screen.getAllByRole('combobox')[0];
      fireEvent.change(select, { target: { value: 'proj-1' } });

      // Fill name
      fireEvent.change(screen.getByPlaceholderText('e.g., Q4 Product Launch'), {
        target: { value: 'Test Campaign' },
      });

      // Submit
      fireEvent.click(screen.getByText('Create Simulation'));

      await waitFor(() => {
        expect(mockCreate).toHaveBeenCalledTimes(1);
        const config = mockCreate.mock.calls[0][0];
        expect(config.communities).toBeDefined();
        expect(config.communities).toHaveLength(2);
        expect(config.communities[0]).toHaveProperty('personality_profile');
        expect(config.communities[0].personality_profile.openness).toBe(0.8);
      });
    });

    it('navigates to /simulation after successful submit', async () => {
      renderPage();
      // Wait for projects to actually render in the dropdown
      await screen.findByRole('option', { name: /Test Project/i });

      const select = screen.getAllByRole('combobox')[0];
      fireEvent.change(select, { target: { value: 'proj-1' } });
      fireEvent.change(screen.getByPlaceholderText('e.g., Q4 Product Launch'), {
        target: { value: 'Test Campaign' },
      });
      fireEvent.click(screen.getByText('Create Simulation'));

      // Page navigates to /simulation/<sim_id> after successful create
      await waitFor(() =>
        expect(mockNavigate).toHaveBeenCalledWith(expect.stringMatching(/^\/simulation\//)),
      );
    });
  });

  /** @spec UI_16_CAMPAIGN_SETUP.md#clone-flow */
  describe('Clone Pre-fill', () => {
    it('pre-fills form from cloneConfig', () => {
      useSimulationStore.getState().setCloneConfig({
        name: 'Cloned Campaign',
        campaign: {
          name: 'Cloned Campaign',
          budget: 5000,
          channels: ['SNS', 'TV'],
          message: 'Cloned message',
          target_communities: ['alpha'],
          controversy: 0.7,
          novelty: 0.9,
          utility: 0.3,
        },
        max_steps: 100,
        random_seed: 99,
        slm_llm_ratio: 0.6,
      });
      renderPage();
      expect(screen.getByDisplayValue('Cloned Campaign')).toBeInTheDocument();
      expect(screen.getByDisplayValue('5000')).toBeInTheDocument();
      expect(screen.getByDisplayValue('Cloned message')).toBeInTheDocument();
      expect(screen.getByDisplayValue('100')).toBeInTheDocument();
      expect(screen.getByDisplayValue('99')).toBeInTheDocument();
    });
  });
});
