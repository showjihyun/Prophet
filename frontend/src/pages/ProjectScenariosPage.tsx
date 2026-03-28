/**
 * ProjectScenariosPage — Detail view for a single project with scenario cards.
 * @spec docs/spec/ui/UI_07_PROJECT_SCENARIOS.md
 */
import { useParams, useNavigate } from "react-router-dom";
import {
  Plus,
  Settings,
  Users,
  Clock,
  Play,
  Square,
  MoreHorizontal,
} from "lucide-react";
import AppSidebar from "../components/shared/AppSidebar";

/* ------------------------------------------------------------------ */
/* Mock Data                                                           */
/* ------------------------------------------------------------------ */

const MOCK_PROJECT = {
  id: "p1",
  name: "Korea Election 2026 Simulation",
  description:
    "Simulate the 2026 Korean presidential election with agent-based modeling across multiple community networks.",
  status: "active" as const,
  scenarios: 4,
  totalAgents: 10000,
  created: "2026-03-15",
  lastRun: "2 hours ago",
};

const MOCK_SCENARIOS = [
  {
    id: "s1",
    name: "Baseline — No Intervention",
    status: "completed" as const,
    description: "Control scenario with default parameters...",
    agents: 2500,
    tier1: 2000,
    tier2: 400,
    tier3: 100,
    runTime: "2h 15m",
    viralProb: "64.2%",
  },
  {
    id: "s2",
    name: "Media Influence Campaign",
    status: "running" as const,
    description: "Simulates large-scale media campaign...",
    agents: 3000,
    tier1: 2400,
    tier2: 480,
    tier3: 120,
    runTime: "1h 45m",
    viralProb: "\u2014",
  },
  {
    id: "s3",
    name: "Echo Chamber Formation",
    status: "draft" as const,
    description: "Tests echo chamber dynamics...",
    agents: 2000,
    tier1: 1600,
    tier2: 320,
    tier3: 80,
    runTime: "\u2014",
    viralProb: "\u2014",
  },
  {
    id: "s4",
    name: "Fact-Check Bot Intervention",
    status: "completed" as const,
    description: "Deploy AI fact-checker agents...",
    agents: 2500,
    tier1: 1800,
    tier2: 500,
    tier3: 200,
    runTime: "3h 20m",
    viralProb: "31.2%",
  },
];

/* ------------------------------------------------------------------ */
/* Status Badge                                                        */
/* ------------------------------------------------------------------ */

type ScenarioStatus = "completed" | "running" | "draft";

const SCENARIO_STATUS_STYLES: Record<
  ScenarioStatus,
  { bg: string; text: string; label: string; pulse?: boolean }
> = {
  completed: { bg: "bg-green-50", text: "text-green-700", label: "Completed" },
  running: {
    bg: "bg-red-50",
    text: "text-red-700",
    label: "Running",
    pulse: true,
  },
  draft: { bg: "bg-gray-100", text: "text-gray-600", label: "Draft" },
};

