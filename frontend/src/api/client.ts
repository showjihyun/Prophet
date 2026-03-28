/**
 * API client for Prophet backend.
 * @spec docs/spec/06_API_SPEC.md
 */

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
    create: (config: unknown) =>
      request("/simulations", { method: "POST", body: JSON.stringify(config) }),
    get: (id: string) => request(`/simulations/${id}`),
    list: () => request("/simulations"),
    start: (id: string) => request(`/simulations/${id}/start`, { method: "POST" }),
    step: (id: string) => request(`/simulations/${id}/step`, { method: "POST" }),
    pause: (id: string) => request(`/simulations/${id}/pause`, { method: "POST" }),
    resume: (id: string) => request(`/simulations/${id}/resume`, { method: "POST" }),
    stop: (id: string) => request(`/simulations/${id}/stop`, { method: "POST" }),
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
