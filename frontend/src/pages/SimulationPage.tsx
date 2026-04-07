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
import { useEffect, useRef, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiClient } from "../api/client";
import { LS_KEY_SIMULATION_ID } from "@/config/constants";
import { FolderOpen, Brain } from "lucide-react";
import ControlPanel from "../components/control/ControlPanel";
import CommunityPanel from "../components/graph/CommunityPanel";
import GraphPanel from "../components/graph/GraphPanel";
import MetricsPanel from "../components/graph/MetricsPanel";
import TimelinePanel from "../components/timeline/TimelinePanel";
import ConversationPanel from "../components/control/ConversationPanel";
import LLMDashboard from "../components/llm/LLMDashboard";
import SimulationReportModal from "../components/shared/SimulationReportModal";
import ToastContainer from "../components/shared/ToastNotification";
import AgentInspector from "../components/agent/AgentInspector";
import { useSimulationSocket } from "../hooks/useSimulationSocket";
import { useSimulationStore } from "../store/simulationStore";
import type { StepResult, EmergentEvent, SimulationStatus } from "../types/simulation";

export default function SimulationPage() {
  const navigate = useNavigate();
  const { simulationId: urlSimId } = useParams<{ simulationId: string }>();
  const simulation = useSimulationStore((s) => s.simulation);
  const appendStep = useSimulationStore((s) => s.appendStep);
  const appendEmergentEvent = useSimulationStore((s) => s.appendEmergentEvent);
  const setStatus = useSimulationStore((s) => s.setStatus);
  const isLLMDashboardOpen = useSimulationStore((s) => s.isLLMDashboardOpen);
  const status = useSimulationStore((s) => s.status);
  // FE-PERF-01: subscribe to length only, not the full array
  const stepsLength = useSimulationStore((s) => s.steps.length);
  const addToast = useSimulationStore((s) => s.addToast);
  const selectedAgentId = useSimulationStore((s) => s.selectedAgentId);
  const isAgentInspectorOpen = useSimulationStore((s) => s.isAgentInspectorOpen);
  const setSimulation = useSimulationStore((s) => s.setSimulation);

  const [reportOpen, setReportOpen] = useState(false);
  // Dedup: track last toast event_type and the timestamp it was shown
  const lastToastRef = useRef<{ type: string; at: number } | null>(null);

  // Restore simulation from URL param or localStorage on mount.
  // @spec docs/spec/06_API_SPEC.md#get-simulationssimulation_id
  useEffect(() => {
    const targetId = urlSimId || (!simulation ? localStorage.getItem(LS_KEY_SIMULATION_ID) : null);
    if (targetId && targetId !== simulation?.simulation_id) {
      apiClient.simulations.get(targetId).then((sim) => {
        setSimulation(sim);
      }).catch(() => {
        localStorage.removeItem(LS_KEY_SIMULATION_ID);
      });
    }
  }, [urlSimId]); // eslint-disable-line react-hooks/exhaustive-deps

  const simulationId = simulation?.simulation_id ?? null;
  const { lastMessage, retryExhausted, reconnect } = useSimulationSocket(simulationId);

  useEffect(() => {
    if (!lastMessage) return;
    switch (lastMessage.type) {
      case 'step_result':
        appendStep(lastMessage.data as StepResult);
        break;
      case 'emergent_event': {
        const event = lastMessage.data as EmergentEvent;
        appendEmergentEvent(event);
        // Dedup: skip toast if same event_type fired within the last 10 seconds
        const now = Date.now();
        const last = lastToastRef.current;
        if (!last || last.type !== event.event_type || now - last.at > 10_000) {
          lastToastRef.current = { type: event.event_type ?? "event", at: now };
          addToast({
            type: 'warning',
            message: `${(event.event_type ?? "event").replace(/_/g, ' ')} detected at step ${event.step ?? 0}`,
          });
        }
        break;
      }
      case 'status_change':
        setStatus((lastMessage.data as { status: SimulationStatus }).status);
        break;
    }
  }, [lastMessage, appendStep, appendEmergentEvent, setStatus, addToast]);

  // Show report modal when simulation completes.
  // setState is deferred via queueMicrotask to avoid calling it synchronously
  // inside the effect body (react-hooks/set-state-in-effect).
  useEffect(() => {
    if (status === 'completed' && stepsLength > 0) {
      queueMicrotask(() => setReportOpen(true));
    }
  }, [status, stepsLength]);

  if (!simulation) {
    return (
      <div className="h-screen w-screen flex flex-col bg-[var(--background)]">
        <ControlPanel />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center flex flex-col items-center gap-4">
            <Brain className="w-16 h-16 text-[var(--muted-foreground)]" />
            <h2 className="text-xl font-semibold text-[var(--foreground)]">No Active Simulation</h2>
            <p className="text-sm text-[var(--muted-foreground)] max-w-md">
              Select a project and run a scenario to start simulation.
            </p>
            <button
              onClick={() => navigate("/projects")}
              className="h-10 px-6 text-sm font-medium rounded-md bg-[var(--primary)] text-[var(--primary-foreground)] hover:opacity-90 transition-opacity flex items-center gap-2"
            >
              <FolderOpen className="w-4 h-4" />
              Go to Projects
            </button>
            <button
              onClick={() => navigate("/setup")}
              className="h-10 px-6 text-sm font-medium rounded-md border border-[var(--border)] text-[var(--foreground)] hover:bg-[var(--secondary)] transition-colors flex items-center gap-2"
            >
              <Brain className="w-4 h-4" />
              Create Simulation
            </button>
          </div>
        </div>
        <ToastContainer />
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

      {/* WebSocket retry exhausted banner */}
      {retryExhausted && (
        <div className="flex items-center justify-center gap-3 px-4 py-2 bg-amber-900/80 text-amber-200 text-sm">
          <span>WebSocket connection lost after {5} retries.</span>
          <button
            onClick={reconnect}
            className="px-3 py-1 rounded bg-amber-700 hover:bg-amber-600 text-white text-xs font-medium transition-colors"
          >
            Click to retry
          </button>
        </div>
      )}

      {/* Zone 2: Middle Content — fills available space; stacks vertically on tablet/mobile */}
      <div className="flex flex-1 min-h-0 zone2-panels">
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

      {/* Agent Inspector — right drawer, shown when agent selected */}
      {isAgentInspectorOpen && selectedAgentId && simulation && (
        <AgentInspector
          agentId={selectedAgentId}
          simulationId={simulation.simulation_id}
          isPaused={status === "paused"}
        />
      )}

      {/* Simulation Report Modal — shown on completion */}
      {reportOpen && <SimulationReportModal onClose={() => setReportOpen(false)} />}

      {/* Toast Notifications */}
      <ToastContainer />
    </div>
  );
}
