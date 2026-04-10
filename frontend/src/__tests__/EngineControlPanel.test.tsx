/**
 * EngineControlPanel — unit tests for SLM/LLM ratio modal.
 *
 * Covers:
 * - Render when open/closed
 * - Slider interaction updates ratio
 * - Apply button gated to PAUSED status
 * - Escape key closes modal
 * - Impact indicators display after apply
 * - Mode label derivation (Quality/Balanced/Speed)
 * - Tier distribution badges display
 * - Budget input
 * - Backdrop click closes modal
 *
 * @spec docs/spec/05_LLM_SPEC.md#71-user-engine-control-slmllm-ratio
 */
import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { useSimulationStore } from "../store/simulationStore";
import { SIM_STATUS } from "@/config/constants";

const mockMutateAsync = vi.fn();

vi.mock("@/api/queries", () => ({
  useEngineControl: () => ({
    mutateAsync: mockMutateAsync,
    isPending: false,
  }),
}));

import EngineControlPanel from "@/components/control/EngineControlPanel";

const MOCK_SIMULATION = {
  simulation_id: "sim-ec-001",
  project_id: "proj-001",
  scenario_id: "scen-001",
  status: "paused" as const,
  current_step: 5,
  max_steps: 365,
  created_at: new Date().toISOString(),
  config: {} as never,
};

const MOCK_ENGINE_RESPONSE = {
  tier_distribution: {
    tier1_count: 800,
    tier2_count: 100,
    tier3_count: 100,
    tier1_model: "phi4",
    tier3_model: "claude-sonnet-4-6-20250514",
    estimated_cost_per_step: 0.30,
    estimated_latency_ms: 250,
  },
  impact_assessment: {
    cost_efficiency: "$0.30 per step",
    reasoning_depth: "Balanced",
    simulation_velocity: "~250ms per step",
    prediction_type: "Hybrid",
  },
};

