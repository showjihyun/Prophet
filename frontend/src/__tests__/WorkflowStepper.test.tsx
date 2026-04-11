/**
 * WorkflowStepper tests.
 *
 * Pure-function tests for `deriveWorkflowStages` + a minimal render
 * assertion that the component mounts all 6 stages with correct
 * data-state attributes.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#workflow-stepper
 */
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import WorkflowStepper from "@/components/layout/WorkflowStepper";
import { deriveWorkflowStages } from "@/components/layout/workflowStepperUtils";
import { SIM_STATUS } from "@/config/constants";
import { useSimulationStore } from "@/store/simulationStore";
import type { SimulationRun } from "@/types/simulation";

// --------------------------------------------------------------------------- //
// Pure derivation logic                                                       //
// --------------------------------------------------------------------------- //

describe("deriveWorkflowStages", () => {
  it("highlights Generate as active when no simulation exists", () => {
    const stages = deriveWorkflowStages({
      hasSimulation: false,
      status: SIM_STATUS.CREATED,
      emergentCount: 0,
      stepsCount: 0,
    });
    expect(stages).toHaveLength(6);
    const byId = Object.fromEntries(stages.map((s) => [s.id, s]));
    expect(byId.generate.state).toBe("active");
    expect(byId.inject.state).toBe("pending");
    expect(byId.simulate.state).toBe("pending");
    expect(byId.detect.state).toBe("pending");
    expect(byId.visualize.state).toBe("pending");
    expect(byId.decide.state).toBe("pending");
  });

  it("marks Generate completed + Inject active when sim is configured", () => {
    const stages = deriveWorkflowStages({
      hasSimulation: true,
      status: SIM_STATUS.CONFIGURED,
      emergentCount: 0,
      stepsCount: 0,
    });
    const byId = Object.fromEntries(stages.map((s) => [s.id, s]));
    expect(byId.generate.state).toBe("completed");
    expect(byId.inject.state).toBe("active");
    expect(byId.simulate.state).toBe("pending");
  });

  it("marks Simulate + Visualize active when running with steps", () => {
    const stages = deriveWorkflowStages({
      hasSimulation: true,
      status: SIM_STATUS.RUNNING,
      emergentCount: 0,
      stepsCount: 5,
    });
    const byId = Object.fromEntries(stages.map((s) => [s.id, s]));
    expect(byId.generate.state).toBe("completed");
    expect(byId.inject.state).toBe("completed");
    expect(byId.simulate.state).toBe("active");
    expect(byId.visualize.state).toBe("active");
  });

  it("activates Detect when emergent events exist", () => {
    const stages = deriveWorkflowStages({
      hasSimulation: true,
      status: SIM_STATUS.RUNNING,
      emergentCount: 3,
      stepsCount: 10,
    });
    const byId = Object.fromEntries(stages.map((s) => [s.id, s]));
    expect(byId.detect.state).toBe("active");
  });

  it("reactivates Inject when sim is paused (injection window open)", () => {
    const stages = deriveWorkflowStages({
      hasSimulation: true,
      status: SIM_STATUS.PAUSED,
      emergentCount: 0,
      stepsCount: 10,
    });
    const byId = Object.fromEntries(stages.map((s) => [s.id, s]));
    expect(byId.inject.state).toBe("active");
    expect(byId.simulate.state).toBe("active");
  });

  it("activates Decide + marks everything else completed on terminal status", () => {
    const stages = deriveWorkflowStages({
      hasSimulation: true,
      status: SIM_STATUS.COMPLETED,
      emergentCount: 2,
      stepsCount: 50,
    });
    const byId = Object.fromEntries(stages.map((s) => [s.id, s]));
    expect(byId.generate.state).toBe("completed");
    expect(byId.inject.state).toBe("completed");
    expect(byId.simulate.state).toBe("completed");
    expect(byId.detect.state).toBe("completed");
    expect(byId.visualize.state).toBe("completed");
    expect(byId.decide.state).toBe("active");
  });

  it("handles failed terminal state the same as completed for Decide", () => {
    const stages = deriveWorkflowStages({
      hasSimulation: true,
      status: SIM_STATUS.FAILED,
      emergentCount: 0,
      stepsCount: 3,
    });
    const byId = Object.fromEntries(stages.map((s) => [s.id, s]));
    expect(byId.decide.state).toBe("active");
    expect(byId.simulate.state).toBe("completed");
  });
});

// --------------------------------------------------------------------------- //
// Component render                                                            //
// --------------------------------------------------------------------------- //

describe("<WorkflowStepper />", () => {
  it("renders all 6 stages with data-state attributes", () => {
    // Reset store to a known empty state
    useSimulationStore.setState({
      simulation: null,
      status: SIM_STATUS.CREATED,
      emergentEvents: [],
      steps: [],
    });

    render(<WorkflowStepper />);

    const stepper = screen.getByTestId("workflow-stepper");
    expect(stepper).toBeInTheDocument();

    const stageIds = ["generate", "inject", "simulate", "detect", "visualize", "decide"];
    for (const id of stageIds) {
      const el = screen.getByTestId(`stepper-stage-${id}`);
      expect(el).toBeInTheDocument();
      expect(el).toHaveAttribute("data-state");
    }
  });

  it("reflects store state when a simulation is running", () => {
    useSimulationStore.setState({
      simulation: { simulation_id: "abc", status: SIM_STATUS.RUNNING } as SimulationRun,
      status: SIM_STATUS.RUNNING,
      emergentEvents: [],
      steps: [{ step: 1 } as unknown as ReturnType<typeof Object>] as never,
    });

    render(<WorkflowStepper />);

    expect(screen.getByTestId("stepper-stage-generate")).toHaveAttribute(
      "data-state",
      "completed",
    );
    expect(screen.getByTestId("stepper-stage-simulate")).toHaveAttribute(
      "data-state",
      "active",
    );
    expect(screen.getByTestId("stepper-stage-decide")).toHaveAttribute(
      "data-state",
      "pending",
    );
  });
});
