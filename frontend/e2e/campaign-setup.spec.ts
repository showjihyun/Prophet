/**
 * E2E: Campaign Setup form end-to-end flow.
 * @spec docs/spec/ui/UI_16_CAMPAIGN_SETUP.md
 *
 * Covers the full campaign creation path after the CampaignSetupPage
 * refactor (page split into hook + 6 section components). These tests
 * exercise the form as a user would and verify that the refactor
 * preserves behavior end-to-end, not just in unit tests.
 */
import { test, expect } from '@playwright/test';
import { API, cleanupRunningSimulations } from './helpers';

test.describe('Campaign Setup form — full flow', () => {
  test.beforeEach(async ({ request }) => {
    await cleanupRunningSimulations(request);
  });

  test('renders all 6 form sections', async ({ page }) => {
    await page.goto('/setup');
    await expect(page.getByTestId('campaign-setup-page')).toBeVisible({ timeout: 10000 });

    // Section 1: Project Selector
    await expect(page.locator('#campaign-project')).toBeVisible();
    // Section 2: Campaign Info
    await expect(page.locator('#campaign-name')).toBeVisible();
    await expect(page.locator('#campaign-budget')).toBeVisible();
    await expect(page.locator('#campaign-message')).toBeVisible();
    // Section 3: Target Communities (fallback options visible before load)
    await expect(page.getByText('Target Communities')).toBeVisible();
    // Section 4: Campaign Attributes
    await expect(page.locator('#attr-controversy')).toBeVisible();
    await expect(page.locator('#attr-novelty')).toBeVisible();
    await expect(page.locator('#attr-utility')).toBeVisible();
    // Section 5: Community Configuration (collapsible)
    await expect(page.getByText(/Community Configuration/)).toBeVisible();
    // Section 6: Advanced Settings (collapsible)
    await expect(page.getByText('Advanced Settings')).toBeVisible();
  });

  test('submit button is disabled without a name', async ({ page }) => {
    await page.goto('/setup');
    await expect(page.getByTestId('campaign-setup-page')).toBeVisible();
    const submit = page.getByRole('button', { name: /Create Simulation/i });
    await expect(submit).toBeDisabled();
  });

  test('channel checkboxes toggle independently', async ({ page }) => {
    await page.goto('/setup');
    await expect(page.getByTestId('campaign-setup-page')).toBeVisible();

    const sns = page.getByRole('checkbox', { name: 'SNS' });
    const tv = page.getByRole('checkbox', { name: 'TV' });

    await expect(sns).not.toBeChecked();
    await sns.check();
    await expect(sns).toBeChecked();
    await expect(tv).not.toBeChecked();

    await tv.check();
    await expect(tv).toBeChecked();
    await expect(sns).toBeChecked();

    await sns.uncheck();
    await expect(sns).not.toBeChecked();
    await expect(tv).toBeChecked();
  });

  test('advanced settings is collapsed by default and expands on click', async ({ page }) => {
    await page.goto('/setup');
    await expect(page.getByTestId('campaign-setup-page')).toBeVisible();

    // Max Steps input should not be visible when collapsed
    const maxSteps = page.locator('#adv-max-steps');
    await expect(maxSteps).not.toBeVisible();

    // Click the Advanced Settings summary
    await page.getByText('Advanced Settings').click();
    await expect(maxSteps).toBeVisible();
  });

  test('attribute sliders update their displayed value', async ({ page }) => {
    await page.goto('/setup');
    await expect(page.getByTestId('campaign-setup-page')).toBeVisible();

    // Controversy starts at 0.1
    const controversyValue = page.locator('#attr-controversy');
    await expect(controversyValue).toHaveValue('0.1');

    // Change via keyboard for reliability (range inputs are finicky)
    await controversyValue.focus();
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('ArrowRight');
    await expect(controversyValue).toHaveValue(/0\.[234]/);
  });

  test('project selector is disabled/read-only when projectId is in URL', async ({ page, request }) => {
    // Create a project first
    const projRes = await request.post(`${API}/projects/`, {
      data: { name: 'E2E Test Project' },
    });
    const project = await projRes.json();

    await page.goto(`/projects/${project.project_id}/new-scenario`);
    await expect(page.getByTestId('campaign-setup-page')).toBeVisible({ timeout: 10000 });

    const projectInput = page.locator('#campaign-project');
    await expect(projectInput).toBeVisible();
    // Should be a read-only <input>, not a <select>
    const tagName = await projectInput.evaluate((el) => el.tagName.toLowerCase());
    expect(tagName).toBe('input');
    await expect(projectInput).toHaveAttribute('readonly', '');

    // Cleanup
    await request.delete(`${API}/projects/${project.project_id}/`);
  });
});
