/**
 * CampaignSetupPage — Campaign creation form with simulation parameters.
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md
 */
import { useState, useEffect, useCallback } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { apiClient } from "../api/client";
import type { CreateSimulationConfig, CommunityConfigInput, CommunityTemplate, ProjectSummary } from "../api/client";
import PageNav from "../components/shared/PageNav";
import { useSimulationStore } from "../store/simulationStore";

const CHANNELS = ["SNS", "Influencer", "Online Ads", "TV", "Email"] as const;
const AGENT_TYPES = ["early_adopter", "consumer", "skeptic", "expert", "influencer", "bridge"] as const;

const PERSONALITY_KEYS = ["openness", "skepticism", "trend_following", "brand_loyalty", "social_influence"] as const;
const PERSONALITY_LABELS: Record<string, string> = {
  openness: "Openness",
  skepticism: "Skepticism",
  trend_following: "Trend Following",
  brand_loyalty: "Brand Loyalty",
  social_influence: "Social Influence",
};

const COMMUNITY_COLORS = ["#3b82f6", "#22c55e", "#f97316", "#a855f7", "#ef4444", "#06b6d4", "#ec4899", "#84cc16"];

function defaultCommunity(index: number): CommunityConfigInput {
  return {
    id: String.fromCharCode(65 + index),
    name: `Community ${String.fromCharCode(65 + index)}`,
    size: 100,
    agent_type: "consumer",
    personality_profile: { openness: 0.5, skepticism: 0.5, trend_following: 0.5, brand_loyalty: 0.5, social_influence: 0.5 },
  };
}