function ScenarioStatusBadge({ status }: { status: ScenarioStatus }) {
  const s = SCENARIO_STATUS_STYLES[status];
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}
    >
      {s.pulse && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500" />
        </span>
      )}
      {s.label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Project Status Badge (for info bar)                                 */
/* ------------------------------------------------------------------ */

function ProjectStatusBadge() {
  return (
    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-green-50 text-green-700">
      Active
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Tier Colors                                                         */
/* ------------------------------------------------------------------ */

const TIER_COLORS = {
  tier1: "#94a3b8",
  tier2: "#f59e0b",
  tier3: "#a855f7",
};

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function ProjectScenariosPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();

  // In real app, fetch project by projectId. For now use mock.
  void projectId;
  const project = MOCK_PROJECT;

  return (
    <div
      data-testid="project-scenarios-page"
      className="min-h-screen flex bg-[var(--background)]"
    >
      <AppSidebar />

      {/* Main Content */}
      <main className="flex-1 overflow-auto" style={{ padding: 32 }}>
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-sm mb-6">
          <button
            onClick={() => navigate("/projects")}
            className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
          >
            Projects
          </button>
          <span className="text-[var(--muted-foreground)]">&gt;</span>
          <span className="text-[var(--foreground)] font-medium">{project.name}</span>
        </nav>

        {/* Project Header */}
        <div className="flex items-start justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold font-display text-[var(--foreground)]">
              {project.name}
            </h1>
            <p className="text-sm text-[var(--muted-foreground)] mt-1">{project.description}</p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <button className="inline-flex items-center gap-2 h-9 px-3 text-sm font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] rounded-md transition-colors">
              <Settings className="w-4 h-4" />
              Settings
            </button>
            <button className="inline-flex items-center gap-2 h-9 px-4 text-sm font-medium text-white bg-[var(--foreground)] rounded-md hover:bg-[var(--foreground)]/90 transition-colors">
              <Plus className="w-4 h-4" />
              New Scenario
            </button>
          </div>
        </div>

        {/* Project Info Bar */}
        <div className="flex items-center gap-6 bg-[var(--muted)] rounded-lg px-5 py-3 mb-6 flex-wrap">
          <div className="flex items-center gap-2">
            <span className="text-xs text-[var(--muted-foreground)]">Status</span>
            <ProjectStatusBadge />
          </div>
          <Divider />
          <InfoItem label="Scenarios" value={String(project.scenarios)} />
          <Divider />
          <InfoItem
            label="Total Agents"
            value={project.totalAgents.toLocaleString()}
          />
          <Divider />
          <InfoItem label="Created" value={project.created} />
          <Divider />
          <InfoItem label="Last Run" value={project.lastRun} />
        </div>

        {/* Scenarios Section */}
        <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4">
          Scenarios
        </h2>

        <div className="flex flex-col gap-4">
          {MOCK_SCENARIOS.map((scenario) => (
            <div
              key={scenario.id}
              className="interactive bg-[var(--card)] border border-[var(--border)] rounded-lg p-5"
            >
              {/* Header: name + status */}
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-base font-semibold text-[var(--foreground)]">
                  {scenario.name}
                </h3>
                <ScenarioStatusBadge status={scenario.status} />
              </div>

              {/* Description */}
              <p className="text-sm text-[var(--muted-foreground)] mb-3">
                {scenario.description}
              </p>

              {/* Metadata + Actions */}
              <div className="flex items-center justify-between flex-wrap gap-2">
                {/* Metadata */}
                <div className="flex items-center gap-4 flex-wrap">
                  <span className="inline-flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                    <Users className="w-3.5 h-3.5" />
                    Agents: {scenario.agents.toLocaleString()}
                  </span>
                  <span className="text-xs" style={{ color: TIER_COLORS.tier1 }}>
                    Tier 1: {scenario.tier1.toLocaleString()}
                  </span>
                  <span className="text-xs" style={{ color: TIER_COLORS.tier2 }}>
                    Tier 2: {scenario.tier2.toLocaleString()}
                  </span>
                  <span className="text-xs" style={{ color: TIER_COLORS.tier3 }}>
                    Tier 3: {scenario.tier3.toLocaleString()}
                  </span>
                  <span className="inline-flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                    <Clock className="w-3.5 h-3.5" />
                    Run time: {scenario.runTime}
                  </span>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2">
                  {scenario.status === "completed" && (
                    <button
                      onClick={() => navigate("/")}
                      className="h-8 px-3 text-sm font-medium border border-[var(--border)] rounded-md bg-[var(--card)] hover:bg-gray-50 transition-colors"
                    >
                      Results
                    </button>
                  )}
                  {scenario.status === "running" && (
                    <button className="inline-flex items-center gap-1.5 h-8 px-3 text-sm font-medium text-red-600 border border-red-200 rounded-md bg-red-50 hover:bg-red-100 transition-colors">
                      <Square className="w-3.5 h-3.5" />
                      Stop
                    </button>
                  )}
                  {scenario.status === "draft" && (
                    <button
                      onClick={() => navigate("/")}
                      className="inline-flex items-center gap-1.5 h-8 px-3 text-sm font-medium text-white bg-[var(--foreground)] rounded-md hover:bg-[var(--foreground)]/90 transition-colors"
                    >
                      <Play className="w-3.5 h-3.5" />
                      Run
                    </button>
                  )}
                  <button className="h-8 w-8 flex items-center justify-center text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] rounded-md transition-colors">
                    <MoreHorizontal className="w-4 h-4" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/* Small helpers                                                       */
/* ------------------------------------------------------------------ */

function Divider() {
  return <div className="h-4 w-px bg-[var(--border)]" />;
}

function InfoItem({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="text-xs text-[var(--muted-foreground)]">{label}</span>
      <span className="text-sm font-semibold text-[var(--foreground)]">{value}</span>
    </div>
  );
}
