/**
 * ProjectsListPage — Top-level project management dashboard.
 * @spec docs/spec/ui/UI_06_PROJECTS_LIST.md
 */
import { useNavigate } from "react-router-dom";
import { Plus, Layers, Users, Clock } from "lucide-react";
import AppSidebar from "../components/shared/AppSidebar";

/* ------------------------------------------------------------------ */
/* Mock Data                                                           */
/* ------------------------------------------------------------------ */

const MOCK_PROJECTS = [
  {
    id: "p1",
    name: "Korea Election 2026 Simulation",
    description:
      "Simulate the 2026 Korean presidential election with agent-based modeling...",
    scenarios: 4,
    totalAgents: 10000,
    lastRun: "2026-03-15",
    status: "active" as const,
  },
  {
    id: "p2",
    name: "COVID-19 Misinformation Spread",
    description:
      "Analyzing viral misinformation patterns across multi-community networks...",
    scenarios: 3,
    totalAgents: 6000,
    lastRun: "2026-01-20",
    status: "draft" as const,
  },
  {
    id: "p3",
    name: "Brand Perception Study — TechCorp",
    description:
      "Multi-community brand perception simulation for TechCorp product launch...",
    scenarios: 6,
    totalAgents: 8000,
    lastRun: "2026-03-01",
    status: "in-progress" as const,
  },
];

/* ------------------------------------------------------------------ */
/* Status Badge                                                        */
/* ------------------------------------------------------------------ */

type ProjectStatus = "active" | "draft" | "in-progress";

const STATUS_STYLES: Record<ProjectStatus, { bg: string; text: string; label: string }> = {
  active: { bg: "bg-[var(--sentiment-positive)]/10", text: "text-[var(--sentiment-positive)]", label: "Active" },
  draft: { bg: "bg-[var(--secondary)]", text: "text-[var(--muted-foreground)]", label: "Draft" },
  "in-progress": { bg: "bg-[var(--sentiment-warning)]/15", text: "text-[var(--sentiment-warning)]", label: "In-progress" },
};

function StatusBadge({ status }: { status: ProjectStatus }) {
  const s = STATUS_STYLES[status];
  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}
    >
      {s.label}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function ProjectsListPage() {
  const navigate = useNavigate();

  return (
    <div
      data-testid="projects-list-page"
      className="min-h-screen flex bg-[var(--background)]"
    >
      <AppSidebar />

      {/* Main Content */}
      <main className="flex-1 overflow-auto" style={{ padding: 32 }}>
        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold font-display text-[var(--foreground)]">Projects</h1>
            <p className="text-sm text-[var(--muted-foreground)] mt-1">
              Manage your simulation projects and scenarios
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button className="inline-flex items-center gap-2 h-9 px-4 text-sm font-medium text-white bg-[var(--foreground)] rounded-md hover:bg-[var(--foreground)]/90 transition-colors">
              <Plus className="w-4 h-4" />
              New Project
            </button>
            {/* Avatar placeholder */}
            <div className="w-8 h-8 rounded-full bg-[var(--border)] flex items-center justify-center text-xs font-medium text-[var(--muted-foreground)]">
              U
            </div>
          </div>
        </div>

        {/* Project Cards */}
        <div className="flex flex-col gap-4">
          {MOCK_PROJECTS.map((project) => (
            <div
              key={project.id}
              className="interactive bg-[var(--card)] border border-[var(--border)] rounded-lg p-5 hover:shadow-[0_2px_8px_rgba(0,0,0,0.08)] transition-shadow"
            >
              {/* Top row */}
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0 mr-4">
                  <button
                    onClick={() => navigate(`/projects/${project.id}`)}
                    className="text-base font-semibold text-[var(--foreground)] hover:underline text-left"
                  >
                    {project.name}
                  </button>
                  <p className="text-sm text-[var(--muted-foreground)] mt-1 line-clamp-2">
                    {project.description}
                  </p>
                </div>
                <button
                  onClick={() => navigate(`/projects/${project.id}`)}
                  className="shrink-0 h-8 px-3 text-sm font-medium border border-[var(--border)] rounded-md bg-[var(--card)] hover:bg-[var(--secondary)] transition-colors"
                >
                  Open
                </button>
              </div>

              {/* Metadata row */}
              <div className="flex items-center gap-4 mt-3 flex-wrap">
                <span className="inline-flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                  <Layers className="w-3.5 h-3.5" />
                  Scenarios: {project.scenarios}
                </span>
                <span className="inline-flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                  <Users className="w-3.5 h-3.5" />
                  Total Agents: {project.totalAgents.toLocaleString()}
                </span>
                <span className="inline-flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                  <Clock className="w-3.5 h-3.5" />
                  Last Run: {project.lastRun}
                </span>
                <StatusBadge status={project.status} />
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
