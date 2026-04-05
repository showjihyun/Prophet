/**
 * E2E: Simulation execution control — Play, Step, Pause, Reset, Run All.
 * @spec docs/spec/ui/UI_FLOW_SPEC.md#flow-13-flow-14
 *
 * Tests actual simulation state transitions via API + UI verification.
 */
import { test, expect } from '@playwright/test';
import { API, createSimulation, cleanupRunningSimulations } from './helpers';

test.describe('FLOW-13: Simulation Step-by-Step Control', () => {
  test('API: full control sequence — start → step → pause → resume → stop', async ({ request }) => {
    const simId = await createSimulation(request, 'E2E Control Sequence', 20);

    // Start
    const startRes = await request.post(`${API}/simulations/${simId}/start/`);
    expect(startRes.ok()).toBeTruthy();
    expect((await startRes.json()).status).toBe('running');

    // Step
    const stepRes = await request.post(`${API}/simulations/${simId}/step/`);
    expect(stepRes.ok()).toBeTruthy();
    const step = await stepRes.json();
    expect(step.step).toBeGreaterThanOrEqual(0);
    expect(step.adoption_rate).toBeGreaterThanOrEqual(0);
    expect(step.mean_sentiment).toBeDefined();
    expect(step.action_distribution).toBeDefined();
    expect(step.community_metrics).toBeDefined();

    // Pause
    const pauseRes = await request.post(`${API}/simulations/${simId}/pause/`);
    expect(pauseRes.ok()).toBeTruthy();
    expect((await pauseRes.json()).status).toBe('paused');

    // Resume (start from paused)
    const resumeRes = await request.post(`${API}/simulations/${simId}/start/`);
    expect(resumeRes.ok()).toBeTruthy();
    expect((await resumeRes.json()).status).toBe('running');

    // Stop (reset)
    const stopRes = await request.post(`${API}/simulations/${simId}/stop/`);
    expect(stopRes.ok()).toBeTruthy();
    const stopBody = await stopRes.json();
    // Stop can result in 'created' (reset) or 'completed' (if all steps ran)
    expect(['created', 'completed']).toContain(stopBody.status);
  });

  test('UI: simulation page shows correct state after steps', async ({ page, request }) => {
    const simId = await createSimulation(request, 'E2E UI Control', 20);

    // Start and step via API
    await request.post(`${API}/simulations/${simId}/start/`);
    await request.post(`${API}/simulations/${simId}/step/`);

    // Load in UI
    await page.goto(`/simulations/${simId}`);
    await expect(page.getByTestId('simulation-page')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('timeline-panel')).toBeVisible();
    await expect(page.getByTestId('metrics-panel')).toBeVisible();
  });
});

test.describe('FLOW-14: Run All → Completion', () => {
  test('API: run-all completes simulation and returns report', async ({ request }) => {
    await cleanupRunningSimulations(request);
    const simId = await createSimulation(request, 'E2E Run All', 5);

    const runRes = await request.post(`${API}/simulations/${simId}/run-all`);
    expect(runRes.ok()).toBeTruthy();
    const report = await runRes.json();
    expect(report.total_steps).toBeGreaterThan(0);
    expect(report.final_adoption_rate).toBeGreaterThanOrEqual(0);
    expect(report.final_mean_sentiment).toBeDefined();
    expect(report.status).toBe('completed');
  });
});
