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
import { useNavigate } from "react-router-dom";
import { Plus, Brain } from "lucide-react";
import ControlPanel from "../components/control/ControlPanel";
import CommunityPanel from "../components/graph/CommunityPanel";
import GraphPanel from "../components/graph/GraphPanel";
import MetricsPanel from "../components/graph/MetricsPanel";
import TimelinePanel from "../components/timeline/TimelinePanel";
import ConversationPanel from "../components/control/ConversationPanel";
import LLMDashboard from "../components/llm/LLMDashboard";
import { useSimulationSocket } from "../hooks/useSimulationSocket";
import { useSimulationStore } from "../store/simulationStore";
import type { StepResult, EmergentEvent, SimulationStatus } from "../types/simulation";

export default function SimulationPage() {
  const navigate = useNavigate();
  const simulation = useSimulationStore((s) => s.simulation);
  const appendStep = useSimulationStore((s) => s.appendStep);
  const appendEmergentEvent = useSimulationStore((s) => s.appendEmergentEvent);
  const setStatus = useSimulationStore((s) => s.setStatus);
  const isLLMDashboardOpen = useSimulationStore((s) => s.isLLMDashboardOpen);

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

  if (!simulation) {
    return (
      <div className="h-screen w-screen flex flex-col bg-[var(--background)]">
        <ControlPanel />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center flex flex-col items-center gap-4">
            <Brain className="w-16 h-16 text-[var(--muted-foreground)]" />
            <h2 className="text-xl font-semibold text-[var(--foreground)]">No Active Simulation</h2>
            <p className="text-sm text-[var(--muted-foreground)] max-w-md">
              Create a new simulation to start analyzing campaign diffusion across your virtual social network.
            </p>
            <button
              onClick={() => navigate("/setup")}
              className="h-10 px-6 text-sm font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              <Plus className="w-4 h-4" />
              Create New Simulation
            </button>
          </div>
        </div>
      </div>
    );
  }

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

      {/* LLM Dashboard — collapsible overlay at bottom */}
      {isLLMDashboardOpen && (
        <div className="shrink-0 border-t border-[var(--border)] bg-[var(--card)]">
          <LLMDashboard />
        </div>
      )}
    </div>
  );
}
