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
import { lazy, Suspense, useEffect, useRef, useState } from "react";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import { apiClient } from "../api/client";
import { LS_KEY_SIMULATION_ID, SIM_STATUS } from "@/config/constants";
import { FolderOpen, Brain, X } from "lucide-react";
import ControlPanel from "../components/control/ControlPanel";
import WorkflowStepper from "../components/layout/WorkflowStepper";
import EmergentEventsPanel from "../components/emergent/EmergentEventsPanel";
import CommunityPanel from "../components/graph/CommunityPanel";
// GraphPanel pulls three.js + react-force-graph-3d (~1 MB raw / 375 KB gzipped).
// Lazy-load it so the empty state ("No Active Simulation") below renders
// without paying the WebGL bundle cost. Once a simulation is active, the
// chunk is fetched once and cached.
const GraphPanel = lazy(() => import("../components/graph/GraphPanel"));
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
  // SPEC 26 §4.5.2 (v0.3.0) — read ?step= query param for Analytics deep-link.
  const [searchParams, setSearchParams] = useSearchParams();
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
  const focusedStep = useSimulationStore((s) => s.focusedStep);
  const setFocusedStep = useSimulationStore((s) => s.setFocusedStep);

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
    if (status === SIM_STATUS.COMPLETED && stepsLength > 0) {
      queueMicrotask(() => setReportOpen(true));
    }
  }, [status, stepsLength]);

  /**
   * SPEC 26 §4.5.2 (v0.3.0) — round-trip from Analytics event-row deep-link.
   *
   * On mount (or whenever the query string changes), parse `?step=N`. A valid
   * non-negative integer pins `focusedStep`. Anything else is silently ignored
   * so malformed URLs don't break live behavior.
   */
  useEffect(() => {
    const raw = searchParams.get("step");
    if (raw == null) return;
    const parsed = Number.parseInt(raw, 10);
    if (Number.isFinite(parsed) && parsed >= 0 && String(parsed) === raw) {
      setFocusedStep(parsed);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  /** Dismiss the focus banner: clear store field and strip ?step from URL. */
  const clearStepFocus = () => {
    setFocusedStep(null);
    const next = new URLSearchParams(searchParams);
    next.delete("step");
    setSearchParams(next, { replace: true });
  };

  if (!simulation) {
    return (
      <div className="h-full w-full flex flex-col bg-[var(--background)]">
        <ControlPanel />
        <WorkflowStepper />
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
      className="h-full w-full flex flex-col overflow-hidden bg-[var(--background)]"
    >
      {/* Zone 1: Simulation Control Bar — 56px */}
      <ControlPanel />

      {/* Workflow Stepper — 6-stage progress indicator */}
      <WorkflowStepper />

      {/* Step focus banner — SPEC 26 §4.5.2 (v0.3.0).
          Shown when Analytics deep-linked to a specific step.
          NOTE: v0.3.0 announces the focus only. Graph / metrics state replay
          at the focused step is deferred to v0.4.0 (see SPEC §9). */}
      {focusedStep !== null && (
        <div
          data-testid="step-focus-banner"
          className="flex items-center justify-between gap-3 px-4 py-2 bg-amber-500/10 border-y border-amber-500/30 text-amber-600 text-sm"
        >
          <span>
            Viewing step <strong>{focusedStep}</strong> from Analytics. Live
            updates continue in the background.
          </span>
          <button
            type="button"
            onClick={clearStepFocus}
            className="flex items-center gap-1 text-xs font-medium px-2 py-1 rounded border border-amber-500/40 hover:bg-amber-500/20 transition-colors"
          >
            <X className="w-3 h-3" />
            Return to live
          </button>
        </div>
      )}

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
          <Suspense
            fallback={
              <div className="w-full h-full flex items-center justify-center text-sm text-[var(--muted-foreground)]">
                Loading 3D graph engine…
              </div>
            }
          >
            <GraphPanel />
          </Suspense>
        </div>

        {/* Right: Metrics Panel — 280px */}
        <MetricsPanel />
      </div>

      {/* Zone 3: Bottom Area — 220px */}
      <div className="shrink-0 flex flex-col" style={{ height: "var(--bottom-area-height)" }}>
        {/* Timeline + Diffusion Wave — 120px (with emergent event markers) */}
        <TimelinePanel />

        {/* Conversations | Emergent Events — split horizontally */}
        <div className="flex-1 min-h-0 flex">
          <div className="flex-1 min-w-0">
            <ConversationPanel />
          </div>
          {/* SPEC 24 §2.2.5 — widened from 280px → var(--emergent-panel-width)
              (360px) and shown from md breakpoint so emergent events
              are not clipped on common 13–14" laptops. */}
          <div
            className="shrink-0 hidden md:flex"
            style={{ width: "var(--emergent-panel-width)" }}
          >
            <EmergentEventsPanel />
          </div>
        </div>
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
          isPaused={status === SIM_STATUS.PAUSED}
        />
      )}

      {/* Simulation Report Modal — shown on completion */}
      {reportOpen && <SimulationReportModal onClose={() => setReportOpen(false)} />}

      {/* Toast Notifications */}
      <ToastContainer />
    </div>
  );
}
