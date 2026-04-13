/**
 * TanStack Query hooks for the Prophet API.
 *
 * Centralized query/mutation layer. Every page that fetches data SHOULD
 * import from here instead of calling `apiClient` directly. Benefits:
 * - Request deduplication (two components asking for the same data → 1 fetch)
 * - Cross-route caching (navigate away and back → instant)
 * - Automatic background revalidation
 * - Single place to tweak `staleTime`, `retry`, `refetchInterval`
 *
 * Query key conventions:
 *   ['<resource>', <id>?, <subresource>?, <param>?]
 *
 * Example keys:
 *   ['projects']
 *   ['project', projectId]
 *   ['simulation', simId]
 *   ['simulation', simId, 'agents', { limit: 200 }]
 *   ['simulation', simId, 'communities']
 *   ['simulation', simId, 'llm', 'stats']
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#data-fetching
 */
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiClient } from "./client";
import type { SimulationRun } from "../types/simulation";

// ───────── Query keys (typed factory) ─────────
//
// Keep all keys in one place so invalidation in mutations stays in sync
// with the queries that read them. This is the standard TanStack pattern.

export const queryKeys = {
  // Projects
  projects: ["projects"] as const,
  project: (projectId: string) => ["project", projectId] as const,

  // Simulations
  simulations: ["simulations"] as const,
  simulation: (simId: string | null) => ["simulation", simId] as const,
  simulationSteps: (simId: string | null) =>
    ["simulation", simId, "steps"] as const,

  // Per-simulation sub-resources
  agents: (simId: string | null, params?: { limit?: number }) =>
    ["simulation", simId, "agents", params ?? null] as const,
  agent: (simId: string | null, agentId: string | null) =>
    ["simulation", simId, "agent", agentId] as const,
  agentMemory: (simId: string | null, agentId: string | null) =>
    ["simulation", simId, "agent", agentId, "memory"] as const,
  communities: (simId: string | null) =>
    ["simulation", simId, "communities"] as const,
  network: (simId: string | null) =>
    ["simulation", simId, "network"] as const,
  llmStats: (simId: string | null) =>
    ["simulation", simId, "llm", "stats"] as const,
  llmImpact: (simId: string | null) =>
    ["simulation", simId, "llm", "impact"] as const,
} as const;

// ───────── Projects ─────────

export function useProjects() {
  return useQuery({
    queryKey: queryKeys.projects,
    queryFn: () => apiClient.projects.list(),
  });
}

export function useProject(projectId: string | null) {
  return useQuery({
    queryKey: queryKeys.project(projectId ?? ""),
    queryFn: () => apiClient.projects.get(projectId!),
    enabled: !!projectId,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { name: string }) => apiClient.projects.create(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.projects });
    },
  });
}

// ───────── Simulations ─────────

export function useSimulations() {
  return useQuery({
    queryKey: queryKeys.simulations,
    queryFn: () => apiClient.simulations.list(),
  });
}

export function useSimulation(simId: string | null) {
  return useQuery<SimulationRun>({
    queryKey: queryKeys.simulation(simId),
    queryFn: () => apiClient.simulations.get(simId!),
    enabled: !!simId,
  });
}

export function useSimulationSteps(simId: string | null) {
  return useQuery({
    queryKey: queryKeys.simulationSteps(simId),
    queryFn: () => apiClient.simulations.getSteps(simId!),
    enabled: !!simId,
  });
}

export function useSimulationCompare(simIdA: string | null, simIdB: string | null) {
  return useQuery({
    queryKey: ["simulationCompare", simIdA, simIdB] as const,
    queryFn: () => apiClient.simulations.compare(simIdA!, simIdB!),
    enabled: !!simIdA && !!simIdB,
  });
}

// ───────── Agents ─────────

export function useAgents(simId: string | null, params?: { limit?: number }) {
  return useQuery({
    queryKey: queryKeys.agents(simId, params),
    queryFn: () => apiClient.agents.list(simId!, params),
    enabled: !!simId,
  });
}

export function useAgent(simId: string | null, agentId: string | null) {
  return useQuery({
    queryKey: queryKeys.agent(simId, agentId),
    queryFn: () => apiClient.agents.get(simId!, agentId!),
    enabled: !!simId && !!agentId,
  });
}

export function useAgentMemory(simId: string | null, agentId: string | null) {
  return useQuery({
    queryKey: queryKeys.agentMemory(simId, agentId),
    queryFn: () => apiClient.agents.getMemory(simId!, agentId!),
    enabled: !!simId && !!agentId,
  });
}

// ───────── Communities ─────────

export function useCommunities(simId: string | null) {
  return useQuery({
    queryKey: queryKeys.communities(simId),
    queryFn: () => apiClient.communities.list(simId!),
    enabled: !!simId,
  });
}

// ───────── Network ─────────

