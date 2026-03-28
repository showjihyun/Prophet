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
import ControlPanel from "../components/control/ControlPanel";
import CommunityPanel from "../components/graph/CommunityPanel";
import GraphPanel from "../components/graph/GraphPanel";
import MetricsPanel from "../components/graph/MetricsPanel";
import TimelinePanel from "../components/timeline/TimelinePanel";
import ConversationPanel from "../components/control/ConversationPanel";

export default function SimulationPage() {
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
