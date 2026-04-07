/**
 * Auto-generated from SPEC: docs/spec/07_FRONTEND_SPEC.md
 * SPEC Version: 0.1.0
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#community-manage-page
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

const mockList = vi.fn();
const mockCreate = vi.fn();
const mockUpdate = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    communityTemplates: {
      list: () => mockList(),
      create: (...args: unknown[]) => mockCreate(...args),
      update: (...args: unknown[]) => mockUpdate(...args),
      delete: (...args: unknown[]) => mockDelete(...args),
    },
  },
}));

// PageNav may use window.matchMedia — stub it
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

import CommunityManagePage from '@/pages/CommunityManagePage';

const MOCK_TEMPLATES = [
  {
    template_id: 'tpl-1',
    name: 'Early Adopters',
    agent_type: 'early_adopter',
    default_size: 100,
    description: 'Tech-savvy early adopters',
    personality_profile: {
      openness: 0.8,
      skepticism: 0.2,
      trend_following: 0.7,
      brand_loyalty: 0.3,
      social_influence: 0.6,
    },
  },
  {
    template_id: 'tpl-2',
    name: 'Skeptics',
    agent_type: 'skeptic',
    default_size: 200,
    description: 'Critical thinkers',
    personality_profile: {
      openness: 0.3,
      skepticism: 0.9,
      trend_following: 0.2,
      brand_loyalty: 0.6,
      social_influence: 0.2,
    },
  },
];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/communities/manage']}>
      <CommunityManagePage />
    </MemoryRouter>,
  );
}

describe('CommunityManagePage (07_FRONTEND_SPEC)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
    mockList.mockResolvedValue({ templates: [] });
    mockCreate.mockResolvedValue({ template_id: 'new-tpl' });
    mockUpdate.mockResolvedValue({});
    mockDelete.mockResolvedValue({});
  });

  /** @spec 07_FRONTEND_SPEC.md#community-manage-layout */
  describe('Layout', () => {
    it('renders the page with data-testid', async () => {
      renderPage();
      expect(screen.getByTestId('community-manage-page')).toBeInTheDocument();
    });

    it('renders Manage Templates breadcrumb', async () => {
      renderPage();
      expect(screen.getByText('Manage Templates')).toBeInTheDocument();
    });

    it('renders + Add Template button', async () => {
      renderPage();
      expect(screen.getByRole('button', { name: /\+ Add Template/i })).toBeInTheDocument();
    });

    it('renders Back to Communities link', async () => {
      renderPage();
      expect(screen.getByText(/Back to Communities/i)).toBeInTheDocument();
    });

    it('clicking Back to Communities navigates to /communities', async () => {
      renderPage();
      fireEvent.click(screen.getByText(/Back to Communities/i));
      expect(mockNavigate).toHaveBeenCalledWith('/communities');
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#community-manage-load */
  describe('Template Loading', () => {
    it('calls communityTemplates.list on mount', async () => {
      renderPage();
      await waitFor(() => expect(mockList).toHaveBeenCalled());
    });

    it('shows loading message initially', () => {
      // Keep list pending
      mockList.mockReturnValue(new Promise(() => {}));
      renderPage();
      expect(screen.getByText(/loading templates/i)).toBeInTheDocument();
    });

    it('shows empty message when no templates returned', async () => {
      mockList.mockResolvedValue({ templates: [] });
      renderPage();
      await waitFor(() =>
        expect(screen.getByText(/no templates yet/i)).toBeInTheDocument(),
      );
    });

    it('renders template cards for returned templates', async () => {
      mockList.mockResolvedValue({ templates: MOCK_TEMPLATES });
      renderPage();
      await waitFor(() => {
        expect(screen.getByTestId('template-card-tpl-1')).toBeInTheDocument();
        expect(screen.getByTestId('template-card-tpl-2')).toBeInTheDocument();
      });
    });

    it('shows template names in cards', async () => {
      mockList.mockResolvedValue({ templates: MOCK_TEMPLATES });
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Early Adopters')).toBeInTheDocument();
        expect(screen.getByText('Skeptics')).toBeInTheDocument();
      });
    });

    it('shows template descriptions when present', async () => {
      mockList.mockResolvedValue({ templates: MOCK_TEMPLATES });
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Tech-savvy early adopters')).toBeInTheDocument();
        expect(screen.getByText('Critical thinkers')).toBeInTheDocument();
      });
    });

    it('shows error message when list call fails', async () => {
      mockList.mockRejectedValue(new Error('Server Error'));
      renderPage();
      await waitFor(() =>
        expect(screen.getByText(/Server Error/)).toBeInTheDocument(),
      );
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#community-manage-add */
  describe('Add Template Form', () => {
    it('clicking + Add Template shows New Template form', async () => {
      renderPage();
      fireEvent.click(screen.getByRole('button', { name: /\+ Add Template/i }));
      await waitFor(() =>
        expect(screen.getByText('New Template')).toBeInTheDocument(),
      );
    });

    it('shows Name, Agent Type, Default Size, Description fields', async () => {
      renderPage();
      fireEvent.click(screen.getByRole('button', { name: /\+ Add Template/i }));
      await waitFor(() => {
        expect(screen.getByPlaceholderText('Template name')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Optional description')).toBeInTheDocument();
      });
    });

    it('shows personality profile sliders', async () => {
      renderPage();
      fireEvent.click(screen.getByRole('button', { name: /\+ Add Template/i }));
      await waitFor(() => {
        expect(screen.getByText('Personality Profile')).toBeInTheDocument();
        expect(screen.getByText(/openness/i)).toBeInTheDocument();
        expect(screen.getByText(/skepticism/i)).toBeInTheDocument();
      });
    });

    it('Save button is disabled when name is empty', async () => {
      renderPage();
      fireEvent.click(screen.getByRole('button', { name: /\+ Add Template/i }));
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /^Save$/i })).toBeDisabled();
      });
    });

    it('Save button is enabled when name is filled', async () => {
      renderPage();
      fireEvent.click(screen.getByRole('button', { name: /\+ Add Template/i }));
      await waitFor(() => screen.getByPlaceholderText('Template name'));
      fireEvent.change(screen.getByPlaceholderText('Template name'), {
        target: { value: 'My Template' },
      });
      expect(screen.getByRole('button', { name: /^Save$/i })).not.toBeDisabled();
    });

    it('Cancel button hides the form', async () => {
      renderPage();
      fireEvent.click(screen.getByRole('button', { name: /\+ Add Template/i }));
      await waitFor(() => screen.getByText('New Template'));
      fireEvent.click(screen.getByRole('button', { name: /^Cancel$/i }));
      await waitFor(() =>
        expect(screen.queryByText('New Template')).not.toBeInTheDocument(),
      );
    });

    it('calls communityTemplates.create on Save with a name', async () => {
      mockList.mockResolvedValue({ templates: [] });
      renderPage();
      await waitFor(() => expect(mockList).toHaveBeenCalled());

      fireEvent.click(screen.getByRole('button', { name: /\+ Add Template/i }));
      await waitFor(() => screen.getByPlaceholderText('Template name'));

      fireEvent.change(screen.getByPlaceholderText('Template name'), {
        target: { value: 'Brand New Template' },
      });
      fireEvent.click(screen.getByRole('button', { name: /^Save$/i }));

      await waitFor(() => expect(mockCreate).toHaveBeenCalledTimes(1));
      expect(mockCreate.mock.calls[0][0]).toMatchObject({ name: 'Brand New Template' });
    });

    it('reloads template list after successful create', async () => {
      mockList.mockResolvedValue({ templates: [] });
      renderPage();
      await waitFor(() => expect(mockList).toHaveBeenCalledTimes(1));

      fireEvent.click(screen.getByRole('button', { name: /\+ Add Template/i }));
      await waitFor(() => screen.getByPlaceholderText('Template name'));

      fireEvent.change(screen.getByPlaceholderText('Template name'), {
        target: { value: 'Fresh Template' },
      });
      fireEvent.click(screen.getByRole('button', { name: /^Save$/i }));

      await waitFor(() => expect(mockList).toHaveBeenCalledTimes(2));
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#community-manage-edit */
  describe('Edit Template Form', () => {
    it('clicking Edit shows Edit Template form pre-filled with template data', async () => {
      mockList.mockResolvedValue({ templates: MOCK_TEMPLATES });
      renderPage();
      await waitFor(() => screen.getByTestId('template-card-tpl-1'));

      fireEvent.click(screen.getAllByRole('button', { name: /^Edit$/i })[0]);
      await waitFor(() => {
        expect(screen.getByText('Edit Template')).toBeInTheDocument();
        expect(screen.getByDisplayValue('Early Adopters')).toBeInTheDocument();
      });
    });

    it('calls communityTemplates.update on Save when editing', async () => {
      mockList.mockResolvedValue({ templates: MOCK_TEMPLATES });
      renderPage();
      await waitFor(() => screen.getByTestId('template-card-tpl-1'));

      fireEvent.click(screen.getAllByRole('button', { name: /^Edit$/i })[0]);
      await waitFor(() => screen.getByText('Edit Template'));

      fireEvent.click(screen.getByRole('button', { name: /^Save$/i }));

      await waitFor(() => expect(mockUpdate).toHaveBeenCalledWith('tpl-1', expect.any(Object)));
    });
  });

  /** @spec 07_FRONTEND_SPEC.md#community-manage-delete */
  describe('Delete Template', () => {
    it('renders Delete button for each template card', async () => {
      mockList.mockResolvedValue({ templates: MOCK_TEMPLATES });
      renderPage();
      await waitFor(() => {
        const deleteButtons = screen.getAllByRole('button', { name: /^Delete$/i });
        expect(deleteButtons).toHaveLength(2);
      });
    });

    it('calls communityTemplates.delete after confirm', async () => {
      mockList.mockResolvedValue({ templates: MOCK_TEMPLATES });
      // Stub window.confirm to return true
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      renderPage();
      await waitFor(() => screen.getByTestId('template-card-tpl-1'));

      fireEvent.click(screen.getAllByRole('button', { name: /^Delete$/i })[0]);

      await waitFor(() => expect(mockDelete).toHaveBeenCalledWith('tpl-1'));
      vi.restoreAllMocks();
    });

    it('does NOT call delete when confirm is cancelled', async () => {
      mockList.mockResolvedValue({ templates: MOCK_TEMPLATES });
      vi.spyOn(window, 'confirm').mockReturnValue(false);
      renderPage();
      await waitFor(() => screen.getByTestId('template-card-tpl-1'));

      fireEvent.click(screen.getAllByRole('button', { name: /^Delete$/i })[0]);

      expect(mockDelete).not.toHaveBeenCalled();
      vi.restoreAllMocks();
    });

    it('reloads template list after successful delete', async () => {
      mockList.mockResolvedValue({ templates: MOCK_TEMPLATES });
      vi.spyOn(window, 'confirm').mockReturnValue(true);
      renderPage();
      // Wait for the Delete button to actually render (templates resolved
      // AND React committed the new state).
      const deleteButtons = await screen.findAllByRole('button', { name: /^Delete$/i });
      expect(deleteButtons.length).toBeGreaterThan(0);

      fireEvent.click(deleteButtons[0]);

      // After successful delete, the mutation refetches the list.
      await waitFor(() => expect(mockList).toHaveBeenCalledTimes(2));
      vi.restoreAllMocks();
    });
  });
});
