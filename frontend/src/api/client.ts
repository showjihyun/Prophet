/**
 * API client for Prophet backend.
 * @spec docs/spec/06_API_SPEC.md
 */

import type { SimulationRun, StepResult } from '../types/simulation';

export interface CreateSimulationConfig {
  name: string;
  description?: string;
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

const BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api/v1`
  : "http://localhost:8000/api/v1";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
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
    getSteps: (id: string) => request<StepResult[]>(`/simulations/${id}/steps`),
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
    engineControl: (id: string, body: { slm_llm_ratio: number; slm_model?: string; budget_usd?: number }) =>
      request<Record<string, unknown>>(`/simulations/${id}/engine-control`, { method: "POST", body: JSON.stringify(body) }),
    recommendEngine: (body: { agent_count: number; budget_usd: number; max_steps?: number }) =>
      request<Record<string, unknown>>("/simulations/recommend-engine", { method: "POST", body: JSON.stringify(body) }),
  },
  agents: {
    list: (simId: string) => request(`/simulations/${simId}/agents`),
    get: (simId: string, agentId: string) =>
      request(`/simulations/${simId}/agents/${agentId}`),
    modify: (simId: string, agentId: string, body: Record<string, unknown>) =>
      request<Record<string, unknown>>(`/simulations/${simId}/agents/${agentId}`, { method: "PATCH", body: JSON.stringify(body) }),
    getMemory: (simId: string, agentId: string) =>
      request<{ memories: unknown[] }>(`/simulations/${simId}/agents/${agentId}/memory`),
  },
  network: {
    get: (simId: string) => request(`/simulations/${simId}/network?format=cytoscape`),
    getMetrics: (simId: string) =>
      request<Record<string, unknown>>(`/simulations/${simId}/network/metrics`),
  },
  llm: {
    getStats: (simId: string) => request(`/simulations/${simId}/llm/stats`),
    getImpact: (simId: string) => request(`/simulations/${simId}/llm/impact`),
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
