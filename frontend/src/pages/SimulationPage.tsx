/**
 * SimulationPage — Main simulation workspace (UI-01).
 * @spec docs/spec/07_FRONTEND_SPEC.md#simulation-dashboard
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md
 *
 * Layout (4 horizontal zones):
 * Zone 1: Simulation Control Bar (56px)
 * Zone 2: Community Panel (260px) | Graph Engine (fill) | Metrics Panel (280px)
 * Zone 3: Timeline (120px) + Conversations (fill remaining)
 */
import { useEffect } from "react";
import ControlPanel from "../components/control/ControlPanel";
import CommunityPanel from "../components/graph/CommunityPanel";
import GraphPanel from "../components/graph/GraphPanel";
import MetricsPanel from "../components/graph/MetricsPanel";
import TimelinePanel from "../components/timeline/TimelinePanel";
import ConversationPanel from "../components/control/ConversationPanel";
import { useSimulationSocket } from "../hooks/useSimulationSocket";
import { useSimulationStore } from "../store/simulationStore";
import type { StepResult, EmergentEvent, SimulationStatus } from "../types/simulation";

export default function SimulationPage() {
  const simulation = useSimulationStore((s) => s.simulation);
  const appendStep = useSimulationStore((s) => s.appendStep);
  const appendEmergentEvent = useSimulationStore((s) => s.appendEmergentEvent);
  const setStatus = useSimulationStore((s) => s.setStatus);

  const simulationId = simulation?.simulation_id ?? null;
  const { lastMessage } = useSimulationSocket(simulationId);

  useEffect(() => {
    if (!lastMessage) return;
    switch (lastMessage.type) {
      case 'step_result':
        appendStep(lastMessage.data as StepResult);
        break;
      case 'emergent_event':
        appendEmergentEvent(lastMessage.data as EmergentEvent);
        break;
      case 'status_change':
        setStatus((lastMessage.data as { status: SimulationStatus }).status);
        break;
    }
  }, [lastMessage, appendStep, appendEmergentEvent, setStatus]);
  return (
    <div
      data-testid="simulation-page"
      className="h-screen w-screen flex flex-col overflow-hidden bg-[var(--background)]"
    >
      {/* Zone 1: Simulation Control Bar — 56px */}
      <ControlPanel />

      {/* Zone 2: Middle Content — fills available space */}
      <div className="flex flex-1 min-h-0">
        {/* Left: Community Panel — 260px */}
        <CommunityPanel />

        {/* Center: AI Social World Graph Engine — fill */}
        <div className="flex-1 min-w-0">
          <GraphPanel />
        </div>

        {/* Right: Metrics Panel — 280px */}
        <MetricsPanel />
      </div>

      {/* Zone 3: Bottom Area — 220px */}
      <div className="shrink-0" style={{ height: "var(--bottom-area-height)" }}>
        {/* Timeline + Diffusion Wave — 120px */}
        <TimelinePanel />

        {/* Conversations / Expert Agent — remaining */}
        <ConversationPanel />
      </div>
    </div>
  );
}
