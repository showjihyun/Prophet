/**
 * SimulationListPage — Project Scoping & Filtering tests (§10).
 *
 * Auto-generated from SPEC: docs/spec/18_FRONTEND_PERFORMANCE_SPEC.md#10
 * SPEC Version: 0.1.0
 * Generated BEFORE implementation — tests define the contract.
 *
 * Covers SL-AC-01 through SL-AC-09.
 */
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { MemoryRouter } from 'react-router-dom';

// ── Route navigation mock ─────────────────────────────────────────────
const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return { ...actual, useNavigate: () => mockNavigate };
});

// ── Sidebar stub (SimulationListPage is rendered inside Layout) ────────
vi.mock('@/components/shared/AppSidebar', () => ({
  default: () => <aside data-testid="app-sidebar" />,
}));

// ── apiClient mock — controls useProjects() / useSimulations() data ────
const mockListProjects = vi.fn();
const mockListSimulations = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    projects: {
      list: (...args: unknown[]) => mockListProjects(...args),
    },
    simulations: {
      list: (...args: unknown[]) => mockListSimulations(...args),
    },
  },
}));

import SimulationListPage from '@/pages/SimulationListPage';

// ── Fixtures ───────────────────────────────────────────────────────────
const MOCK_PROJECTS = [
  {
    project_id: 'proj-q4',
    name: 'Q4 Campaigns',
    description: '',
    status: 'active',
    scenario_count: 2,
    created_at: '2026-01-01T00:00:00Z',
  },
  {
    project_id: 'proj-health',
    name: 'Public Health Pilot',
    description: '',
    status: 'active',
    scenario_count: 1,
    created_at: '2026-02-01T00:00:00Z',
  },
];

const MOCK_SIMS = {
  items: [
    {
      simulation_id: 'sim-q4-aaa',
      project_id: 'proj-q4',
      scenario_id: 'scen-1',
      name: 'Beverage Launch',
      status: 'running',
      current_step: 5,
      max_steps: 50,
      created_at: '2026-04-01T10:00:00Z',
      config: {} as never,
    },
    {
      simulation_id: 'sim-q4-bbb',
      project_id: 'proj-q4',
      scenario_id: 'scen-2',
      name: 'Sustainability Test',
      status: 'completed',
      current_step: 50,
      max_steps: 50,
      created_at: '2026-04-02T10:00:00Z',
      config: {} as never,
    },
    {
      simulation_id: 'sim-health-ccc',
      project_id: 'proj-health',
      scenario_id: 'scen-3',
      name: 'Vaccine Message A',
      status: 'paused',
      current_step: 12,
      max_steps: 30,
      created_at: '2026-04-03T10:00:00Z',
      config: {} as never,
    },
    {
      // Orphan: project_id references a project that no longer exists
      simulation_id: 'sim-orphan-ddd',
      project_id: 'proj-deleted',
      scenario_id: 'scen-4',
      name: 'Orphan Run',
      status: 'failed',
      current_step: 3,
      max_steps: 20,
      created_at: '2026-04-04T10:00:00Z',
      config: {} as never,
    },
  ],
};

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/simulation']}>
      <SimulationListPage />
    </MemoryRouter>,
  );
}

// ── Tests ──────────────────────────────────────────────────────────────