export default function CampaignSetupPage() {
  const navigate = useNavigate();
  const { projectId: urlProjectId } = useParams<{ projectId: string }>();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(urlProjectId ?? "");

  useEffect(() => {
    apiClient.projects.list().then((res) => setProjects(Array.isArray(res) ? res : [])).catch(() => {});
  }, []);

  const cloneConfig = useSimulationStore((s) => s.cloneConfig);
  const setCloneConfig = useSimulationStore((s) => s.setCloneConfig);

  // Campaign info
  const [name, setName] = useState("");
  const [budget, setBudget] = useState("");
  const [channels, setChannels] = useState<Set<string>>(new Set());
  const [message, setMessage] = useState("");
  const [targetCommunities, setTargetCommunities] = useState<Set<string>>(new Set());

  // Campaign attributes (A-1)
  const [controversy, setControversy] = useState(0.1);
  const [novelty, setNovelty] = useState(0.5);
  const [utility, setUtility] = useState(0.5);

  // Community configuration (A-2)
  const [communities, setCommunities] = useState<CommunityConfigInput[]>([]);
  const [communityOpen, setCommunityOpen] = useState(false);

  // Advanced
  const [maxSteps, setMaxSteps] = useState(365);
  const [randomSeed, setRandomSeed] = useState(42);
  const [slmLlmRatio, setSlmLlmRatio] = useState(80);
  const [llmProvider, setLlmProvider] = useState("ollama");

  // Pre-fill from cloneConfig
  useEffect(() => {
    if (!cloneConfig) return;
    setName(cloneConfig.name ?? "");
    setChannels(new Set(cloneConfig.campaign?.channels ?? []));
    setMessage(cloneConfig.campaign?.message ?? "");
    setTargetCommunities(new Set(cloneConfig.campaign?.target_communities ?? []));
    if (cloneConfig.campaign?.controversy != null) setControversy(cloneConfig.campaign.controversy);
    if (cloneConfig.campaign?.novelty != null) setNovelty(cloneConfig.campaign.novelty);
    if (cloneConfig.campaign?.utility != null) setUtility(cloneConfig.campaign.utility);
    if (cloneConfig.communities) setCommunities(cloneConfig.communities);
    if (cloneConfig.max_steps) setMaxSteps(cloneConfig.max_steps);
    if (cloneConfig.random_seed) setRandomSeed(cloneConfig.random_seed);
    if (cloneConfig.slm_llm_ratio != null) setSlmLlmRatio(Math.round(cloneConfig.slm_llm_ratio * 100));
    if (cloneConfig.default_llm_provider) setLlmProvider(cloneConfig.default_llm_provider);
    if (cloneConfig.campaign?.budget) setBudget(String(cloneConfig.campaign.budget));
    setCloneConfig(null);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadTemplates = useCallback(async () => {
    try {
      const res = await apiClient.communityTemplates.list();
      const templates = res.templates ?? [];
      const loaded: CommunityConfigInput[] = templates.map((t: CommunityTemplate, i: number) => ({
        id: t.template_id,
        name: t.name,
        size: t.default_size,
        agent_type: t.agent_type,
        personality_profile: {
          openness: t.personality_profile?.openness ?? 0.5,
          skepticism: t.personality_profile?.skepticism ?? 0.5,
          trend_following: t.personality_profile?.trend_following ?? 0.5,
          brand_loyalty: t.personality_profile?.brand_loyalty ?? 0.5,
          social_influence: t.personality_profile?.social_influence ?? 0.5,
        },
      }));
      setCommunities(loaded);
      setCommunityOpen(true);
      // Sync target communities to loaded IDs
      setTargetCommunities(new Set());
    } catch {
      setError("Failed to load community templates");
    }
  }, []);

  function toggleChannel(ch: string) {
    setChannels((prev) => {
      const next = new Set(prev);
      if (next.has(ch)) next.delete(ch); else next.add(ch);
      return next;
    });
  }

  function toggleCommunity(id: string) {
    setTargetCommunities((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  function updateCommunity(index: number, updates: Partial<CommunityConfigInput>) {
    setCommunities((prev) => prev.map((c, i) => (i === index ? { ...c, ...updates } : c)));
  }

  function updatePersonality(index: number, key: string, value: number) {
    setCommunities((prev) =>
      prev.map((c, i) =>
        i === index ? { ...c, personality_profile: { ...c.personality_profile, [key]: value } } : c,
      ),
    );
  }

  function removeCommunity(index: number) {
    if (communities.length <= 1) return;
    const removedId = communities[index].id;
    setCommunities((prev) => prev.filter((_, i) => i !== index));
    setTargetCommunities((prev) => {
      const next = new Set(prev);
      next.delete(removedId);
      return next;
    });
  }

  function addCommunity() {
    setCommunities((prev) => [...prev, defaultCommunity(prev.length)]);
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedProjectId) {
      setError("Please select a project before creating a simulation.");
      return;
    }
    if (communities.length > 0) {
      const invalidComm = communities.find((c) => c.size < 10 || c.size > 5000);
      if (invalidComm) {
        setError(`Community "${invalidComm.name}": agent count must be between 10 and 5000.`);
        return;
      }
      const emptyName = communities.find((c) => !c.name.trim());
      if (emptyName) {
        setError("All communities must have a name.");
        return;
      }
    }
    if (maxSteps < 1 || maxSteps > 1000) {
      setError("Max steps must be between 1 and 1000.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const config: CreateSimulationConfig = {
        name,
        campaign: {
          name,
          budget: Number(budget) || 0,
          channels: Array.from(channels),
          message,
          target_communities: targetCommunities.size > 0 ? Array.from(targetCommunities) : ["all"],
          controversy,
          novelty,
          utility,
        },
        communities: communities.length > 0 ? communities : undefined,
        max_steps: maxSteps,
        default_llm_provider: llmProvider,
        random_seed: randomSeed,
        slm_llm_ratio: slmLlmRatio / 100,
      };
      const sim = await apiClient.simulations.create(config);
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
      await apiClient.projects.createScenario(selectedProjectId, {
        name: config.name,
        config: { simulation_id: sim.simulation_id },
      }).catch(() => {});
      navigate("/simulation");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create simulation");
      setSubmitting(false);
    }
  }

  // Derive community IDs for target selection
  const communityOptions = communities.length > 0
    ? communities.map((c, i) => ({ id: c.id, name: c.name, color: COMMUNITY_COLORS[i % COMMUNITY_COLORS.length] }))
    : [
        { id: "alpha", name: "Alpha", color: "#3b82f6" },
        { id: "beta", name: "Beta", color: "#22c55e" },
        { id: "gamma", name: "Gamma", color: "#f97316" },
        { id: "delta", name: "Delta", color: "#a855f7" },
        { id: "bridge", name: "Bridge", color: "#ef4444" },
      ];

  return (
    <div data-testid="campaign-setup-page" className="min-h-screen bg-[var(--background)] flex flex-col">
      <PageNav
        breadcrumbs={[
          { label: "Projects", href: "/projects" },
          ...(urlProjectId ? [{ label: "Project", href: `/projects/${urlProjectId}` }] : []),
          { label: "Campaign Setup" },
        ]}
      />

      <div className="flex-1 p-6 flex justify-center overflow-auto">
        <form onSubmit={handleSubmit} className="w-full max-w-2xl flex flex-col gap-6">
          <h1 className="text-xl font-bold font-display text-[var(--foreground)]">Create New Simulation</h1>

          {/* Section 1: Project Selector */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">Project</label>
            {urlProjectId ? (
              <input
                type="text"
                readOnly
                value={projects.find((p) => p.project_id === urlProjectId)?.name ?? urlProjectId}
                className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--secondary)] text-[var(--muted-foreground)] cursor-not-allowed"
              />
            ) : (
              <select
                value={selectedProjectId}
                onChange={(e) => setSelectedProjectId(e.target.value)}
                className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
              >
                <option value="">Select a project...</option>
                {projects.map((p) => (
                  <option key={p.project_id} value={p.project_id}>{p.name}</option>
                ))}
              </select>
            )}
          </div>

          {/* Section 2: Campaign Info */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">Campaign Name</label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g., Q4 Product Launch"
              required
              className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">Budget ($)</label>
            <input
              type="number"
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              placeholder="10000"
              min="0"
              className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
            />
          </div>

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">Channels</label>
            <div className="flex flex-wrap gap-3">
              {CHANNELS.map((ch) => (
                <label key={ch} className="flex items-center gap-2 text-sm cursor-pointer">
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

          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">Campaign Message</label>
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Enter the campaign message to simulate..."
              rows={4}
              className="px-3 py-2 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)] resize-y"
            />
          </div>

          {/* Section 3: Target Communities */}
          <div className="flex flex-col gap-1.5">
            <label className="text-sm font-medium text-[var(--foreground)]">Target Communities</label>
            <p className="text-xs text-[var(--muted-foreground)]">Select none to target all communities</p>
            <div className="flex flex-wrap gap-2">
              {communityOptions.map((c) => {
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
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: selected ? "white" : c.color }} />
                    {c.name}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Section 4: Campaign Attributes (A-1) */}
          <div className="flex flex-col gap-4 border border-[var(--border)] rounded-lg bg-[var(--card)] p-4">
            <h2 className="text-sm font-semibold text-[var(--foreground)]">Campaign Attributes</h2>
            <div className="flex flex-col gap-3">
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <label className="text-sm text-[var(--muted-foreground)]">Controversy</label>
                  <span className="text-xs font-mono text-[var(--muted-foreground)]">{controversy.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={controversy}
                  onChange={(e) => setControversy(Number(e.target.value))}
                  className="w-full accent-[var(--foreground)]"
                />
                <p className="text-[10px] text-[var(--muted-foreground)]">Higher values cause polarization and heated debate</p>
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <label className="text-sm text-[var(--muted-foreground)]">Novelty</label>
                  <span className="text-xs font-mono text-[var(--muted-foreground)]">{novelty.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={novelty}
                  onChange={(e) => setNovelty(Number(e.target.value))}
                  className="w-full accent-[var(--foreground)]"
                />
                <p className="text-[10px] text-[var(--muted-foreground)]">Higher values increase attention and curiosity</p>
              </div>
              <div className="flex flex-col gap-1">
                <div className="flex items-center justify-between">
                  <label className="text-sm text-[var(--muted-foreground)]">Utility</label>
                  <span className="text-xs font-mono text-[var(--muted-foreground)]">{utility.toFixed(1)}</span>
                </div>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.1"
                  value={utility}
                  onChange={(e) => setUtility(Number(e.target.value))}
                  className="w-full accent-[var(--foreground)]"
                />
                <p className="text-[10px] text-[var(--muted-foreground)]">Higher values increase adoption likelihood</p>
              </div>
            </div>
          </div>

          {/* Section 5: Community Configuration (A-2) */}
          <details
            open={communityOpen}
            onToggle={(e) => setCommunityOpen((e.target as HTMLDetailsElement).open)}
            className="border border-[var(--border)] rounded-lg bg-[var(--card)]"
          >
            <summary className="px-4 py-3 text-sm font-medium text-[var(--foreground)] cursor-pointer select-none flex items-center justify-between">
              <span>Community Configuration ({communities.length} communities)</span>
            </summary>
            <div className="px-4 pb-4 border-t border-[var(--border)] pt-4 flex flex-col gap-4">
              <button
                type="button"
                onClick={loadTemplates}
                className="self-start px-3 py-1.5 text-xs font-medium border border-[var(--border)] rounded-md bg-[var(--secondary)] hover:bg-[var(--accent)] transition-colors"
              >
                Load from Templates
              </button>

              {communities.map((comm, idx) => (
                <div
                  key={idx}
                  className="border border-[var(--border)] rounded-lg p-4 flex flex-col gap-3"
                  style={{ borderLeftColor: COMMUNITY_COLORS[idx % COMMUNITY_COLORS.length], borderLeftWidth: 3 }}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-semibold text-[var(--foreground)]">{comm.name || `Community ${idx + 1}`}</span>
                    <button
                      type="button"
                      onClick={() => removeCommunity(idx)}
                      disabled={communities.length <= 1}
                      className="text-xs text-[var(--destructive)] hover:underline disabled:opacity-30 disabled:cursor-not-allowed"
                    >
                      Remove
                    </button>
                  </div>

                  <div className="grid grid-cols-3 gap-3">
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-[var(--muted-foreground)]">Name</label>
                      <input
                        type="text"
                        value={comm.name}
                        onChange={(e) => updateCommunity(idx, { name: e.target.value })}
                        className="h-8 px-2 text-xs border border-[var(--border)] rounded bg-[var(--background)] focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
                      />
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-[var(--muted-foreground)]">Agent Type</label>
                      <select
                        value={comm.agent_type}
                        onChange={(e) => updateCommunity(idx, { agent_type: e.target.value })}
                        className="h-8 px-2 text-xs border border-[var(--border)] rounded bg-[var(--background)] focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
                      >
                        {AGENT_TYPES.map((t) => (
                          <option key={t} value={t}>{t.replace("_", " ")}</option>
                        ))}
                      </select>
                    </div>
                    <div className="flex flex-col gap-1">
                      <label className="text-xs text-[var(--muted-foreground)]">Agent Count</label>
                      <input
                        type="number"
                        value={comm.size}
                        onChange={(e) => updateCommunity(idx, { size: Math.max(10, Math.min(5000, Number(e.target.value))) })}
                        min={10}
                        max={5000}
                        className="h-8 px-2 text-xs border border-[var(--border)] rounded bg-[var(--background)] focus:outline-none focus:ring-1 focus:ring-[var(--ring)]"
                      />
                    </div>
                  </div>

                  {/* Personality Sliders */}
                  <div className="flex flex-col gap-2">
                    <span className="text-xs font-medium text-[var(--muted-foreground)]">Personality Profile</span>
                    {PERSONALITY_KEYS.map((key) => (
                      <div key={key} className="flex items-center gap-2">
                        <span className="text-[11px] text-[var(--muted-foreground)] w-28 shrink-0">
                          {PERSONALITY_LABELS[key]}
                        </span>
                        <input
                          type="range"
                          min="0"
                          max="1"
                          step="0.05"
                          value={comm.personality_profile[key as keyof typeof comm.personality_profile]}
                          onChange={(e) => updatePersonality(idx, key, Number(e.target.value))}
                          className="flex-1 accent-[var(--foreground)] h-1"
                        />
                        <span className="text-[10px] font-mono text-[var(--muted-foreground)] w-8 text-right">
                          {(comm.personality_profile[key as keyof typeof comm.personality_profile]).toFixed(2)}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ))}

              <button
                type="button"
                onClick={addCommunity}
                className="self-start px-3 py-1.5 text-xs font-medium border border-dashed border-[var(--border)] rounded-md hover:bg-[var(--secondary)] transition-colors"
              >
                + Add Community
              </button>
            </div>
          </details>

          {/* Section 6: Advanced Settings */}
          <details className="border border-[var(--border)] rounded-lg bg-[var(--card)]">
            <summary className="px-4 py-3 text-sm font-medium text-[var(--foreground)] cursor-pointer select-none">
              Advanced Settings
            </summary>
            <div className="px-4 pb-4 flex flex-col gap-4 border-t border-[var(--border)] pt-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--muted-foreground)]">Max Steps (simulation days)</label>
                <input
                  type="number"
                  value={maxSteps}
                  onChange={(e) => setMaxSteps(Number(e.target.value))}
                  min="1"
                  max="1000"
                  className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--muted-foreground)]">Random Seed</label>
                <input
                  type="number"
                  value={randomSeed}
                  onChange={(e) => setRandomSeed(Number(e.target.value))}
                  className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--muted-foreground)]">LLM Provider</label>
                <select
                  value={llmProvider}
                  onChange={(e) => setLlmProvider(e.target.value)}
                  className="h-10 px-3 text-sm border border-[var(--border)] rounded-md bg-[var(--card)] focus:outline-none focus:ring-2 focus:ring-[var(--ring)]"
                >
                  <option value="ollama">Ollama (Local)</option>
                  <option value="claude">Claude API</option>
                  <option value="openai">OpenAI API</option>
                </select>
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-[var(--muted-foreground)]">
                  SLM / LLM Ratio: {slmLlmRatio}% SLM / {100 - slmLlmRatio}% LLM
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
            disabled={submitting || !name || !selectedProjectId}
            className="h-11 px-6 text-sm font-medium text-white bg-[var(--foreground)] rounded-md hover:bg-[var(--foreground)]/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {submitting ? "Creating..." : "Create Simulation"}
          </button>
        </form>
      </div>
    </div>
  );
}
