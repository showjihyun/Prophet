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
  },
  agents: {
    list: (simId: string) => request(`/simulations/${simId}/agents`),
    get: (simId: string, agentId: string) =>
      request(`/simulations/${simId}/agents/${agentId}`),
  },
  network: {
    get: (simId: string) => request(`/simulations/${simId}/network?format=cytoscape`),
  },
  llm: {
    getStats: (simId: string) => request(`/simulations/${simId}/llm/stats`),
    getImpact: (simId: string) => request(`/simulations/${simId}/llm/impact`),
  },
};
