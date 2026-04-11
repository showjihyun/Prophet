/**
 * Pure helpers for the WorkflowStepper component.
 *
 * Separated from WorkflowStepper.tsx so Vite's react-refresh plugin can
 * hot-reload the component in isolation (rule: component files must only
 * export components).
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#workflow-stepper
 */
import {
  SIM_STATUS,
  TERMINAL_SIM_STATUSES,
} from "@/config/constants";
import type { SimulationStatus } from "@/types/simulation";

export type StageState = "pending" | "active" | "completed";

export interface WorkflowStage {
  id: "generate" | "inject" | "simulate" | "detect" | "visualize" | "decide";
  label: string;
  description: string;
  state: StageState;
}

export interface StageDerivationInput {
  hasSimulation: boolean;
  status: SimulationStatus;
  emergentCount: number;
  stepsCount: number;
}

/**
 * Pure function that maps the current store snapshot onto the 6 workflow
 * stages. Kept separate so it can be unit-tested without mounting React.
 */
export function deriveWorkflowStages(
  input: StageDerivationInput,
): WorkflowStage[] {
  const { hasSimulation, status, emergentCount, stepsCount } = input;
  const isTerminal = (TERMINAL_SIM_STATUSES as readonly SimulationStatus[]).includes(status);
  const isRunning = status === SIM_STATUS.RUNNING;
  const isPaused = status === SIM_STATUS.PAUSED;
  const isConfigured = status === SIM_STATUS.CONFIGURED;
  const hasSteps = stepsCount > 0;

  const pending = <S extends StageState>(): S => "pending" as S;

  return [
    {
      id: "generate",
      label: "Generate",
      description: "Build agents & network",
      state: hasSimulation ? "completed" : "active",
    },
    {
      id: "inject",
      label: "Inject",
      description: "Campaign / events",
      state: !hasSimulation
        ? pending()
        : isConfigured || isPaused
          ? "active"
          : hasSteps || isTerminal
            ? "completed"
            : pending(),
    },
    {
      id: "simulate",
      label: "Simulate",
      description: "Agents tick forward",
      state: !hasSimulation
        ? pending()
        : isRunning || isPaused
          ? "active"
          : isTerminal
            ? "completed"
            : pending(),
    },
    {
      id: "detect",
      label: "Detect",
      description: "Emergent events",
      state: !hasSimulation
        ? pending()
        : emergentCount > 0 && !isTerminal
          ? "active"
          : emergentCount > 0 && isTerminal
            ? "completed"
            : pending(),
    },
    {
      id: "visualize",
      label: "Visualize",
      description: "3D network render",
      state: !hasSimulation
        ? pending()
        : hasSteps && !isTerminal
          ? "active"
          : isTerminal
            ? "completed"
            : pending(),
    },
    {
      id: "decide",
      label: "Decide",
      description: "Compare / export",
      state: !hasSimulation
        ? pending()
        : isTerminal
          ? "active"
          : pending(),
    },
  ];
}
