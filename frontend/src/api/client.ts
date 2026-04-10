/**
 * API client for Prophet backend.
 * @spec docs/spec/06_API_SPEC.md
 * @spec docs/spec/20_CLEAN_ARCHITECTURE_SPEC.md#4.1
 *
 * Thin HTTP layer — all type definitions live in types/api.ts.
 */

import type { SimulationRun, StepResult } from '../types/simulation';
import type { MemoryRecord } from '../types/api';
import { API_VERSION_PREFIX, DEFAULT_API_BASE_URL, LS_KEY_TOKEN } from "@/config/constants";

// Re-export API types so existing consumers don't break
export type {
  CommunityConfigInput,
  CreateSimulationConfig,
  SettingsLlm,
  SettingsSimulation,
  SettingsResponse,
  SettingsUpdateRequest,
  AgentSummary,
  AgentDetail,
  MemoryRecord,
  ProjectSummary,
  ScenarioInfo,
  ProjectDetail,
  CommunityInfo,
  ThreadSummary,
  ThreadMessage,
  ThreadDetail,
  CommunityTemplate,
  CommunityTemplateInput,
  RunAllReport,
  CytoscapeGraph,
  NetworkMetrics,
} from '../types/api';

import type {
  CreateSimulationConfig,
  SettingsResponse,
  SettingsUpdateRequest,
  AgentSummary,
  AgentDetail,
  ProjectSummary,
  ProjectDetail,
  ScenarioInfo,
  CommunityInfo,
  ThreadSummary,
  ThreadDetail,
  CommunityTemplate,
  CommunityTemplateInput,
  RunAllReport,
  CytoscapeGraph,
  NetworkMetrics,
} from '../types/api';

