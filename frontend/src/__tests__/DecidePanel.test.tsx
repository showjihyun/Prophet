/**
 * DecidePanel tests — tab switching, export trigger, compare flow.
 * @spec docs/spec/07_FRONTEND_SPEC.md#decide-panel
 */
import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MemoryRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import DecidePanel from "@/components/decide/DecidePanel";
import { useSimulationStore } from "@/store/simulationStore";
import { SIM_STATUS } from "@/config/constants";
import type { SimulationRun } from "@/types/simulation";

// Mock useNavigate so we can assert navigation without a real router
const mockNavigate = vi.fn();
vi.mock("react-router-dom", async () => {
  const actual = await vi.importActual("react-router-dom");
  return { ...actual, useNavigate: () => mockNavigate };
});

// Mock queries.ts (DecidePanel consumes hooks, not raw apiClient)
const mockExport = vi.fn();
const mockMonteCarloMutateAsync = vi.fn().mockResolvedValue({
  simulation_id: "sim-current",
  n_runs: 10,
  viral_probability: 0.7,
  expected_reach: 412.3,
  p5_reach: 280,
  p50_reach: 415,
  p95_reach: 612,
  community_adoption: {},
  run_summaries: [],
});
vi.mock("@/api/queries", () => ({
  useSimulations: () => ({
    data: {
      items: [
        { simulation_id: "sim-other", name: "Other", status: "completed" },
      ],
      total: 1,
    },
    isLoading: false,
  }),
  useRunMonteCarlo: () => ({
    mutateAsync: mockMonteCarloMutateAsync,
    isPending: false,
  }),
  exportSimulation: () => mockExport,
}));

function renderPanel() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <DecidePanel onClose={vi.fn()} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("<DecidePanel />", () => {
  beforeEach(() => {
    mockNavigate.mockClear();
    mockExport.mockClear();
    mockMonteCarloMutateAsync.mockClear();
    useSimulationStore.setState({
      simulation: {
        simulation_id: "sim-current",
        status: SIM_STATUS.COMPLETED,
      } as SimulationRun,
      status: SIM_STATUS.COMPLETED,
    });
  });

  it("renders all three tabs (compare / monte carlo / export)", () => {
    renderPanel();
    expect(screen.getByTestId("decide-tab-compare")).toBeInTheDocument();
    expect(screen.getByTestId("decide-tab-monte_carlo")).toBeInTheDocument();
    expect(screen.getByTestId("decide-tab-export")).toBeInTheDocument();
  });

  it("defaults to the compare tab", () => {
    renderPanel();
    expect(screen.getByTestId("decide-compare-select")).toBeInTheDocument();
  });

  it("switches to Monte Carlo tab when clicked", () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("decide-tab-monte_carlo"));
    expect(screen.getByTestId("decide-mc-runs-slider")).toBeInTheDocument();
    expect(screen.getByTestId("decide-mc-run")).toBeInTheDocument();
  });

  it("switches to Export tab and triggers export on submit", () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("decide-tab-export"));
    fireEvent.click(screen.getByTestId("decide-export-format-csv"));
    fireEvent.click(screen.getByTestId("decide-export-submit"));
    expect(mockExport).toHaveBeenCalledWith("sim-current", "csv");
  });

  it("export defaults to json format", () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("decide-tab-export"));
    fireEvent.click(screen.getByTestId("decide-export-submit"));
    expect(mockExport).toHaveBeenCalledWith("sim-current", "json");
  });

  it("compare submit is disabled until another sim is chosen", () => {
    renderPanel();
    const submit = screen.getByTestId("decide-compare-submit") as HTMLButtonElement;
    expect(submit).toBeDisabled();
  });

  /** @spec 24_UI_WORKFLOW_SPEC.md#2.3.4 — DP-AC-07 */
  it("compare navigates to /simulation/:simulationId/compare/:otherId (both IDs in URL)", () => {
    renderPanel();
    fireEvent.change(screen.getByTestId("decide-compare-select"), {
      target: { value: "sim-other" },
    });
    fireEvent.click(screen.getByTestId("decide-compare-submit"));
    expect(mockNavigate).toHaveBeenCalledWith(
      "/simulation/sim-current/compare/sim-other",
    );
  });

  /** @spec 29_MONTE_CARLO_SPEC.md — MC-AC-06 */
  it("Monte Carlo slider min=2 max=50 (single-seed is not MC)", () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("decide-tab-monte_carlo"));
    const slider = screen.getByTestId("decide-mc-runs-slider") as HTMLInputElement;
    expect(slider.min).toBe("2");
    expect(slider.max).toBe("50");
  });

  /** @spec 29_MONTE_CARLO_SPEC.md — MC-AC-07 */
  it("Monte Carlo Run calls the real /monte-carlo endpoint, not run-all", async () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("decide-tab-monte_carlo"));
    fireEvent.click(screen.getByTestId("decide-mc-run"));
    expect(mockMonteCarloMutateAsync).toHaveBeenCalledWith(
      expect.objectContaining({ simId: "sim-current", n_runs: 10 }),
    );
  });

  /** @spec 29_MONTE_CARLO_SPEC.md — MC-AC-08 */
  it("renders viral probability + expected reach after a successful sweep", async () => {
    renderPanel();
    fireEvent.click(screen.getByTestId("decide-tab-monte_carlo"));
    fireEvent.click(screen.getByTestId("decide-mc-run"));
    // Mutation resolves synchronously in our mock; flush microtasks.
    await Promise.resolve();
    await Promise.resolve();
    const result = await screen.findByTestId("decide-mc-result");
    expect(result).toBeInTheDocument();
    expect(screen.getByTestId("decide-mc-viral-prob")).toHaveTextContent("70%");
    expect(screen.getByTestId("decide-mc-expected")).toHaveTextContent("412");
  });
});
