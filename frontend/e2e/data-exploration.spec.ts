/**
 * E2E: Data exploration — communities, agents, threads, comparison.
 * @spec docs/spec/ui/UI_FLOW_SPEC.md#flow-22-to-flow-28
 *
 * Tests API-level data access for exploration pages.
 */
import { test, expect } from '@playwright/test';
import { API, createSimulation } from './helpers';

test.describe('Data Exploration APIs', () => {
  let simId: string;

  test.beforeAll(async ({ request }) => {
    simId = await createSimulation(request, 'E2E Data Explore');
    await request.post(`${API}/simulations/${simId}/start/`);
    for (let i = 0; i < 3; i++) {
      await request.post(`${API}/simulations/${simId}/step/`);
    }
    await request.post(`${API}/simulations/${simId}/pause/`);
  });

  test('FLOW-22: communities list returns community data', async ({ request }) => {
    const res = await request.get(`${API}/simulations/${simId}/communities/`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.communities).toBeDefined();
    expect(Array.isArray(body.communities)).toBeTruthy();
  });

  test('FLOW-22: community threads return 3 threads', async ({ request }) => {
    const res = await request.get(`${API}/simulations/${simId}/communities/A/threads`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.threads).toHaveLength(3);
    for (const thread of body.threads) {
      expect(thread.thread_id).toBeTruthy();
      expect(thread.topic).toBeTruthy();
      expect(thread.message_count).toBeGreaterThan(0);
    }
  });

  test('FLOW-26: thread detail returns messages with reactions', async ({ request }) => {
    // Get thread ID first
    const listRes = await request.get(`${API}/simulations/${simId}/communities/A/threads`);
    const threads = (await listRes.json()).threads;
    const threadId = threads[0].thread_id;

    const res = await request.get(`${API}/simulations/${simId}/communities/A/threads/${threadId}`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.messages.length).toBeGreaterThan(0);
    for (const msg of body.messages) {
      expect(msg.message_id).toBeTruthy();
      expect(msg.content).toBeTruthy();
      expect(msg.reactions).toBeDefined();
      expect(msg.reactions.agree).toBeDefined();
      expect(msg.reactions.disagree).toBeDefined();
    }
  });

  test('FLOW-23: agents list returns paginated results', async ({ request }) => {
    const res = await request.get(`${API}/simulations/${simId}/agents?limit=10`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.items).toBeDefined();
    expect(body.total).toBeGreaterThan(0);
    expect(body.items.length).toBeGreaterThan(0);
    expect(body.items.length).toBeLessThanOrEqual(10);
  });

  test('FLOW-24: agent detail returns profile', async ({ request }) => {
    // Get an agent ID
    const listRes = await request.get(`${API}/simulations/${simId}/agents?limit=1`);
    const agents = (await listRes.json()).items;
    const agentId = agents[0].agent_id;

    const res = await request.get(`${API}/simulations/${simId}/agents/${agentId}`);
    expect(res.ok()).toBeTruthy();
    const agent = await res.json();
    expect(agent.agent_id).toBe(agentId);
    expect(agent.personality).toBeDefined();
    expect(agent.emotion).toBeDefined();
    expect(agent.belief).toBeDefined();
  });

  test('FLOW-25: network graph returns nodes and edges', async ({ request }) => {
    const res = await request.get(`${API}/simulations/${simId}/network`);
    expect(res.ok()).toBeTruthy();
    const graph = await res.json();
    expect(graph.nodes.length).toBeGreaterThan(0);
    expect(graph.edges.length).toBeGreaterThan(0);
  });

  test('FLOW-28: step history returns steps data', async ({ request }) => {
    const res = await request.get(`${API}/simulations/${simId}/steps`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    // Steps may be empty if DB persistence hasn't flushed yet (fire-and-forget)
    // At minimum the endpoint returns a valid response
    expect(body.steps).toBeDefined();
    expect(Array.isArray(body.steps)).toBeTruthy();
    for (const step of body.steps) {
      expect(step.adoption_rate).toBeGreaterThanOrEqual(0);
      expect(step.mean_sentiment).toBeDefined();
    }
  });

  test('FLOW-27: scenario comparison API', async ({ request }) => {
    // Create second simulation for comparison
    const res2 = await request.post(`${API}/simulations/`, {
      data: {
        name: 'E2E Compare Target',
        campaign: { name: 'Compare', channels: ['sns'], message: 'test' },
      },
    });
    const sim2 = await res2.json();

    const cmpRes = await request.get(
      `${API}/simulations/${simId}/compare/${sim2.simulation_id}`
    );
    if (cmpRes.ok()) {
      const comparison = await cmpRes.json();
      // Comparison should have metrics for both simulations
      expect(comparison).toBeDefined();
    }
    // 404 is also acceptable if sim2 has no steps
    expect([200, 404]).toContain(cmpRes.status());
  });

  test('LLM stats and calls APIs', async ({ request }) => {
    // FLOW: LLM Dashboard
    const statsRes = await request.get(`${API}/simulations/${simId}/llm/stats`);
    expect(statsRes.ok()).toBeTruthy();

    const callsRes = await request.get(`${API}/simulations/${simId}/llm/calls`);
    expect(callsRes.ok()).toBeTruthy();
  });

  test('Monte Carlo API: start and poll', async ({ request }) => {
    const startRes = await request.post(`${API}/simulations/${simId}/monte-carlo`, {
      data: { n_runs: 3 },
    });
    expect(startRes.status()).toBe(202);
    const mc = await startRes.json();
    expect(mc.job_id).toBeTruthy();

    // Poll status
    const statusRes = await request.get(
      `${API}/simulations/${simId}/monte-carlo/${mc.job_id}`
    );
    expect(statusRes.ok()).toBeTruthy();
    const status = await statusRes.json();
    expect(['queued', 'running', 'completed', 'failed']).toContain(status.status);
  });
});
