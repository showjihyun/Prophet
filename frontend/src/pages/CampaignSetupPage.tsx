/**
 * CampaignSetupPage — Campaign creation form with simulation parameters.
 * @spec docs/spec/07_FRONTEND_SPEC.md#campaign-setup
 */
import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { apiClient } from "../api/client";
import type { CreateSimulationConfig, ProjectSummary } from "../api/client";
import PageNav from "../components/shared/PageNav";
import { useSimulationStore } from "../store/simulationStore";

const CHANNELS = ["SNS", "Influencer", "Online Ads", "TV", "Email"] as const;
const COMMUNITIES = [
  { id: "alpha", name: "Alpha", color: "#3b82f6" },
  { id: "beta", name: "Beta", color: "#22c55e" },
  { id: "gamma", name: "Gamma", color: "#f97316" },
  { id: "delta", name: "Delta", color: "#a855f7" },
  { id: "bridge", name: "Bridge", color: "#ef4444" },
] as const;

export default function CampaignSetupPage() {
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");

  useEffect(() => {
    apiClient.projects.list().then((res) => setProjects(Array.isArray(res) ? res : [])).catch(() => {});
  }, []);

  const [name, setName] = useState("");
  const [budget, setBudget] = useState("");
  const [channels, setChannels] = useState<Set<string>>(new Set());
  const [message, setMessage] = useState("");
  const [targetCommunities, setTargetCommunities] = useState<Set<string>>(
    new Set()
  );
  const [maxSteps, setMaxSteps] = useState(365);
  const [randomSeed, setRandomSeed] = useState(42);
  const [slmLlmRatio, setSlmLlmRatio] = useState(80);

  function toggleChannel(ch: string) {
    setChannels((prev) => {
      const next = new Set(prev);
      if (next.has(ch)) next.delete(ch);
      else next.add(ch);
      return next;
    });
  }

  function toggleCommunity(id: string) {
    setTargetCommunities((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const config: CreateSimulationConfig = {
        name,
        campaign: {
          name,
          budget: Number(budget),
          channels: Array.from(channels),
          message,
          target_communities: Array.from(targetCommunities),
        },
        max_steps: maxSteps,
        random_seed: randomSeed,
        slm_llm_ratio: slmLlmRatio / 100,
      };
      const sim = await apiClient.simulations.create(config);
      // Store the created simulation in Zustand so SimulationPage can use it
      const { setSimulation, setStatus } = useSimulationStore.getState();
      setSimulation({
        simulation_id: sim.simulation_id,
        name: config.name,
        status: sim.status as any,
        current_step: 0,
        max_steps: config.max_steps ?? 50,
        created_at: new Date().toISOString(),
      });
      setStatus(sim.status as any);
      // Link simulation to selected project as a scenario
      if (selectedProjectId) {
        await apiClient.projects.createScenario(selectedProjectId, {
          name: config.name,
          config: { simulation_id: sim.simulation_id },
        }).catch(() => {});
      }
      navigate("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create simulation");
      setSubmitting(false);
    }
  }

  return (
    <div
      data-testid="campaign-setup-page"
      className="min-h-screen bg-[var(--background)] flex flex-col"
    >
      <PageNav
        breadcrumbs={[
          { label: "Home", href: "/" },
          { label: "Campaign Setup" },
        ]}
      />

      <div className="flex-1 p-6 flex justify-center overflow-auto">
        <form
          onSubmit={handleSubmit}
          className="w-full max-w-2xl flex flex-col gap-6"
        >
          <h1 className="text-xl font-bold font-display text-[var(--foreground)]">
            Create New Simulation
          </h1>

          {/* Project Selector */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">
              Project (optional)
            </label>
            <select
              value={selectedProjectId}
              onChange={(e) => setSelectedProjectId(e.target.value)}
              className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            >
              <option value="">No Project</option>
              {projects.map((p) => (
                <option key={p.project_id} value={p.project_id}>
                  {p.name}
                </option>
              ))}
            </select>
          </div>

          {/* Campaign Name */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">
              Campaign Name
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Q4 Product Launch"
              required
              className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
          </div>

          {/* Budget */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">
              Budget ($)
            </label>
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="10000"
              min="0"
              className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
          </div>

          {/* Channels */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">
              Channels
            </label>
            <div className="flex flex-wrap gap-3">
              {CHANNELS.map((ch) => (
                <label
                  key={ch}
                  className="flex items-center gap-2 text-sm cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={channels.has(ch)}
                    onChange={() => toggleChannel(ch)}
                    className="w-4 h-4 rounded border-[var(--border)] text-[var(--foreground)] focus:ring-[var(--ring)]"
                  />
                  {ch}
                </label>
              ))}
            </div>
          </div>

          {/* Message */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">
              Campaign Message
            </label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Enter the campaign message to simulate..."
              rows={4}
              className="px-3 py-2 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] resize-y"
            />
          </div>

          {/* Target Communities */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">
              Target Communities
            </label>
            <div className="flex flex-wrap gap-2">
              {COMMUNITIES.map((c) => {
                const selected = targetCommunities.has(c.id);
                return (
                  <button
                    key={c.id}
                    type="button"
                    onClick={() => toggleCommunity(c.id)}
                    className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm border transition-colors ${
                      selected
                        ? "border-transparent text-white"
                        : "border-[var(--border)] text-[var(--muted-foreground)] bg-[var(--card)] hover:bg-[var(--secondary)]"
                    }`}
                    style={selected ? { backgroundColor: c.color } : undefined}
                  >
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{
                        backgroundColor: selected ? "white" : c.color,
                      }}
                    />
                    {c.name}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Advanced Settings */}
          <details className="border border-[var(--border)] rounded-lg bg-[var(--card)]">
            <summary className="px-4 py-3 text-sm font-medium text-[var(--foreground)] cursor-pointer select-none">
              Advanced Settings
            </summary>
            <div className="px-4 pb-4 flex flex-col gap-4 border-t border-[var(--border)] pt-4">
              {/* Max Steps */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--muted-foreground)]">
                  Max Steps (simulation days)
                </label>
                <input
                  type="number"
                  value={maxSteps}
                  onChange={(e) => setMaxSteps(Number(e.target.value))}
                  min="1"
                  max="1000"
                  className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
              </div>

              {/* Random Seed */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--muted-foreground)]">
                  Random Seed
                </label>
                <input
                  type="number"
                  value={randomSeed}
                  onChange={(e) => setRandomSeed(Number(e.target.value))}
                  className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
              </div>

              {/* SLM/LLM Ratio */}
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--muted-foreground)]">
                  SLM / LLM Ratio: {slmLlmRatio}% SLM / {100 - slmLlmRatio}%
                  LLM
                </label>
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={slmLlmRatio}
                  onChange={(e) => setSlmLlmRatio(Number(e.target.value))}
                  className="w-full accent-[var(--foreground)]"
                />
                <div className="flex justify-between text-[10px] text-[var(--muted-foreground)]">
                  <span>100% LLM</span>
                  <span>100% SLM</span>
                </div>
              </div>
            </div>
          </details>

          {/* Error Display */}
          {error && (
            <div className="rounded-md bg-[var(--destructive)]/10 border border-[var(--destructive)]/30 p-3 text-sm text-[var(--destructive)]">
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit"
            disabled={submitting || !name}
            className="h-11 px-6 text-sm font-medium text-white bg-[var(--foreground)] rounded-md hover:bg-[var(--foreground)]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? "Creating..." : "Create Simulation"}
          </button>
        </form>
      </div>
    </div>
  );
}
