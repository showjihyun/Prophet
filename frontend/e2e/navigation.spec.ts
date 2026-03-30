/**
 * E2E: Page navigation — all routes render without errors.
 * @spec docs/spec/07_FRONTEND_SPEC.md
 */
import { test, expect } from '@playwright/test';

test.describe('Page Navigation', () => {
  test('home page (/) renders SimulationPage', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByTestId('simulation-page')).toBeVisible();
  });

  test('/communities renders CommunitiesDetailPage', async ({ page }) => {
    await page.goto('/communities');
    await expect(page.getByTestId('communities-detail-page')).toBeVisible();
  });

  test('/influencers renders TopInfluencersPage', async ({ page }) => {
    await page.goto('/influencers');
    await expect(page.getByTestId('top-influencers-page')).toBeVisible();
  });

  test('/metrics renders GlobalMetricsPage', async ({ page }) => {
    await page.goto('/metrics');
    await expect(page.getByTestId('global-metrics-page')).toBeVisible();
  });

  test('/settings renders SettingsPage', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  });

  test('/setup renders CampaignSetupPage', async ({ page }) => {
    await page.goto('/setup');
    await expect(page.getByRole('heading', { name: /Create New Simulation/i })).toBeVisible();
  });

  test('/projects renders ProjectsListPage', async ({ page }) => {
    await page.goto('/projects');
    await expect(page.getByRole('heading', { name: /Projects/i })).toBeVisible();
  });

  test('/opinions renders ScenarioOpinionsPage', async ({ page }) => {
    await page.goto('/opinions');
    await expect(page.getByRole('heading', { name: /Scenario/i })).toBeVisible();
  });

  test('Global Insights button navigates to /metrics', async ({ page }) => {
    await page.goto('/');
    await page.getByRole('button', { name: 'Global Insights' }).click();
    await expect(page).toHaveURL(/\/metrics/);
  });

  test('no console errors on main page', async ({ page }) => {
    const errors: string[] = [];
    page.on('console', (msg) => {
      if (msg.type() === 'error') errors.push(msg.text());
    });
    await page.goto('/');
    await page.waitForTimeout(2000);
    // Filter out known non-critical errors (network failures when backend is unreachable from browser)
    const realErrors = errors.filter(
      (e) => !e.includes('ERR_CONNECTION_REFUSED') && !e.includes('Failed to fetch'),
    );
    expect(realErrors).toHaveLength(0);
  });
});
