/**
 * API client for Prophet backend.
 * @spec docs/spec/06_API_SPEC.md
 */

import type { SimulationRun, StepResult } from '../types/simulation';
import { API_VERSION_PREFIX, DEFAULT_API_BASE_URL, LS_KEY_TOKEN } from "@/config/constants";

export interface CommunityConfigInput {
  id: string;
  name: string;
  size: number;
  agent_type: string;
  personality_profile: {
    openness: number;
    skepticism: number;
    trend_following: number;
    brand_loyalty: number;
    social_influence: number;
  };
}

export interface CreateSimulationConfig {
  name: string;
  description?: string;
  project_id?: string;
  campaign: {
    name: string;
    budget?: number;
    channels: string[];
    message: string;
    target_communities: string[];
    controversy?: number;
    novelty?: number;
    utility?: number;
  };
  communities?: CommunityConfigInput[];
  max_steps?: number;
  default_llm_provider?: string;
  random_seed?: number;
  slm_llm_ratio?: number;
  slm_model?: string;
  budget_usd?: number;
}

/** Settings response from GET /api/v1/settings. @spec docs/spec/06_API_SPEC.md#7-settings-endpoints */
export interface SettingsLlm {
  default_provider: string;
  ollama_base_url: string;
  ollama_default_model: string;
  slm_model: string;
  ollama_embed_model: string;
  anthropic_model: string;
  anthropic_api_key_set: boolean;
  openai_model: string;
  openai_api_key_set: boolean;
}

export interface SettingsSimulation {
  slm_llm_ratio: number;
  llm_tier3_ratio: number;
  llm_cache_ttl: number;
}

export interface SettingsResponse {
  llm: SettingsLlm;
  simulation: SettingsSimulation;
}

export interface SettingsUpdateRequest {
  llm?: Partial<{
    default_provider: string;
    ollama_base_url: string;
    ollama_default_model: string;
    slm_model: string;
    ollama_embed_model: string;
    anthropic_api_key: string;
    anthropic_model: string;
    openai_api_key: string;
    openai_model: string;
  }>;
  simulation?: Partial<SettingsSimulation>;
}

/** Agent summary from list endpoint. @spec docs/spec/06_API_SPEC.md#get-agents */
export interface AgentSummary {
  agent_id: string;
  community_id: string;
  agent_type: string;
  action: string;
  adopted: boolean;
  influence_score: number;
  belief: number;
}

/** Full agent detail. @spec docs/spec/06_API_SPEC.md#get-agents-agent_id */
export interface AgentDetail extends AgentSummary {
  personality: Record<string, number>;
  emotion: Record<string, number>;
  memories: MemoryRecord[];
}

/** Agent memory record. */
export interface MemoryRecord {
  memory_type: string;
  content: string;
  timestamp: number;
  importance: number;
  source_agent_id?: string;
}

/** Project summary from list endpoint. @spec docs/spec/06_API_SPEC.md#project-endpoints */
export interface ProjectSummary {
  project_id: string;
  name: string;
  description: string;
  status: string;
  scenario_count: number;
  created_at: string | null;
}

/** Scenario info. @spec docs/spec/06_API_SPEC.md#project-endpoints */
export interface ScenarioInfo {
  scenario_id: string;
  name: string;
  description: string;
  status: string;
  simulation_id: string | null;
  config: Record<string, unknown>;
  created_at: string | null;
}

/** Full project detail including scenarios. @spec docs/spec/06_API_SPEC.md#project-endpoints */
export interface ProjectDetail extends ProjectSummary {
  scenarios: ScenarioInfo[];
}

/** Community info. @spec docs/spec/06_API_SPEC.md#get-communities */
export interface CommunityInfo {
  community_id: string;
  name: string;
  size: number;
  adoption_rate: number;
  mean_belief: number;
  sentiment_variance: number;
  dominant_action: string;
}

/** Thread summary. @spec docs/spec/06_API_SPEC.md#5-community-endpoints */
export interface ThreadSummary {
  thread_id: string;
  topic: string;
  participant_count: number;
  message_count: number;
  avg_sentiment: number;
}

/** Thread message. @spec docs/spec/06_API_SPEC.md#5-community-endpoints */
export interface ThreadMessage {
  message_id: string;
  agent_id: string;
  community_id: string;
  stance: 'Progressive' | 'Conservative' | 'Neutral';
  content: string;
  reactions: { agree: number; disagree: number; nuanced: number };
  is_reply: boolean;
  reply_to_id: string | null;
}

/** Thread detail with messages. @spec docs/spec/06_API_SPEC.md#5-community-endpoints */
export interface ThreadDetail extends ThreadSummary {
  messages: ThreadMessage[];
}

/** Community template. @spec docs/spec/06_API_SPEC.md#community-template-endpoints */
export interface CommunityTemplate {
  template_id: string;
  name: string;
  agent_type: string;
  default_size: number;
  description: string;
  personality_profile: Record<string, number>;
}

/** Input for creating/updating a community template. */
export interface CommunityTemplateInput {
  name: string;
  agent_type: string;
  default_size: number;
  description?: string;
  personality_profile?: Record<string, number>;
}

/** Report returned by POST /simulations/{id}/run-all. @spec docs/spec/06_API_SPEC.md#post-simulationssimulation_idrun-all */
export interface RunAllReport {
  simulation_id: string;
  status: string;
  total_steps: number;
  final_adoption_rate: number;
  final_mean_sentiment: number;
  community_summary: Array<Record<string, unknown>>;
  emergent_events_count: number;
  duration_ms: number;
}

/** Cytoscape graph format. @spec docs/spec/06_API_SPEC.md#get-network */
export interface CytoscapeGraph {
  nodes: Array<{ data: Record<string, unknown> }>;
  edges: Array<{ data: Record<string, unknown> }>;
}

/** Network metrics. @spec docs/spec/06_API_SPEC.md#get-network-metrics */
export interface NetworkMetrics {
  clustering_coefficient: number;
  avg_path_length: number;
  modularity: number;
  density: number;
  total_nodes: number;
  total_edges: number;
}

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
    monteCarlo: (id: string, opts: { n_runs: number; llm_enabled?: boolean }) =>
      request<{ job_id: string }>(`/simulations/${id}/monte-carlo`, { method: "POST", body: JSON.stringify(opts) }),
    getMonteCarloJob: (id: string, jobId: string) =>
      request<Record<string, unknown>>(`/simulations/${id}/monte-carlo/${jobId}`),
    getLatestMonteCarlo: (id: string) =>
      request<Record<string, unknown> | null>(`/simulations/${id}/monte-carlo`),
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
