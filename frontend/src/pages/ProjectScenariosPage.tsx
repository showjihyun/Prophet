/**
 * ProjectScenariosPage — Detail view for a single project with scenario cards.
 * @spec docs/spec/ui/UI_07_PROJECT_SCENARIOS.md
 */
import { useParams, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import {
  Plus,
  Settings,
  Clock,
  Play,
  Square,
  MoreHorizontal,
  Trash2,
} from "lucide-react";
import { apiClient } from "../api/client";
import type { ProjectDetail, ScenarioInfo } from "../api/client";
import { useSimulationStore } from "../store/simulationStore";

/* ------------------------------------------------------------------ */
/* Status Badge                                                        */
/* ------------------------------------------------------------------ */

function ScenarioStatusBadge({ status }: { status: string }) {
  const styles: Record<string, { bg: string; text: string; pulse?: boolean }> = {
    completed: { bg: "bg-[var(--sentiment-positive)]/10", text: "text-[var(--sentiment-positive)]" },
    running: { bg: "bg-[var(--destructive)]/10", text: "text-[var(--destructive)]", pulse: true },
    draft: { bg: "bg-[var(--secondary)]", text: "text-[var(--muted-foreground)]" },
  };
  const s = styles[status] ?? { bg: "bg-[var(--secondary)]", text: "text-[var(--muted-foreground)]" };
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium ${s.bg} ${s.text}`}>
      {s.pulse && (
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--destructive)] opacity-75" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--destructive)]" />
        </span>
      )}
      {status}
    </span>
  );
}

function ProjectStatusBadge({ status }: { status: string }) {
  return (
    <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium bg-[var(--sentiment-positive)]/10 text-[var(--sentiment-positive)]">
      {status}
    </span>
  );
}

/* ------------------------------------------------------------------ */
/* Page                                                                */
/* ------------------------------------------------------------------ */

export default function ProjectScenariosPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const setSimulation = useSimulationStore((s) => s.setSimulation);
  const setCurrentProject = useSimulationStore((s) => s.setCurrentProject);

  const [project, setProject] = useState<ProjectDetail | null>(null);
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!projectId) return;
    setCurrentProject(projectId);
    apiClient.projects.get(projectId)
      .then((detail) => {
        setProject(detail);
        setScenarios(detail.scenarios);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [projectId, setCurrentProject]);

  const handleNewScenario = () => {
    if (!projectId) return;
    navigate(`/projects/${projectId}/new-scenario`);
  };

  const handleRun = async (scenario: ScenarioInfo) => {
    if (!projectId) return;
    try {
      const res = await apiClient.projects.runScenario(projectId, scenario.scenario_id);
      if (res && res.simulation_id) {
        try {
          const sim = await apiClient.simulations.get(res.simulation_id);
          useSimulationStore.getState().setSimulation(sim);
        } catch { /* ignore */ }
      }
      navigate("/simulation");
    } catch { /* ignore */ }
  };

  const handleResults = async (scenario: ScenarioInfo) => {
    if (scenario.simulation_id) {
      try {
        const sim = await apiClient.simulations.get(scenario.simulation_id);
        setSimulation(sim);
      } catch { /* ignore */ }
    }
    navigate("/simulation");
  };

  const handleDelete = async (scenario: ScenarioInfo) => {
    if (!projectId) return;
    if (!window.confirm(`Delete scenario "${scenario.name}"?`)) return;
    try {
      await apiClient.projects.deleteScenario(projectId, scenario.scenario_id);
      setScenarios((prev) => prev.filter((s) => s.scenario_id !== scenario.scenario_id));
    } catch { /* ignore */ }
  };

  const projectName = project?.name ?? "Project";
  const projectDescription = project?.description ?? "";

  return (
    <div
      data-testid="project-scenarios-page"
      className="min-h-screen bg-[var(--background)]"
    >
      {/* Main Content */}
      <main className="overflow-auto" style={{ padding: 32 }}>
        {/* Breadcrumb */}
        <nav className="flex items-center gap-1.5 text-sm mb-6">
          <button
            onClick={() => navigate("/projects")}
            className="text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
          >
            Projects
          </button>
          <span className="text-[var(--muted-foreground)]">&gt;</span>
          <span className="text-[var(--foreground)] font-medium">{projectName}</span>
        </nav>

        {/* Loading */}
        {loading && (
          <p className="text-sm text-[var(--muted-foreground)]">Loading project...</p>
        )}

        {!loading && project && (
          <>
            {/* Project Header */}
            <div className="flex items-start justify-between mb-6">
              <div>
                <h1 className="text-2xl font-bold font-display text-[var(--foreground)]">
                  {projectName}
                </h1>
                <p className="text-sm text-[var(--muted-foreground)] mt-1">{projectDescription}</p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button className="inline-flex items-center gap-2 h-9 px-3 text-sm font-medium text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] rounded-md transition-colors">
                  <Settings className="w-4 h-4" />
                  Settings
                </button>
                <button
                  onClick={handleNewScenario}
                  className="inline-flex items-center gap-2 h-9 px-4 text-sm font-medium text-white bg-[var(--foreground)] rounded-md hover:bg-[var(--foreground)]/90 transition-colors"
                >
                  <Plus className="w-4 h-4" />
                  New Scenario
                </button>
              </div>
            </div>

            {/* Project Info Bar */}
            <div className="flex items-center gap-6 bg-[var(--muted)] rounded-lg px-5 py-3 mb-6 flex-wrap">
              <div className="flex items-center gap-2">
                <span className="text-xs text-[var(--muted-foreground)]">Status</span>
                <ProjectStatusBadge status={project.status} />
              </div>
              <Divider />
              <InfoItem label="Scenarios" value={String(scenarios.length)} />
              <Divider />
              <InfoItem
                label="Created"
                value={project.created_at ? new Date(project.created_at).toLocaleDateString() : "—"}
              />
            </div>

            {/* Scenarios Section */}
            <h2 className="text-lg font-semibold text-[var(--foreground)] mb-4">
              Scenarios
            </h2>

            {scenarios.length === 0 && (
              <p className="text-sm text-[var(--muted-foreground)]">No scenarios yet. Create one to get started.</p>
            )}

            <div className="flex flex-col gap-4">
              {scenarios.map((scenario) => (
                <div
                  key={scenario.scenario_id}
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
                        <Clock className="w-3.5 h-3.5" />
                        Created: {scenario.created_at ? new Date(scenario.created_at).toLocaleDateString() : "—"}
                      </span>
                    </div>

                    {/* Actions */}
                    <div className="flex items-center gap-2">
                      {scenario.status === "completed" && (
                        <button
                          onClick={() => handleResults(scenario)}
                          className="h-8 px-3 text-sm font-medium border border-[var(--border)] rounded-md bg-[var(--card)] hover:bg-[var(--secondary)] transition-colors"
                        >
                          Results
                        </button>
                      )}
                      {scenario.status === "running" && (
                        <button className="inline-flex items-center gap-1.5 h-8 px-3 text-sm font-medium text-[var(--destructive)] border border-[var(--destructive)]/30 rounded-md bg-[var(--destructive)]/10 hover:bg-[var(--destructive)]/15 transition-colors">
                          <Square className="w-3.5 h-3.5" />
                          Stop
                        </button>
                      )}
                      {(scenario.status === "draft" || scenario.status === "created") && (
                        <button
                          onClick={() => handleRun(scenario)}
                          className="inline-flex items-center gap-1.5 h-8 px-3 text-sm font-medium text-white bg-[var(--foreground)] rounded-md hover:bg-[var(--foreground)]/90 transition-colors"
                        >
                          <Play className="w-3.5 h-3.5" />
                          Run
                        </button>
                      )}
                      <button
                        onClick={() => handleDelete(scenario)}
                        title="Delete scenario"
                        className="h-8 w-8 flex items-center justify-center text-[var(--muted-foreground)] hover:text-[var(--destructive)] hover:bg-[var(--accent)] rounded-md transition-colors"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                      <button className="h-8 w-8 flex items-center justify-center text-[var(--muted-foreground)] hover:text-[var(--foreground)] hover:bg-[var(--accent)] rounded-md transition-colors">
                        <MoreHorizontal className="w-4 h-4" />
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}
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
