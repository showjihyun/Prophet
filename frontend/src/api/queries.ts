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