describe('SimulationListPage — Project Scoping (§10)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockNavigate.mockReset();
    // Happy-path defaults; individual tests override as needed.
    mockListProjects.mockResolvedValue(MOCK_PROJECTS);
    mockListSimulations.mockResolvedValue(MOCK_SIMS);
  });

  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#SL-01 */
  describe('SL-AC-01: default filter state', () => {
    it('mounts with an "All projects" filter dropdown selected by default', async () => {
      renderPage();
      const filter = await screen.findByTestId('simulation-list-project-filter');
      expect(filter).toBeInTheDocument();
      // Native <select>: its `value` reflects the current selection.
      // "All projects" is represented by empty string (null → "").
      expect((filter as HTMLSelectElement).value).toBe('');
    });

    it('dropdown includes an option per project from useProjects()', async () => {
      renderPage();
      await screen.findByTestId('simulation-list-project-filter');
      // Wait for the projects query to resolve before asserting dynamic options.
      await screen.findByRole('option', { name: 'Q4 Campaigns' });
      expect(screen.getByRole('option', { name: /all projects/i })).toBeInTheDocument();
      expect(screen.getByRole('option', { name: 'Public Health Pilot' })).toBeInTheDocument();
    });
  });

  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#SL-02 */
  describe('SL-AC-02: filter application', () => {
    it('shows only simulations matching the selected project', async () => {
      renderPage();
      // Wait for both queries to resolve
      await screen.findByTestId('simulation-row-sim-q4-aaa');

      // Before filter: all 4 sims (including orphan)
      expect(screen.getByTestId('simulation-row-sim-q4-aaa')).toBeInTheDocument();
      expect(screen.getByTestId('simulation-row-sim-q4-bbb')).toBeInTheDocument();
      expect(screen.getByTestId('simulation-row-sim-health-ccc')).toBeInTheDocument();
      expect(screen.getByTestId('simulation-row-sim-orphan-ddd')).toBeInTheDocument();

      // Apply filter: Q4 project
      const filter = screen.getByTestId('simulation-list-project-filter');
      fireEvent.change(filter, { target: { value: 'proj-q4' } });

      // After filter: only Q4 sims
      expect(screen.getByTestId('simulation-row-sim-q4-aaa')).toBeInTheDocument();
      expect(screen.getByTestId('simulation-row-sim-q4-bbb')).toBeInTheDocument();
      expect(screen.queryByTestId('simulation-row-sim-health-ccc')).not.toBeInTheDocument();
      expect(screen.queryByTestId('simulation-row-sim-orphan-ddd')).not.toBeInTheDocument();
    });
  });

  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#SL-03 */
  describe('SL-AC-03: New Simulation with "All projects" selected', () => {
    it('navigates to /setup (no project in URL)', async () => {
      renderPage();
      await screen.findByTestId('simulation-list-project-filter');
      const newButton = screen.getByRole('button', { name: /new simulation/i });
      fireEvent.click(newButton);
      expect(mockNavigate).toHaveBeenCalledWith('/setup');
    });
  });

  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#SL-03 */
  describe('SL-AC-04: New Simulation with a project filter selected', () => {
    it('navigates to /setup/:projectId', async () => {
      renderPage();
      const filter = await screen.findByTestId('simulation-list-project-filter');
      // Wait for the Q4 option to exist before selecting it.
      await screen.findByRole('option', { name: 'Q4 Campaigns' });
      fireEvent.change(filter, { target: { value: 'proj-q4' } });

      const newButton = screen.getByRole('button', { name: /new simulation/i });
      fireEvent.click(newButton);
      expect(mockNavigate).toHaveBeenCalledWith('/setup/proj-q4');
    });
  });

  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#SL-04 */
  describe('SL-AC-05: per-row project name for known project', () => {
    it('renders "{simulation_id} · {project_name}" inline below the simulation name', async () => {
      renderPage();
      const row = await screen.findByTestId('simulation-row-sim-q4-aaa');
      // Middle-dot separator + project name must appear in the same row
      expect(row.textContent).toContain('sim-q4-aaa');
      expect(row.textContent).toContain('·');
      expect(row.textContent).toContain('Q4 Campaigns');
    });
  });

  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#SL-04 */
  describe('SL-AC-06: orphan simulation (unknown project_id)', () => {
    it('renders simulation_id without the middle-dot separator and without crashing', async () => {
      renderPage();
      const row = await screen.findByTestId('simulation-row-sim-orphan-ddd');
      expect(row.textContent).toContain('sim-orphan-ddd');
      // Orphan fallback: no middle-dot, no project label
      expect(row.textContent).not.toContain('·');
      // Also: no deleted project name leaks through
      expect(row.textContent).not.toContain('proj-deleted');
    });
  });

  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#SL-05 */
  describe('SL-AC-07: filtered empty state', () => {
    it('shows "No simulations in this project" copy when the filtered set is empty', async () => {
      // Project exists but has zero sims. Replace sims with a health-only set, then filter by q4.
      mockListSimulations.mockResolvedValue({
        items: [MOCK_SIMS.items[2]], // health sim only
      });
      renderPage();
      const filter = await screen.findByTestId('simulation-list-project-filter');
      // Wait for projects to load so the Q4 option is available to select.
      await screen.findByRole('option', { name: 'Q4 Campaigns' });
      fireEvent.change(filter, { target: { value: 'proj-q4' } });

      // Filtered empty state has its own test id and copy
      expect(
        await screen.findByTestId('simulation-list-empty-filtered'),
      ).toBeInTheDocument();
      expect(screen.getByText(/no simulations in this project/i)).toBeInTheDocument();
      expect(
        screen.getByRole('button', { name: /create in this project/i }),
      ).toBeInTheDocument();
    });

    it('the filtered empty state CTA navigates to /setup/:projectId', async () => {
      mockListSimulations.mockResolvedValue({
        items: [MOCK_SIMS.items[2]],
      });
      renderPage();
      const filter = await screen.findByTestId('simulation-list-project-filter');
      await screen.findByRole('option', { name: 'Q4 Campaigns' });
      fireEvent.change(filter, { target: { value: 'proj-q4' } });

      const cta = await screen.findByRole('button', {
        name: /create in this project/i,
      });
      fireEvent.click(cta);
      expect(mockNavigate).toHaveBeenCalledWith('/setup/proj-q4');
    });
  });

  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#SL-01 */
  describe('SL-AC-08: projects query loading', () => {
    it('renders the dropdown with "All projects" only while projects are loading', async () => {
      // Projects never resolve — stay in loading
      mockListProjects.mockImplementation(() => new Promise(() => {}));
      // Sims resolve normally so the page body can render
      renderPage();

      const filter = await screen.findByTestId('simulation-list-project-filter');
      // Just the "All projects" option
      expect(screen.getByRole('option', { name: /all projects/i })).toBeInTheDocument();
      expect(
        screen.queryByRole('option', { name: 'Q4 Campaigns' }),
      ).not.toBeInTheDocument();
      // Page did not crash
      expect(filter).toBeInTheDocument();
    });
  });

  /** @spec 18_FRONTEND_PERFORMANCE_SPEC.md#SL-01 */
  describe('SL-AC-09: projects query error', () => {
    it('falls back to "All projects" only; simulation list still renders', async () => {
      mockListProjects.mockRejectedValue(new Error('boom'));
      renderPage();

      const filter = await screen.findByTestId('simulation-list-project-filter');
      expect(filter).toBeInTheDocument();
      expect(screen.getByRole('option', { name: /all projects/i })).toBeInTheDocument();

      // Simulation rows still render (the sims query is independent)
      await waitFor(() => {
        expect(screen.getByTestId('simulation-row-sim-q4-aaa')).toBeInTheDocument();
      });
    });
  });
});
