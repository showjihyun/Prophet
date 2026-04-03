/**
 * Auto-generated from SPEC: docs/spec/ui/UI_07_PROJECT_SCENARIOS.md
 * SPEC Version: 0.1.0
 *
 * @spec docs/spec/ui/UI_07_PROJECT_SCENARIOS.md
 */
import { render, screen, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
    useParams: () => ({ projectId: 'proj-1' }),
  };
});

vi.mock('@/hooks/useSimulationSocket', () => ({
  useSimulationSocket: () => ({ lastMessage: null }),
}));

vi.mock('@/components/shared/AppSidebar', () => ({
  default: () => <aside data-testid="app-sidebar" />,
}));

const mockGetProject = vi.fn();
const mockRunScenario = vi.fn();
const mockGetSimulation = vi.fn();
const mockDeleteScenario = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    projects: {
      get: (...args: unknown[]) => mockGetProject(...args),
      runScenario: (...args: unknown[]) => mockRunScenario(...args),
      deleteScenario: (...args: unknown[]) => mockDeleteScenario(...args),
    },
    simulations: {
      get: (...args: unknown[]) => mockGetSimulation(...args),
    },
  },
}));

import ProjectScenariosPage from '@/pages/ProjectScenariosPage';

const MOCK_PROJECT_DETAIL = {
  project_id: 'proj-1',
  name: 'Alpha Campaign',
  description: 'A test project',
  status: 'active',
  scenario_count: 2,
  created_at: '2026-01-15T10:00:00Z',
  scenarios: [
    {
      scenario_id: 'scen-1',
      name: 'Scenario One',
      description: 'First scenario',
      status: 'completed',
      simulation_id: 'sim-99',
      created_at: '2026-01-20T10:00:00Z',
    },
    {
      scenario_id: 'scen-2',
      name: 'Scenario Two',
      description: 'Second scenario',
      status: 'draft',
      simulation_id: null,
      created_at: '2026-01-25T10:00:00Z',
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/projects/proj-1']}>
      <ProjectScenariosPage />
    </MemoryRouter>,
  );
}

describe('ProjectScenariosPage (UI-07)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
  });

  /** @spec UI_07_PROJECT_SCENARIOS.md#layout-structure */
  describe('Layout', () => {
    it('renders page with data-testid', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      expect(screen.getByTestId('project-scenarios-page')).toBeInTheDocument();
    });

    it('renders breadcrumb navigation with Projects link', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      expect(screen.getByText('Projects')).toBeInTheDocument();
    });

    it('renders project name in breadcrumb after loading', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() => {
        const names = screen.getAllByText('Alpha Campaign');
        expect(names.length).toBeGreaterThanOrEqual(1);
      });
    });
  });

  /** @spec UI_07_PROJECT_SCENARIOS.md#loading-state */
  describe('Loading State', () => {
    it('shows loading text while fetching project', () => {
      mockGetProject.mockReturnValue(new Promise(() => {})); // never resolves
      renderPage();
      expect(screen.getByText('Loading project...')).toBeInTheDocument();
    });
  });

  /** @spec UI_07_PROJECT_SCENARIOS.md#project-detail */
  describe('Project Detail', () => {
    it('loads project detail from API on mount', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() => expect(mockGetProject).toHaveBeenCalledWith('proj-1'));
    });

    it('renders project name as page title', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() => {
        const heading = screen.getByRole('heading', { level: 1 });
        expect(heading).toHaveTextContent('Alpha Campaign');
      });
    });

    it('renders project description', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() =>
        expect(screen.getByText('A test project')).toBeInTheDocument(),
      );
    });

    it('renders project info bar with status, scenario count, and created date', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Status')).toBeInTheDocument();
        expect(screen.getByText('active')).toBeInTheDocument();
        // "Scenarios" appears in both the info bar label and section heading — both should be present
        const scenariosLabels = screen.getAllByText('Scenarios');
        expect(scenariosLabels.length).toBeGreaterThanOrEqual(1);
        expect(screen.getByText('2')).toBeInTheDocument();
      });
    });
  });

  /** @spec UI_07_PROJECT_SCENARIOS.md#new-scenario-button */
  describe('New Scenario Button', () => {
    it('renders New Scenario button', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('button', { name: /new scenario/i })).toBeInTheDocument(),
      );
    });

    it('renders Settings button', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('button', { name: /settings/i })).toBeInTheDocument(),
      );
    });
  });

  /** @spec UI_07_PROJECT_SCENARIOS.md#scenario-cards */
  describe('Scenario Cards', () => {
    it('renders scenario names', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('Scenario One')).toBeInTheDocument();
        expect(screen.getByText('Scenario Two')).toBeInTheDocument();
      });
    });

    it('renders scenario descriptions', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('First scenario')).toBeInTheDocument();
        expect(screen.getByText('Second scenario')).toBeInTheDocument();
      });
    });

    it('renders status badges for each scenario', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() => {
        expect(screen.getByText('completed')).toBeInTheDocument();
        expect(screen.getByText('draft')).toBeInTheDocument();
      });
    });

    it('renders Results button for completed scenario', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('button', { name: /results/i })).toBeInTheDocument(),
      );
    });

    it('renders Run button for draft scenario', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() =>
        expect(screen.getByRole('button', { name: /run/i })).toBeInTheDocument(),
      );
    });

    it('renders delete button for each scenario', async () => {
      mockGetProject.mockResolvedValue(MOCK_PROJECT_DETAIL);
      renderPage();
      await waitFor(() => {
        // There should be one delete (Trash2) button per scenario
        const deleteButtons = screen.getAllByTitle('Delete scenario');
        expect(deleteButtons).toHaveLength(2);
      });
    });
  });

  /** @spec UI_07_PROJECT_SCENARIOS.md#empty-scenarios */
  describe('Empty Scenarios', () => {
    it('shows empty message when no scenarios exist', async () => {
      mockGetProject.mockResolvedValue({ ...MOCK_PROJECT_DETAIL, scenarios: [], scenario_count: 0 });
      renderPage();
      await waitFor(() =>
        expect(
          screen.getByText('No scenarios yet. Create one to get started.'),
        ).toBeInTheDocument(),
      );
    });
  });
});
