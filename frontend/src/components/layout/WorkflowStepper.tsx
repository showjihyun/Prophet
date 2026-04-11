/**
 * WorkflowStepper — 6-stage progress indicator for the Prophet pipeline.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#workflow-stepper
 *
 * Makes the implicit Generate → Inject → Simulate → Detect → Visualize →
 * Decide workflow explicit in the UI. Each stage is derived from the
 * current simulation status + emergent events so the user always sees
 * "where they are" without memorizing the flow.
 *
 * Pure derivation helpers live in ``./workflowStepperUtils`` to keep this
 * file component-only (Vite react-refresh rule).
 */
import { memo } from "react";
import { Check } from "lucide-react";
import { useSimulationStore } from "../../store/simulationStore";
import {
  deriveWorkflowStages,
  type StageState,
  type WorkflowStage,
} from "./workflowStepperUtils";

// --------------------------------------------------------------------------- //
// Component                                                                   //
// --------------------------------------------------------------------------- //

function StageNode({ stage, index }: { stage: WorkflowStage; index: number }) {
  const base =
    "flex items-center justify-center w-7 h-7 rounded-full text-xs font-semibold transition-colors";
  const label =
    "flex flex-col items-start leading-tight min-w-0";

  const styles: Record<StageState, { circle: string; label: string; desc: string }> = {
    pending: {
      circle: "bg-[var(--secondary)] text-[var(--muted-foreground)] border border-[var(--border)]",
      label: "text-[var(--muted-foreground)]",
      desc: "text-[var(--muted-foreground)]/60",
    },
    active: {
      circle:
        "bg-[var(--primary)] text-[var(--primary-foreground)] ring-2 ring-[var(--primary)]/40 animate-pulse",
      label: "text-[var(--foreground)] font-semibold",
      desc: "text-[var(--muted-foreground)]",
    },
    completed: {
      circle: "bg-emerald-600 text-white",
      label: "text-[var(--foreground)]",
      desc: "text-[var(--muted-foreground)]",
    },
  };

  const s = styles[stage.state];

  return (
    <div
      className="flex items-center gap-2 min-w-0"
      data-testid={`stepper-stage-${stage.id}`}
      data-state={stage.state}
    >
      <div className={`${base} ${s.circle}`} aria-hidden="true">
        {stage.state === "completed" ? <Check className="w-4 h-4" /> : index + 1}
      </div>
      <div className={label}>
        <span className={`text-xs ${s.label}`}>{stage.label}</span>
        <span className={`text-[10px] ${s.desc} hidden lg:inline`}>
          {stage.description}
        </span>
      </div>
    </div>
  );
}

function StageConnector({ leftState }: { leftState: StageState }) {
  const color =
    leftState === "completed"
      ? "bg-emerald-600"
      : leftState === "active"
        ? "bg-[var(--primary)]/50"
        : "bg-[var(--border)]";
  return (
    <div
      className={`h-px flex-1 min-w-4 ${color} transition-colors`}
      aria-hidden="true"
    />
  );
}

function WorkflowStepper() {
  const simulation = useSimulationStore((s) => s.simulation);
  const status = useSimulationStore((s) => s.status);
  const emergentCount = useSimulationStore((s) => s.emergentEvents.length);
  const stepsCount = useSimulationStore((s) => s.steps.length);

  const stages = deriveWorkflowStages({
    hasSimulation: !!simulation,
    status,
    emergentCount,
    stepsCount,
  });

  return (
    <nav
      aria-label="Simulation workflow progress"
      data-testid="workflow-stepper"
      className="flex items-center gap-2 px-4 py-2 border-b border-[var(--border)] bg-[var(--card)] overflow-x-auto"
    >
      {stages.map((stage, idx) => (
        <div key={stage.id} className="flex items-center gap-2 shrink-0">
          <StageNode stage={stage} index={idx} />
          {idx < stages.length - 1 && <StageConnector leftState={stage.state} />}
        </div>
      ))}
    </nav>
  );
}

export default memo(WorkflowStepper);