describe("EngineControlPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useSimulationStore.setState({
      simulation: MOCK_SIMULATION,
      status: SIM_STATUS.PAUSED,
      slmLlmRatio: 0.5,
    });
  });

  describe("visibility", () => {
    it("renders nothing when isOpen is false", () => {
      const { container } = render(
        <EngineControlPanel isOpen={false} onClose={vi.fn()} />,
      );
      expect(container.firstChild).toBeNull();
    });

    it("renders modal when isOpen is true", () => {
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Engine Control")).toBeInTheDocument();
    });
  });

  describe("mode label", () => {
    it("shows Balanced for ratio=0.5", () => {
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      expect(screen.getByText("Balanced")).toBeInTheDocument();
    });

    it("shows Quality for ratio < 0.3", () => {
      useSimulationStore.setState({ slmLlmRatio: 0.2 });
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      expect(screen.getByText("Quality")).toBeInTheDocument();
    });

    it("shows Speed for ratio > 0.7", () => {
      useSimulationStore.setState({ slmLlmRatio: 0.8 });
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      expect(screen.getByText("Speed")).toBeInTheDocument();
    });
  });

  describe("slider interaction", () => {
    it("displays current SLM percentage", () => {
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      expect(screen.getByText("50% SLM")).toBeInTheDocument();
    });

    it("updates ratio on slider change", () => {
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      const slider = screen.getByRole("slider");
      fireEvent.change(slider, { target: { value: "0.75" } });
      expect(useSimulationStore.getState().slmLlmRatio).toBe(0.75);
    });

    it("slider is disabled when not paused", () => {
      useSimulationStore.setState({ status: SIM_STATUS.RUNNING });
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      const slider = screen.getByRole("slider");
      expect(slider).toBeDisabled();
    });
  });

  describe("apply button gating", () => {
    it("shows 'Apply' when paused", () => {
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      const applyBtn = screen.getByRole("button", { name: /apply/i });
      expect(applyBtn).toBeEnabled();
      expect(applyBtn).toHaveTextContent("Apply");
    });

    it("shows 'Pause to adjust' when running", () => {
      useSimulationStore.setState({ status: SIM_STATUS.RUNNING });
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      const btn = screen.getByText("Pause to adjust");
      expect(btn).toBeDisabled();
    });

    it("calls engineControl mutation on apply", async () => {
      mockMutateAsync.mockResolvedValueOnce(MOCK_ENGINE_RESPONSE);
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      const applyBtn = screen.getByRole("button", { name: /apply/i });
      fireEvent.click(applyBtn);
      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith({
          simId: "sim-ec-001",
          body: { slm_llm_ratio: 0.5, budget_usd: 50 },
        });
      });
    });
  });

  describe("impact display after apply", () => {
    it("shows impact indicators after successful apply", async () => {
      mockMutateAsync.mockResolvedValueOnce(MOCK_ENGINE_RESPONSE);
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      fireEvent.click(screen.getByRole("button", { name: /apply/i }));
      await waitFor(() => {
        expect(screen.getByText("Cost / Step")).toBeInTheDocument();
        expect(screen.getByText("$0.30 per step")).toBeInTheDocument();
        expect(screen.getByText("Reasoning")).toBeInTheDocument();
        expect(screen.getByText("Velocity")).toBeInTheDocument();
        expect(screen.getByText("~250ms per step")).toBeInTheDocument();
        expect(screen.getByText("Prediction")).toBeInTheDocument();
        expect(screen.getByText("Hybrid")).toBeInTheDocument();
      });
    });

    it("shows tier distribution badges after apply", async () => {
      mockMutateAsync.mockResolvedValueOnce(MOCK_ENGINE_RESPONSE);
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      fireEvent.click(screen.getByRole("button", { name: /apply/i }));
      await waitFor(() => {
        expect(screen.getByText("T1: 800")).toBeInTheDocument();
        expect(screen.getByText("T2: 100")).toBeInTheDocument();
        expect(screen.getByText("T3: 100")).toBeInTheDocument();
      });
    });

    it("shows error message on apply failure", async () => {
      mockMutateAsync.mockRejectedValueOnce(new Error("Server error"));
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      fireEvent.click(screen.getByRole("button", { name: /apply/i }));
      await waitFor(() => {
        expect(screen.getByText("Server error")).toBeInTheDocument();
      });
    });
  });

  describe("close behavior", () => {
    it("calls onClose on Escape key", () => {
      const onClose = vi.fn();
      render(<EngineControlPanel isOpen={true} onClose={onClose} />);
      fireEvent.keyDown(screen.getByRole("dialog"), { key: "Escape" });
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("calls onClose on backdrop click", () => {
      const onClose = vi.fn();
      const { container } = render(
        <EngineControlPanel isOpen={true} onClose={onClose} />,
      );
      // Backdrop is the first child div with bg-black/50
      const backdrop = container.querySelector(".bg-black\\/50");
      expect(backdrop).not.toBeNull();
      fireEvent.click(backdrop!);
      expect(onClose).toHaveBeenCalledTimes(1);
    });

    it("calls onClose on X button click", () => {
      const onClose = vi.fn();
      render(<EngineControlPanel isOpen={true} onClose={onClose} />);
      const closeBtn = screen.getByLabelText("Close");
      fireEvent.click(closeBtn);
      expect(onClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("budget input", () => {
    it("renders budget input with default value 50", () => {
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      const budgetInput = screen.getByRole("spinbutton");
      expect(budgetInput).toHaveValue(50);
    });

    it("updates budget on change", () => {
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      const budgetInput = screen.getByRole("spinbutton");
      fireEvent.change(budgetInput, { target: { value: "100" } });
      expect(budgetInput).toHaveValue(100);
    });

    it("clamps budget to non-negative", () => {
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      const budgetInput = screen.getByRole("spinbutton");
      fireEvent.change(budgetInput, { target: { value: "-10" } });
      expect(budgetInput).toHaveValue(0);
    });

    it("sends updated budget in apply call", async () => {
      mockMutateAsync.mockResolvedValueOnce(MOCK_ENGINE_RESPONSE);
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      const budgetInput = screen.getByRole("spinbutton");
      fireEvent.change(budgetInput, { target: { value: "75" } });
      fireEvent.click(screen.getByRole("button", { name: /apply/i }));
      await waitFor(() => {
        expect(mockMutateAsync).toHaveBeenCalledWith(
          expect.objectContaining({
            body: expect.objectContaining({ budget_usd: 75 }),
          }),
        );
      });
    });
  });

  describe("no simulation loaded", () => {
    it("does not call mutation when no simulation", () => {
      useSimulationStore.setState({ simulation: null });
      render(<EngineControlPanel isOpen={true} onClose={vi.fn()} />);
      const applyBtn = screen.getByText(/pause to adjust|apply/i);
      fireEvent.click(applyBtn);
      expect(mockMutateAsync).not.toHaveBeenCalled();
    });
  });
});