const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}${API_VERSION_PREFIX}`
  : DEFAULT_API_BASE_URL;

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem(LS_KEY_TOKEN);
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE_URL}${path}`, {
    headers,
    ...options,
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const apiClient = {
  simulations: {
    create: (config: CreateSimulationConfig) =>
      request<SimulationRun>("/simulations", { method: "POST", body: JSON.stringify(config) }),
    get: (id: string) => request<SimulationRun>(`/simulations/${id}`),
    list: () => request<{ items: SimulationRun[]; total: number }>("/simulations"),
    start: (id: string) => request<{ status: string }>(`/simulations/${id}/start`, { method: "POST" }),
    step: (id: string) => request<StepResult>(`/simulations/${id}/step`, { method: "POST" }),
    pause: (id: string) => request<{ status: string }>(`/simulations/${id}/pause`, { method: "POST" }),
    resume: (id: string) => request<{ status: string }>(`/simulations/${id}/resume`, { method: "POST" }),
    stop: (id: string) => request<{ status: string }>(`/simulations/${id}/stop`, { method: "POST" }),
    getSteps: async (id: string) => {
      const res = await request<{ steps: StepResult[] }>(`/simulations/${id}/steps`);
      return res.steps ?? [];
    },
    injectEvent: (id: string, event: { event_type: string; content: string; controversy?: number; target_communities?: string[] }) =>
      request<{ event_id: string; effective_step: number }>(`/simulations/${id}/inject-event`, { method: "POST", body: JSON.stringify(event) }),
    replay: (id: string, step: number) =>
      request<{ replay_id: string; from_step: number }>(`/simulations/${id}/replay/${step}`, { method: "POST" }),
    compare: (id: string, otherId: string) =>
      request<Record<string, unknown>>(`/simulations/${id}/compare/${otherId}`),
    engineControl: (id: string, body: { slm_llm_ratio: number; slm_model?: string; budget_usd?: number }) =>
      request<Record<string, unknown>>(`/simulations/${id}/engine-control`, { method: "POST", body: JSON.stringify(body) }),
    runAll: (id: string) =>
      request<RunAllReport>(`/simulations/${id}/run-all`, { method: "POST" }),
    recommendEngine: (body: { agent_count: number; budget_usd: number; max_steps?: number }) =>
      request<Record<string, unknown>>("/simulations/recommend-engine", { method: "POST", body: JSON.stringify(body) }),
    export: (id: string, format: 'json' | 'csv' = 'json') => {
      window.open(`${BASE_URL}/simulations/${id}/export?format=${format}`, '_blank');
    },
  },
  agents: {
    list: (simId: string, params?: { community_id?: string; limit?: number; offset?: number }) => {
      const q = new URLSearchParams();
      if (params?.community_id) q.set("community_id", params.community_id);
      if (params?.limit) q.set("limit", String(params.limit));
      if (params?.offset) q.set("offset", String(params.offset));
      const qs = q.toString();
      return request<{ items: AgentSummary[]; total: number }>(`/simulations/${simId}/agents${qs ? `?${qs}` : ""}`);
    },
    get: (simId: string, agentId: string) =>
      request<AgentDetail>(`/simulations/${simId}/agents/${agentId}`),
    modify: (simId: string, agentId: string, body: Record<string, unknown>) =>
      request<AgentDetail>(`/simulations/${simId}/agents/${agentId}`, { method: "PATCH", body: JSON.stringify(body) }),
    getMemory: (simId: string, agentId: string) =>
      request<{ memories: MemoryRecord[] }>(`/simulations/${simId}/agents/${agentId}/memory`),
  },
  communities: {
    list: (simId: string) =>
      request<{ communities: CommunityInfo[] }>(`/simulations/${simId}/communities/`),
    update: (simId: string, communityId: string, data: { name?: string; personality_profile?: Record<string, number> }) =>
      request(`/simulations/${simId}/communities/${communityId}`, { method: "PATCH", body: JSON.stringify(data) }),
    create: (simId: string, data: { name: string; agent_type?: string; size: number; personality_profile?: Record<string, number> }) =>
      request(`/simulations/${simId}/communities/`, { method: "POST", body: JSON.stringify(data) }),
    remove: (simId: string, communityId: string) =>
      request(`/simulations/${simId}/communities/${communityId}`, { method: "DELETE" }),
    reassign: (simId: string, communityId: string, data: { agent_ids: string[]; target_community_id: string }) =>
      request(`/simulations/${simId}/communities/${communityId}/reassign`, { method: "POST", body: JSON.stringify(data) }),
  },
  communityThreads: {
    list: (simId: string, communityId: string) =>
      request<{ threads: ThreadSummary[] }>(`/simulations/${simId}/communities/${communityId}/threads`),
    get: (simId: string, communityId: string, threadId: string) =>
      request<ThreadDetail>(`/simulations/${simId}/communities/${communityId}/threads/${threadId}`),
  },
  communityTemplates: {
    list: () => request<{ templates: CommunityTemplate[] }>("/communities/templates/"),
    create: (data: CommunityTemplateInput) =>
      request<CommunityTemplate>("/communities/templates/", { method: "POST", body: JSON.stringify(data) }),
    update: (id: string, data: CommunityTemplateInput) =>
      request<CommunityTemplate>(`/communities/templates/${id}`, { method: "PUT", body: JSON.stringify(data) }),
    delete: (id: string) =>
      request<void>(`/communities/templates/${id}`, { method: "DELETE" }),
  },
  projects: {
    list: () => request<ProjectSummary[]>("/projects/"),
    get: (id: string) => request<ProjectDetail>(`/projects/${id}`),
    create: (data: { name: string; description?: string }) =>
      request<ProjectSummary>("/projects/", { method: "POST", body: JSON.stringify(data) }),
    createScenario: (projectId: string, data: { name: string; description?: string; config?: Record<string, unknown> }) =>
      request<ScenarioInfo>(`/projects/${projectId}/scenarios`, { method: "POST", body: JSON.stringify(data) }),
    runScenario: (projectId: string, scenarioId: string) =>
      request<{ simulation_id: string; status: string }>(`/projects/${projectId}/scenarios/${scenarioId}/run`, { method: "POST" }),
    deleteScenario: (projectId: string, scenarioId: string) =>
      request<void>(`/projects/${projectId}/scenarios/${scenarioId}`, { method: "DELETE" }),
    update: (id: string, data: { name?: string; description?: string }) =>
      request<ProjectSummary>(`/projects/${id}`, { method: "PATCH", body: JSON.stringify(data) }),
    delete: (id: string) =>
      request<void>(`/projects/${id}`, { method: "DELETE" }),
  },
  network: {
    get: (simId: string) => request<CytoscapeGraph>(`/simulations/${simId}/network/?format=cytoscape`),
    getSummary: (simId: string) =>
      request<CytoscapeGraph>(`/simulations/${simId}/network/?summary=true`),
    getMetrics: (simId: string) =>
      request<NetworkMetrics>(`/simulations/${simId}/network/metrics`),
  },
  llm: {
    getStats: (simId: string) => request(`/simulations/${simId}/llm/stats`),
    getImpact: (simId: string) => request(`/simulations/${simId}/llm/impact`),
    getCalls: (simId: string, params?: { step?: number; agent_id?: string; provider?: string; limit?: number }) => {
      const q = new URLSearchParams();
      if (params?.step != null) q.set("step", String(params.step));
      if (params?.agent_id) q.set("agent_id", params.agent_id);
      if (params?.provider) q.set("provider", params.provider);
      if (params?.limit != null) q.set("limit", String(params.limit));
      const qs = q.toString();
      return request(`/simulations/${simId}/llm/calls${qs ? `?${qs}` : ""}`);
    },
  },
  auth: {
    register: (username: string, password: string) =>
      request<{ user_id: string; username: string }>("/auth/register", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }),
    login: (username: string, password: string) =>
      request<{ token: string; user_id: string; username: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ username, password }),
      }),
    me: () => request<{ user_id: string; username: string }>("/auth/me"),
  },
  settings: {
    get: () => request<SettingsResponse>("/settings/"),
    update: (data: SettingsUpdateRequest) =>
      request<{ status: string }>("/settings/", { method: "PUT", body: JSON.stringify(data) }),
    listOllamaModels: () => request<{ models: string[] }>("/settings/ollama-models"),
    testOllama: () =>
      request<{ status: string; model?: string; latency_ms?: number; message?: string }>(
        "/settings/test-ollama",
        { method: "POST" },
      ),
    listPlatforms: () => request<{ platforms: unknown[] }>("/settings/platforms"),
    listRecsys: () => request<{ algorithms: unknown[] }>("/settings/recsys"),
  },
};
