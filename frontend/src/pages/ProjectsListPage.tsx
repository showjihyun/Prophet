/**
 * ProjectsListPage — Top-level project management dashboard.
 * @spec docs/spec/ui/UI_06_PROJECTS_LIST.md
 */
import { useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import { Plus, Layers, Clock } from "lucide-react";
import AppSidebar from "../components/shared/AppSidebar";
import { apiClient } from "../api/client";
import type { ProjectSummary } from "../api/client";
import { useSimulationStore } from "../store/simulationStore";

/* ------------------------------------------------------------------ */
/* Status Badge                                                        */
/* ------------------------------------------------------------------ */

function StatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; text: string }> = {
    active: { bg: "bg-[var(--sentiment-positive)]/10", text: "text-[var(--sentiment-positive)]" },
    draft: { bg: "bg-[var(--secondary)]", text: "text-[var(--muted-foreground)]" },
    "in-progress": { bg: "bg-[var(--sentiment-warning)]/15", text: "text-[var(--sentiment-warning)]" },
  };
  const s = styles[status] ?? { bg: "bg-[var(--secondary)]", text: "text-[var(--muted-foreground)]" };
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}>
      {status}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function ProjectsListPage() {
  const navigate = useNavigate();
  const setCurrentProject = useSimulationStore((s) => s.setCurrentProject);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.projects.list()
      .then((res) => setProjects(Array.isArray(res) ? res : []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleNewProject = async () => {
    const name = window.prompt("New project name:");
    if (!name?.trim()) return;
    try {
      const project = await apiClient.projects.create({ name: name.trim() });
      setProjects((prev) => [...prev, project]);
    } catch { /* ignore */ }
  };

  const handleOpen = (project: ProjectSummary) => {
    setCurrentProject(project.project_id);
    navigate(`/projects/${project.project_id}`);
  };

  return (
    <div
      data-testid="projects-list-page"
      className="min-h-screen bg-[var(--background)]"
    >
      {/* Main Content */}
      <main className="overflow-auto" style={{ padding: 32 }}>
        {/* Header */}
        <div className="flex items-start justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold font-display text-[var(--foreground)]">Projects</h1>
            <p className="text-sm text-[var(--muted-foreground)] mt-1">
              Manage your simulation projects and scenarios
            </p>
          </div>
          <div className="flex items-center gap-3">
            <button
              onClick={handleNewProject}
              className="inline-flex items-center gap-2 h-9 px-4 text-sm font-medium text-white bg-[var(--foreground)] rounded-md hover:bg-[var(--foreground)]/90 transition-colors"
            >
              <Plus className="w-4 h-4" />
              New Project
            </button>
            {/* Avatar placeholder */}
            <div className="w-8 h-8 rounded-full bg-[var(--border)] flex items-center justify-center text-xs font-medium text-[var(--muted-foreground)]">
              U
            </div>
          </div>
        </div>

        {/* Loading state */}
        {loading && (
          <p className="text-sm text-[var(--muted-foreground)]">Loading projects...</p>
        )}

        {/* Empty state */}
        {!loading && projects.length === 0 && (
          <p className="text-sm text-[var(--muted-foreground)]">No projects yet. Create one to get started.</p>
        )}

        {/* Project Cards */}
        <div className="flex flex-col gap-4">
          {projects.map((project) => (
            <div
              key={project.project_id}
              className="interactive bg-[var(--card)] border border-[var(--border)] rounded-lg p-5 hover:shadow-[0_2px_8px_rgba(0,0,0,0.08)] transition-shadow"
            >
              {/* Top row */}
              <div className="flex items-start justify-between">
                <div className="flex-1 min-w-0 mr-4">
                  <button
                    onClick={() => handleOpen(project)}
                    className="text-base font-semibold text-[var(--foreground)] hover:underline text-left"
                  >
                    {project.name}
                  </button>
                  <p className="text-sm text-[var(--muted-foreground)] mt-1 line-clamp-2">
                    {project.description}
                  </p>
                </div>
                <button
                  onClick={() => handleOpen(project)}
                  className="shrink-0 h-8 px-3 text-sm font-medium border border-[var(--border)] rounded-md bg-[var(--card)] hover:bg-[var(--secondary)] transition-colors"
                >
                  Open
                </button>
              </div>

              {/* Metadata row */}
              <div className="flex items-center gap-4 mt-3 flex-wrap">
                <span className="inline-flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                  <Layers className="w-3.5 h-3.5" />
                  Scenarios: {project.scenario_count}
                </span>
                <span className="inline-flex items-center gap-1.5 text-xs text-[var(--muted-foreground)]">
                  <Clock className="w-3.5 h-3.5" />
                  Created: {project.created_at ? new Date(project.created_at).toLocaleDateString() : "—"}
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
