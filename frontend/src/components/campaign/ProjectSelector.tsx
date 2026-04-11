/**
 * ProjectSelector — Section 1 of the Campaign Setup form.
 * Read-only input when a projectId is in the URL, otherwise a dropdown.
 *
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md#section-1
 */
import type { ProjectSummary } from "../../api/client";

interface Props {
  projects: ProjectSummary[];
  selectedProjectId: string;
  onSelectProject: (projectId: string) => void;
  urlProjectId?: string;
}

export default function ProjectSelector({
  projects,
  selectedProjectId,
  onSelectProject,
  urlProjectId,
}: Props) {
  return (
    <div className="flex flex-col gap-1.5">
      <label htmlFor="campaign-project" className="text-sm font-medium text-[var(--foreground)]">
        Project
      </label>
      {urlProjectId ? (
        <input
          id="campaign-project"
          type="text"
          readOnly
          value={projects.find((p) => p.project_id === urlProjectId)?.name ?? urlProjectId}
          className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--secondary)] text-[var(--muted-foreground)] cursor-not-allowed"
        />
      ) : (
        <select
          id="campaign-project"
          value={selectedProjectId}
          onChange={(e) => onSelectProject(e.target.value)}
          className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
        >
          <option value="">Select a project...</option>
          {projects.map((p) => (
            <option key={p.project_id} value={p.project_id}>
              {p.name}
            </option>
          ))}
        </select>
      )}
    </div>
  );
}
