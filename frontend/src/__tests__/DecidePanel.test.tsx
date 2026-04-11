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
const mockRunAllMutateAsync = vi.fn().mockResolvedValue({ status: "completed" });
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
  useRunAllSimulation: () => ({
    mutateAsync: mockRunAllMutateAsync,
    isPending: false,
  }),
  useExportSimulation: () => mockExport,
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
    mockRunAllMutateAsync.mockClear();
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
});
