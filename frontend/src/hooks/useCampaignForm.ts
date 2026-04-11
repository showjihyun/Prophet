/**
 * useCampaignForm — encapsulates all state, derived values, and handlers
 * for the Campaign Setup form. Extracted from the monolithic
 * CampaignSetupPage (SPEC: docs/spec/ui/UI_16_CAMPAIGN_SETUP.md).
 *
 * The page + section components are pure presentation; all state
 * management and submission logic lives here so it can be tested in
 * isolation and swapped without touching the markup.
 */
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import type {
  CommunityConfigInput,
  CreateSimulationConfig,
  CommunityTemplate,
  ProjectSummary,
} from "../api/client";
import {
  useProjects,
  useCommunityTemplates,
  useCreateSimulation,
  useCreateScenario,
} from "../api/queries";
import { useSimulationStore } from "../store/simulationStore";
import {
  COMMUNITY_COLORS,
  FALLBACK_COMMUNITY_OPTIONS,
  defaultCommunity,
} from "../components/campaign/types";

export interface UseCampaignFormArgs {
  /** Project id from the URL (locks the project selector if present). */
  urlProjectId?: string;
}

export function useCampaignForm({ urlProjectId }: UseCampaignFormArgs) {
  const navigate = useNavigate();

  // ─── Queries ──────────────────────────────────────────────────────────
  const projectsQuery = useProjects();
  const projects: ProjectSummary[] = Array.isArray(projectsQuery.data)
    ? projectsQuery.data
    : [];
  const templatesQuery = useCommunityTemplates();
  const createSimulation = useCreateSimulation();
  const createScenario = useCreateScenario();

  // ─── Clone config (from a previous sim being duplicated) ──────────────
  const cloneConfig = useSimulationStore((s) => s.cloneConfig);
  const setCloneConfig = useSimulationStore((s) => s.setCloneConfig);

  // ─── Top-level state ──────────────────────────────────────────────────
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProjectId, setSelectedProjectId] = useState<string>(urlProjectId ?? "");

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

  // ─── Clone pre-fill (runs once on mount) ──────────────────────────────
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

  // ─── Handlers ─────────────────────────────────────────────────────────
  const toggleChannel = useCallback((ch: string) => {
    setChannels((prev) => {
      const next = new Set(prev);
      if (next.has(ch)) next.delete(ch);
      else next.add(ch);
      return next;
    });
  }, []);

  const toggleCommunity = useCallback((id: string) => {
    setTargetCommunities((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const updateCommunity = useCallback(
    (index: number, updates: Partial<CommunityConfigInput>) => {
      setCommunities((prev) => prev.map((c, i) => (i === index ? { ...c, ...updates } : c)));
    },
    [],
  );

  const updatePersonality = useCallback((index: number, key: string, value: number) => {
    setCommunities((prev) =>
      prev.map((c, i) =>
        i === index ? { ...c, personality_profile: { ...c.personality_profile, [key]: value } } : c,
      ),
    );
  }, []);

  const removeCommunity = useCallback((index: number) => {
    let removedId = "";
    setCommunities((prev) => {
      if (prev.length <= 1) return prev;
      removedId = prev[index].id;
      return prev.filter((_, i) => i !== index);
    });
    if (removedId) {
      setTargetCommunities((prev) => {
        const next = new Set(prev);
        next.delete(removedId);
        return next;
      });
    }
  }, []);

  const addCommunity = useCallback(() => {
    setCommunities((prev) => [...prev, defaultCommunity(prev.length)]);
  }, []);

  const loadTemplates = useCallback(async () => {
    try {
      const res = templatesQuery.data ?? (await templatesQuery.refetch()).data;
      const templates = res?.templates ?? [];
      const loaded: CommunityConfigInput[] = templates.map((t: CommunityTemplate) => ({
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
      setTargetCommunities(new Set());
    } catch {
      setError("Failed to load community templates");
    }
  }, [templatesQuery]);

  // ─── Submit ───────────────────────────────────────────────────────────
  const handleSubmit = useCallback(
    async (e: React.FormEvent) => {
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
        const sim = await createSimulation.mutateAsync(config);
        const { setSimulation, setStatus } = useSimulationStore.getState();
        setSimulation({
          simulation_id: sim.simulation_id,
          name: config.name,
          status: sim.status,
          current_step: 0,
          max_steps: config.max_steps ?? 50,
          created_at: new Date().toISOString(),
        });
        setStatus(sim.status);
        await createScenario
          .mutateAsync({
            projectId: selectedProjectId,
            data: {
              name: config.name,
              config: { simulation_id: sim.simulation_id },
            },
          })
          .catch(() => {});
        navigate(`/simulation/${sim.simulation_id}`);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to create simulation");
        setSubmitting(false);
      }
    },
    [
      selectedProjectId,
      communities,
      maxSteps,
      name,
      budget,
      channels,
      message,
      targetCommunities,
      controversy,
      novelty,
      utility,
      llmProvider,
      randomSeed,
      slmLlmRatio,
      createSimulation,
      createScenario,
      navigate,
    ],
  );

  // ─── Derived values ───────────────────────────────────────────────────
  const communityOptions =
    communities.length > 0
      ? communities.map((c, i) => ({
          id: c.id,
          name: c.name,
          color: COMMUNITY_COLORS[i % COMMUNITY_COLORS.length],
        }))
      : FALLBACK_COMMUNITY_OPTIONS;

  return {
    // Queries/projects
    projects,
    // Form state
    selectedProjectId,
    setSelectedProjectId,
    name,
    setName,
    budget,
    setBudget,
    channels,
    message,
    setMessage,
    targetCommunities,
    controversy,
    setControversy,
    novelty,
    setNovelty,
    utility,
    setUtility,
    communities,
    communityOpen,
    setCommunityOpen,
    maxSteps,
    setMaxSteps,
    randomSeed,
    setRandomSeed,
    slmLlmRatio,
    setSlmLlmRatio,
    llmProvider,
    setLlmProvider,
    // Derived
    communityOptions,
    // Handlers
    toggleChannel,
    toggleCommunity,
    updateCommunity,
    updatePersonality,
    removeCommunity,
    addCommunity,
    loadTemplates,
    handleSubmit,
    // Submission status
    submitting,
    error,
  };
}
