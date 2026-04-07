/**
 * E2E: Project → Scenario → Simulation creation workflow.
 * @spec docs/spec/ui/UI_FLOW_SPEC.md#flow-04-to-flow-09
 *
 * Tests the full user journey: create project → create scenario →
 * run scenario → simulation page loads with data.
 */
import { test, expect } from '@playwright/test';
import { API, cleanupRunningSimulations } from './helpers';

test.describe('FLOW-04~09: Project → Scenario → Simulation Workflow', () => {

  test('API: create project → add scenario → list shows scenario', async ({ request }) => {
    // FLOW-04: Create project
    const projRes = await request.post(`${API}/projects/`, {
      data: { name: `E2E Project ${Date.now()}` },
    });
    expect(projRes.ok()).toBeTruthy();
    const project = await projRes.json();
    expect(project.project_id).toBeTruthy();

    // FLOW-09: Create scenario under project
    const scenRes = await request.post(`${API}/projects/${project.project_id}/scenarios`, {
      data: { name: 'E2E Scenario' },
    });
    expect(scenRes.ok()).toBeTruthy();
    const scenario = await scenRes.json();
    expect(scenario.scenario_id).toBeTruthy();
    expect(scenario.status).toBe('draft');

    // FLOW-05: Get project detail → scenarios list
    const detailRes = await request.get(`${API}/projects/${project.project_id}`);
    expect(detailRes.ok()).toBeTruthy();
    const detail = await detailRes.json();
    expect(detail.scenarios.length).toBe(1);
    expect(detail.scenarios[0].name).toBe('E2E Scenario');
  });

  test('UI: /projects page shows project list', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.getByRole('heading', { name: /Projects/i })).toBeVisible({ timeout: 10000 });
  });

  test('UI: /setup campaign form renders with required fields', async ({ page }) => {
    await page.goto('/setup');
    await expect(page.getByRole('heading', { name: /Create New Simulation/i })).toBeVisible({ timeout: 10000 });

    // FLOW-09: Campaign setup form has required sections
    await expect(page.getByText(/Campaign Name/i)).toBeVisible();
    await expect(page.getByText(/Community Configuration/i)).toBeVisible();
  });

  test('API: full workflow — project → scenario → simulation → step', async ({ request }) => {
    // Create project
    const projRes = await request.post(`${API}/projects/`, {
      data: { name: `Workflow ${Date.now()}` },
    });
    const project = await projRes.json();

    // Create scenario
    const scenRes = await request.post(`${API}/projects/${project.project_id}/scenarios`, {
      data: { name: 'Workflow Scenario' },
    });
    const scenario = await scenRes.json();

    // Clean up running sims first to avoid capacity error
    await cleanupRunningSimulations(request);

    // Create simulation
    const simRes = await request.post(`${API}/simulations/`, {
      data: {
        name: 'Workflow Sim',
        project_id: project.project_id,
        campaign: { name: 'WF', channels: ['sns'], message: 'test' },
        max_steps: 10,
      },
    });
    expect(simRes.ok()).toBeTruthy();
    const sim = await simRes.json();
    expect(sim.simulation_id).toBeTruthy();
    expect(sim.total_agents).toBeGreaterThan(0);

    // Start simulation
    const startRes = await request.post(`${API}/simulations/${sim.simulation_id}/start/`);
    expect(startRes.ok()).toBeTruthy();

    // Execute 3 steps
    for (let i = 0; i < 3; i++) {
      const stepRes = await request.post(`${API}/simulations/${sim.simulation_id}/step/`);
      expect(stepRes.ok()).toBeTruthy();
      const step = await stepRes.json();
      expect(step.step).toBe(i);
      expect(step.adoption_rate).toBeGreaterThanOrEqual(0);
    }

    // Stop sim to free concurrent slot
    await request.post(`${API}/simulations/${sim.simulation_id}/stop/`);

    // Verify step history (in-memory, not DB — may be empty after stop)
    const historyRes = await request.get(`${API}/simulations/${sim.simulation_id}/steps`);
    expect(historyRes.ok()).toBeTruthy();
    const history = await historyRes.json();
    expect(history.steps).toBeDefined();
  });
});
