/**
 * E2E: Modal interactions — Inject Event, Replay, Monte Carlo, Engine Control.
 * @spec docs/spec/07_FRONTEND_SPEC.md#control-panel
 */
import { test, expect } from '@playwright/test';
import { createSimulation } from './helpers';

test.describe('Phase B Modals', () => {
  let simId: string;

  test.beforeAll(async ({ request }) => {
    simId = await createSimulation(request, 'E2E Modal Test');
  });

  test.beforeEach(async ({ page }) => {
    await page.goto(`/simulations/${simId}`);
    await expect(page.getByTestId('simulation-page')).toBeVisible({ timeout: 10000 });
  });

  test('Inject Event modal opens and closes', async ({ page }) => {
    await page.getByTitle('Inject Event').click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Inject Event' })).toBeVisible();
    await expect(page.getByText('Event Type')).toBeVisible();
    await expect(page.getByText('Content')).toBeVisible();
    await expect(page.getByText('Controversy Level')).toBeVisible();

    // Close with Escape
    await page.keyboard.press('Escape');
    await expect(page.getByRole('dialog')).not.toBeVisible();
  });

  test('Inject Event modal has community target buttons', async ({ page }) => {
    await page.getByTitle('Inject Event').click();
    await expect(page.getByText('Target Communities')).toBeVisible();
    for (const c of ['A', 'B', 'C', 'D', 'E']) {
      await expect(page.getByRole('button', { name: c, exact: true })).toBeVisible();
    }
    await page.keyboard.press('Escape');
  });

  test('Replay modal opens with step slider', async ({ page }) => {
    await page.getByTitle('Replay').click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Replay from Step')).toBeVisible();
    await expect(page.getByText('Target Step')).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('Monte Carlo modal opens with config', async ({ page }) => {
    await page.getByTitle('Monte Carlo').click();
    await expect(page.getByRole('dialog')).toBeVisible();
    await expect(page.getByText('Monte Carlo Analysis')).toBeVisible();
    await expect(page.getByText('Number of Runs')).toBeVisible();
    await expect(page.getByText('Enable LLM')).toBeVisible();
    await page.keyboard.press('Escape');
  });

  test('Engine Control panel toggles', async ({ page }) => {
    await page.getByTitle('Engine Control').click();
    await expect(page.getByText('Engine Control')).toBeVisible();
    await expect(page.getByText('LLM (Quality)')).toBeVisible();
    await expect(page.getByText('Budget')).toBeVisible();

    // Click again to close
    await page.getByTitle('Engine Control').click();
  });

  test('Settings button navigates to settings page', async ({ page }) => {
    await page.getByTitle('Settings').click();
    await expect(page).toHaveURL(/\/settings/);
  });
});
