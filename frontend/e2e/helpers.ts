/**
 * E2E test helpers — shared utilities for Playwright tests.
 */
import type { APIRequestContext } from '@playwright/test';

export const API = 'http://localhost:8000/api/v1';

/**
 * Stop all running simulations to free up concurrent slots.
 * Call this in beforeAll/beforeEach to avoid SimulationCapacityError.
 */
export async function cleanupRunningSimulations(request: APIRequestContext): Promise<void> {
  try {
    const res = await request.get(`${API}/simulations/`);
    if (!res.ok()) return;
    const body = await res.json();
    const items = body.items || [];
    // Stop all running/paused sims to free concurrent slots
    for (const sim of items) {
      if (sim.status === 'running' || sim.status === 'paused') {
        try {
          await request.post(`${API}/simulations/${sim.simulation_id}/stop/`);
        } catch { /* ignore */ }
      }
    }
  } catch {
    // ignore cleanup errors
  }
}

/**
 * Create a simulation and return its ID. Automatically cleans up running sims first.
 */
export async function createSimulation(
  request: APIRequestContext,
  name: string,
  maxSteps: number = 10,
): Promise<string> {
  await cleanupRunningSimulations(request);
  const res = await request.post(`${API}/simulations/`, {
    data: {
      name,
      campaign: { name, channels: ['sns'], message: 'E2E test' },
      max_steps: maxSteps,
    },
  });
  const body = await res.json();
  return body.simulation_id;
}