export function useNetwork(simId: string | null) {
  return useQuery({
    queryKey: queryKeys.network(simId),
    queryFn: () => apiClient.network.get(simId!),
    enabled: !!simId,
  });
}

// ───────── LLM stats ─────────
//
// `step` is part of the query key so the cache invalidates automatically
// when a new simulation step lands. The hook re-fetches once per step
// instead of polling on a timer.

export function useLLMStats(simId: string | null, step: number = 0) {
  return useQuery({
    queryKey: [...queryKeys.llmStats(simId), step] as const,
    queryFn: () => apiClient.llm.getStats(simId!),
    enabled: !!simId,
  });
}

export function useLLMImpact(simId: string | null, step: number = 0) {
  return useQuery({
    queryKey: [...queryKeys.llmImpact(simId), step] as const,
    queryFn: () => apiClient.llm.getImpact(simId!),
    enabled: !!simId,
  });
}

// ───────── Community templates ─────────

export function useCommunityTemplates() {
  return useQuery({
    queryKey: ["communityTemplates"] as const,
    queryFn: () => apiClient.communityTemplates.list(),
  });
}

export function useCreateCommunityTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: Parameters<typeof apiClient.communityTemplates.create>[0]) =>
      apiClient.communityTemplates.create(input),
    onSuccess: () => {
      // refetch (not just invalidate) so consumers see fresh data immediately
      qc.refetchQueries({ queryKey: ["communityTemplates"] });
    },
  });
}

export function useUpdateCommunityTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, payload }: { id: string; payload: Parameters<typeof apiClient.communityTemplates.update>[1] }) =>
      apiClient.communityTemplates.update(id, payload),
    onSuccess: () => {
      // refetch (not just invalidate) so consumers see fresh data immediately
      qc.refetchQueries({ queryKey: ["communityTemplates"] });
    },
  });
}

export function useDeleteCommunityTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiClient.communityTemplates.delete(id),
    onSuccess: () => {
      // refetch (not just invalidate) so consumers see fresh data immediately
      qc.refetchQueries({ queryKey: ["communityTemplates"] });
    },
  });
}

// ───────── Community CRUD (per-simulation) ─────────

export function useCreateCommunity(simId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: Parameters<typeof apiClient.communities.create>[1]) =>
      apiClient.communities.create(simId!, input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.communities(simId) });
    },
  });
}

export function useUpdateCommunity(simId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ communityId, payload }: { communityId: string; payload: Parameters<typeof apiClient.communities.update>[2] }) =>
      apiClient.communities.update(simId!, communityId, payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.communities(simId) });
    },
  });
}

export function useDeleteCommunity(simId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (communityId: string) => apiClient.communities.remove(simId!, communityId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.communities(simId) });
    },
  });
}

// ───────── Community threads (conversations) ─────────

export function useCommunityThreads(simId: string | null, communityId: string | null) {
  return useQuery({
    queryKey: ["simulation", simId, "community", communityId, "threads"] as const,
    queryFn: () => apiClient.communityThreads.list(simId!, communityId!),
    enabled: !!simId && !!communityId,
  });
}

export function useCommunityThread(
  simId: string | null,
  communityId: string | null,
  threadId: string | null,
) {
  return useQuery({
    queryKey: ["simulation", simId, "community", communityId, "thread", threadId] as const,
    queryFn: () => apiClient.communityThreads.get(simId!, communityId!, threadId!),
    enabled: !!simId && !!communityId && !!threadId,
  });
}

// ───────── Community opinion (EliteLLM synthesis) ─────────
//
// The backend caches the result by (sim_id, community_id, current_step),
// so triggering this mutation twice at the same step is idempotent and
// pays for only one LLM call.
// @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis

export function useCommunityOpinionSynthesis(simId: string | null) {
  return useMutation({
    mutationFn: (communityId: string) =>
      apiClient.communityOpinion.synthesize(simId!, communityId),
  });
}

/**
 * Cross-community aggregate narrative — the "whole simulation, told as
 * a story" view. Triggers per-community synthesis as a side-effect so
 * the response always ships the breakdown alongside the headline.
 * @spec docs/spec/25_COMMUNITY_INSIGHT_SPEC.md#5-elitellm-opinion-synthesis
 */
export function useOverallOpinionSynthesis(simId: string | null) {
  return useMutation({
    mutationFn: () => apiClient.communityOpinion.synthesizeOverall(simId!),
  });
}

// ───────── Project scenarios ─────────

export function useCreateScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, data }: {
      projectId: string;
      data: Parameters<typeof apiClient.projects.createScenario>[1];
    }) => apiClient.projects.createScenario(projectId, data),
    onSuccess: (_data, { projectId }) => {
      qc.invalidateQueries({ queryKey: queryKeys.project(projectId) });
    },
  });
}

