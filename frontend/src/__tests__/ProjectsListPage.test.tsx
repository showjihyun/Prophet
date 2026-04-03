/**
 * Auto-generated from SPEC: docs/spec/ui/UI_06_PROJECTS_LIST.md
 * SPEC Version: 0.1.0
 *
 * @spec docs/spec/ui/UI_06_PROJECTS_LIST.md
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

vi.mock('@/components/shared/AppSidebar', () => ({
  default: () => <aside data-testid="app-sidebar" />,
}));

const mockListProjects = vi.fn();
const mockCreateProject = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    projects: {
      list: () => mockListProjects(),
      create: (...args: unknown[]) => mockCreateProject(...args),
    },
  },
}));

import ProjectsListPage from '@/pages/ProjectsListPage';

const MOCK_PROJECTS = [
  {
    project_id: 'proj-1',
    name: 'Alpha Campaign',
    description: 'First campaign project',
    status: 'active',
    scenario_count: 3,
    created_at: '2026-01-15T10:00:00Z',
  },
  {
    project_id: 'proj-2',
    name: 'Beta Campaign',
    description: 'Second campaign project',
    status: 'draft',
    scenario_count: 0,
    created_at: '2026-02-01T10:00:00Z',
  },
];

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/projects']}>
      <ProjectsListPage />
    </MemoryRouter>,
  );
}

describe('ProjectsListPage (UI-06)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
  });

  /** @spec UI_06_PROJECTS_LIST.md#layout-structure */
  describe('Layout', () => {
    it('renders page with data-testid', async () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      expect(screen.getByTestId('projects-list-page')).toBeInTheDocument();
    });

    it('renders Projects heading', async () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      expect(screen.getByText('Projects')).toBeInTheDocument();
    });

    it('renders page subtitle', () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      expect(
        screen.getByText('Manage your simulation projects and scenarios'),
      ).toBeInTheDocument();
    });
  });

  /** @spec UI_06_PROJECTS_LIST.md#new-project-button */
  describe('New Project Button', () => {
    it('renders New Project button in header', () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      expect(screen.getByRole('button', { name: /new project/i })).toBeInTheDocument();
    });
  });

  /** @spec UI_06_PROJECTS_LIST.md#loading-state */
  describe('Loading State', () => {
    it('shows loading text while fetching projects', () => {
      mockListProjects.mockReturnValue(new Promise(() => {})); // never resolves
      renderPage();
      expect(screen.getByText('Loading projects...')).toBeInTheDocument();
    });
  });

  /** @spec UI_06_PROJECTS_LIST.md#empty-state */
  describe('Empty State', () => {
    it('shows empty state when no projects exist', async () => {
      mockListProjects.mockResolvedValue([]);
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('Welcome to Prophet MCASP')).toBeInTheDocument(),
      );
    });

    it('shows Create Project button in empty state', async () => {
      mockListProjects.mockResolvedValue([]);
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('button', { name: /create project/i })).toBeInTheDocument(),
      );
    });
  });

  /** @spec UI_06_PROJECTS_LIST.md#project-list */
  describe('Project List', () => {
    it('loads projects from API on mount', async () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      await waitFor(() => expect(mockListProjects).toHaveBeenCalledTimes(1));
    });

    it('renders project names after loading', async () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Alpha Campaign')).toBeInTheDocument();
        expect(screen.getByText('Beta Campaign')).toBeInTheDocument();
      });
    });

    it('renders project description', async () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('First campaign project')).toBeInTheDocument(),
      );
    });

    it('renders scenario counts for each project', async () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Scenarios: 3')).toBeInTheDocument();
        expect(screen.getByText('Scenarios: 0')).toBeInTheDocument();
      });
    });

    it('renders Open button for each project', async () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      await waitFor(() => {
        const openButtons = screen.getAllByRole('button', { name: /open/i });
        expect(openButtons).toHaveLength(MOCK_PROJECTS.length);
      });
    });

    it('navigates to project detail when Open is clicked', async () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      await waitFor(() =>
        expect(screen.getAllByRole('button', { name: /open/i })).toHaveLength(2),
      );
      fireEvent.click(screen.getAllByRole('button', { name: /open/i })[0]);
      expect(mockNavigate).toHaveBeenCalledWith('/projects/proj-1');
    });

    it('renders status badge for each project', async () => {
      mockListProjects.mockResolvedValue(MOCK_PROJECTS);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('active')).toBeInTheDocument();
        expect(screen.getByText('draft')).toBeInTheDocument();
      });
    });
  });
});
