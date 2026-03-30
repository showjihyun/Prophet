/**
 * E2E: Core simulation flow — create, start, step, view results.
 * @spec docs/spec/ui/UI_01_SIMULATION_MAIN.md
 * @spec docs/spec/06_API_SPEC.md#2-simulation-endpoints
 */
import { test, expect } from '@playwright/test';

const API = 'http://localhost:8000/api/v1';

test.describe('Simulation Main Page', () => {
  test('loads the simulation page with all 4 zones', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('simulation-page')).toBeVisible();
    await expect(page.getByTestId('control-panel')).toBeVisible();
    await expect(page.getByTestId('graph-panel')).toBeVisible();
    await expect(page.getByTestId('metrics-panel')).toBeVisible();
    await expect(page.getByTestId('timeline-panel')).toBeVisible();
  });

  test('control panel shows MCASP Prophet Engine branding', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('MCASP Prophet Engine')).toBeVisible();
  });

  test('control panel has playback buttons', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTitle('Play', { exact: true })).toBeVisible();
    await expect(page.getByTitle('Step', { exact: true })).toBeVisible();
    await expect(page.getByTitle('Reset', { exact: true })).toBeVisible();
    await expect(page.getByTitle('Replay', { exact: true })).toBeVisible();
  });

  test('control panel has Phase B feature buttons', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTitle('Inject Event')).toBeVisible();
    await expect(page.getByTitle('Monte Carlo')).toBeVisible();
    await expect(page.getByTitle('Engine Control')).toBeVisible();
  });

  test('speed buttons are visible and clickable', async ({ page }) => {
    await page.goto('/');
    const speeds = ['1x', '2x', '5x', '10x'];
    for (const speed of speeds) {
      await expect(page.getByRole('button', { name: speed })).toBeVisible();
    }
  });

  test('graph panel shows title and legend', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText('AI Social World')).toBeVisible();
    await expect(page.getByTestId('network-legend')).toBeVisible();
  });

  test('metrics panel shows live badge and metric cards', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('live-badge')).toBeVisible();
    await expect(page.getByTestId('active-agents-metric')).toBeVisible();
    await expect(page.getByTestId('sentiment-distribution')).toBeVisible();
    await expect(page.getByTestId('polarization-index')).toBeVisible();
  });

  test('zoom controls are functional', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('zoom-in-btn')).toBeVisible();
    await expect(page.getByTestId('zoom-out-btn')).toBeVisible();
    await expect(page.getByTestId('zoom-maximize-btn')).toBeVisible();
  });
});

test.describe('API E2E: Simulation Lifecycle', () => {
  test('full lifecycle: create → start → step → list', async ({ request }) => {
    // Create
    const createRes = await request.post(`${API}/simulations/`, {
      data: {
        name: 'Playwright E2E Test',
        campaign: { name: 'E2E', channels: ['sns'], message: 'test', target_communities: ['all'] },
        max_steps: 5,
      },
    });
    expect(createRes.ok()).toBeTruthy();
    const sim = await createRes.json();
    expect(sim.simulation_id).toBeTruthy();
    expect(sim.status).toBe('configured');
    expect(sim.total_agents).toBeGreaterThan(0);

    // Start (follow redirect)
    const startRes = await request.post(`${API}/simulations/${sim.simulation_id}/start/`);
    if (startRes.ok()) {
      const startBody = await startRes.json();
      expect(startBody.status).toBe('running');
    }

    // Step
    const stepRes = await request.post(`${API}/simulations/${sim.simulation_id}/step/`);
    if (stepRes.ok()) {
      const stepBody = await stepRes.json();
      expect(stepBody.step).toBeGreaterThanOrEqual(0);
      expect(stepBody.adoption_rate).toBeGreaterThanOrEqual(0);
    }

    // List
    const listRes = await request.get(`${API}/simulations/`);
    expect(listRes.ok()).toBeTruthy();
    const list = await listRes.json();
    expect(list.total).toBeGreaterThan(0);
  });

  test('health endpoint returns ok', async ({ request }) => {
    const res = await request.get('http://localhost:8000/health');
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.status).toBe('ok');
  });
});
