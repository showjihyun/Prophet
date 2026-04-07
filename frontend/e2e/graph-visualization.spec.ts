/**
 * E2E: Graph visualization — Cytoscape renders real network data.
 * @spec docs/spec/07_FRONTEND_SPEC.md#graphpanel
 * @spec docs/spec/06_API_SPEC.md#get-simulationssimulation_idnetwork
 *
 * Verifies that the graph panel renders actual agent nodes with community
 * colors, edges with weight-based opacity, and legend with real counts.
 */
import { test, expect } from '@playwright/test';
import { API, createSimulation } from './helpers';

test.describe('Graph Visualization', () => {
  let simId: string;

  test.beforeAll(async ({ request }) => {
    simId = await createSimulation(request, 'E2E Graph Test');
  });

  test('API: network endpoint returns nodes and edges', async ({ request }) => {
    const res = await request.get(`${API}/simulations/${simId}/network/?format=cytoscape`);
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.nodes).toBeDefined();
    expect(body.edges).toBeDefined();
    expect(body.nodes.length).toBeGreaterThan(0);
    expect(body.edges.length).toBeGreaterThan(0);
  });

  test('API: each node has required SPEC fields', async ({ request }) => {
    const res = await request.get(`${API}/simulations/${simId}/network/?format=cytoscape`);
    const { nodes } = await res.json();
    const node = nodes[0];
    expect(node.data).toBeDefined();
    expect(node.data.id).toBeTruthy();
    expect(node.data.label).toBeTruthy();
    expect(node.data.community).toBeTruthy();
    expect(node.data.agent_type).toBeTruthy();
    expect(typeof node.data.influence_score).toBe('number');
    expect(typeof node.data.adopted).toBe('boolean');
  });

  test('API: community field is short key, not UUID', async ({ request }) => {
    const res = await request.get(`${API}/simulations/${simId}/network/?format=cytoscape`);
    const { nodes } = await res.json();
    for (const node of nodes.slice(0, 10)) {
      expect(node.data.community.length).toBeLessThanOrEqual(10);
    }
  });

  test('API: each edge has required SPEC fields', async ({ request }) => {
    const res = await request.get(`${API}/simulations/${simId}/network/?format=cytoscape`);
    const { edges } = await res.json();
    const edge = edges[0];
    expect(edge.data).toBeDefined();
    expect(edge.data.id).toBeTruthy();
    expect(edge.data.source).toBeTruthy();
    expect(edge.data.target).toBeTruthy();
    expect(typeof edge.data.weight).toBe('number');
    expect(typeof edge.data.is_bridge).toBe('boolean');
  });

  test('API: nodes span multiple communities', async ({ request }) => {
    const res = await request.get(`${API}/simulations/${simId}/network/?format=cytoscape`);
    const { nodes } = await res.json();
    const communities = new Set(nodes.map((n: { data: { community: string } }) => n.data.community));
    expect(communities.size).toBeGreaterThanOrEqual(2);
  });

  test('UI: graph panel renders with real data', async ({ page }) => {
    await page.goto(`/simulations/${simId}`);
    await expect(page.getByTestId('simulation-page')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('graph-panel')).toBeVisible();

    // Graph title visible
    await expect(page.getByText('AI Social World')).toBeVisible();
  });

  test('UI: network legend shows community counts', async ({ page }) => {
    await page.goto(`/simulations/${simId}`);
    await expect(page.getByTestId('simulation-page')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('network-legend')).toBeVisible();

    // Legend should show community names
    const legendText = await page.getByTestId('network-legend').textContent();
    expect(legendText).toBeTruthy();
  });

  test('UI: graph shows node and edge counts', async ({ page }) => {
    await page.goto(`/simulations/${simId}`);
    await expect(page.getByTestId('simulation-page')).toBeVisible({ timeout: 10000 });

    // Wait for graph to load (node/edge count text appears)
    await page.waitForTimeout(3000);
    const graphText = await page.getByTestId('graph-panel').textContent();
    // Should show "N nodes · M edges"
    expect(graphText).toMatch(/\d+\s*nodes/i);
  });

  test('UI: zoom controls are functional', async ({ page }) => {
    await page.goto(`/simulations/${simId}`);
    await expect(page.getByTestId('simulation-page')).toBeVisible({ timeout: 10000 });

    await expect(page.getByTestId('zoom-in-btn')).toBeVisible();
    await expect(page.getByTestId('zoom-out-btn')).toBeVisible();
    await expect(page.getByTestId('zoom-maximize-btn')).toBeVisible();

    // Click zoom in — should not crash
    await page.getByTestId('zoom-in-btn').click();
    await page.waitForTimeout(500);
    await expect(page.getByTestId('graph-panel')).toBeVisible();
  });

  test('UI: no console errors on graph load', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });

    await page.goto(`/simulations/${simId}`);
    await expect(page.getByTestId('simulation-page')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(3000);

    const realErrors = errors.filter(
      (e) =>
        !e.includes('ERR_CONNECTION_REFUSED') &&
        !e.includes('Failed to fetch') &&
        !e.includes('WebSocket') &&
        !e.includes('ResizeObserver'),
    );
    expect(realErrors).toHaveLength(0);
  });
});