export function useRunScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, scenarioId }: { projectId: string; scenarioId: string }) =>
      apiClient.projects.runScenario(projectId, scenarioId),
    onSuccess: (_data, { projectId }) => {
      qc.invalidateQueries({ queryKey: queryKeys.project(projectId) });
    },
  });
}

export function useDeleteScenario() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ projectId, scenarioId }: { projectId: string; scenarioId: string }) =>
      apiClient.projects.deleteScenario(projectId, scenarioId),
    onSuccess: (_data, { projectId }) => {
      qc.invalidateQueries({ queryKey: queryKeys.project(projectId) });
    },
  });
}

// ───────── Simulation lifecycle mutations ─────────
//
// Imperative dispatches (start/pause/step/stop/runAll). Main benefit of
// useMutation here is isPending for UI gating + auto invalidation on the
// simulation key.

export function useCreateSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (config: Parameters<typeof apiClient.simulations.create>[0]) =>
      apiClient.simulations.create(config),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: queryKeys.simulations });
    },
  });
}

export function useStartSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (simId: string) => apiClient.simulations.start(simId),
    onSuccess: (_data, simId) => {
      qc.invalidateQueries({ queryKey: queryKeys.simulation(simId) });
    },
  });
}

export function usePauseSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (simId: string) => apiClient.simulations.pause(simId),
    onSuccess: (_data, simId) => {
      qc.invalidateQueries({ queryKey: queryKeys.simulation(simId) });
    },
  });
}

export function useResumeSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (simId: string) => apiClient.simulations.resume(simId),
    onSuccess: (_data, simId) => {
      qc.invalidateQueries({ queryKey: queryKeys.simulation(simId) });
    },
  });
}

export function useStopSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (simId: string) => apiClient.simulations.stop(simId),
    onSuccess: (_data, simId) => {
      qc.invalidateQueries({ queryKey: queryKeys.simulation(simId) });
    },
  });
}

export function useStepSimulation() {
  return useMutation({
    mutationFn: (simId: string) => apiClient.simulations.step(simId),
  });
}

export function useRunAllSimulation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (simId: string) => apiClient.simulations.runAll(simId),
    onSuccess: (_data, simId) => {
      qc.invalidateQueries({ queryKey: queryKeys.simulation(simId) });
    },
  });
}

/**
 * Trigger a simulation export download.
 *
 * Not technically a mutation (it's a window.open() call that the browser
 * handles), but it's exposed here so components never import ``apiClient``
 * directly — they consume the hook instead. This keeps the
 * ``components/** must not import apiClient`` architectural invariant
 * passing.
 */
export function useExportSimulation() {
  return (simId: string, format: "json" | "csv" = "json") => {
    apiClient.simulations.export(simId, format);
  };
}

/** Monte Carlo sweep — explicit user trigger, never auto-fires.
 *  SPEC: docs/spec/29_MONTE_CARLO_SPEC.md#32-hook-mc-fe-02
 */
export function useRunMonteCarlo() {
  return useMutation({
    mutationFn: ({
      simId,
      n_runs,
      max_concurrency,
    }: {
      simId: string;
      n_runs: number;
      max_concurrency?: number;
    }) =>
      apiClient.simulations.runMonteCarlo(simId, { n_runs, max_concurrency }),
  });
}

// ───────── Campaign / intervention dispatches ─────────

export function useInjectEvent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ simId, event }: {
      simId: string;
      event: Parameters<typeof apiClient.simulations.injectEvent>[1];
    }) => apiClient.simulations.injectEvent(simId, event),
    onSuccess: (_data, { simId }) => {
      qc.invalidateQueries({ queryKey: queryKeys.simulation(simId) });
    },
  });
}

export function useReplay() {
  return useMutation({
    mutationFn: ({ simId, step }: { simId: string; step: number }) =>
      apiClient.simulations.replay(simId, step),
  });
}

export function useEngineControl() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ simId, body }: {
      simId: string;
      body: Parameters<typeof apiClient.simulations.engineControl>[1];
    }) => apiClient.simulations.engineControl(simId, body),
    onSuccess: (_data, { simId }) => {
      qc.invalidateQueries({ queryKey: queryKeys.simulation(simId) });
    },
  });
}

export function useModifyAgent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ simId, agentId, body }: {
      simId: string;
      agentId: string;
      body: Parameters<typeof apiClient.agents.modify>[2];
    }) => apiClient.agents.modify(simId, agentId, body),
    onSuccess: (_data, { simId, agentId }) => {
      qc.invalidateQueries({ queryKey: queryKeys.agent(simId, agentId) });
    },
  });
}

// ───────── Auth ─────────

export function useLogin() {
  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      apiClient.auth.login(username, password),
  });
}

export function useRegister() {
  return useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      apiClient.auth.register(username, password),
  });
}
