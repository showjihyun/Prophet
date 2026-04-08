/**
 * E2E: HelpTooltip shared component — ensure contextual help icons
 * appear next to technical terms across the app and expand on hover
 * without UI jitter.
 *
 * The HelpTooltip was introduced to explain simulation jargon (adoption
 * rate, polarization index, cascade depth, etc.) at point of use. These
 * tests protect the anti-flicker design and the glossary integration.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#coding-conventions-no-hardcoded-domain-literals
 */
import { test, expect } from '@playwright/test';
import { API, createSimulation } from './helpers';

test.describe('HelpTooltip — shared contextual help', () => {
  test('metrics panel has help icons for technical terms', async ({ page, request }) => {
    const simId = await createSimulation(request, 'E2E Tooltip Sim', 5);
    await page.goto(`/simulations/${simId}`);
    await expect(page.getByTestId('simulation-page')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('metrics-panel')).toBeVisible();

    // Every HelpTooltip renders a hidden <span role="tooltip"> by design
    // (opacity-toggled for anti-flicker). At least 4 should exist in the
    // metrics panel: activeAgents, sentimentDistribution, polarization,
    // cascadeDepth, cascadeWidth, influencer.
    const tooltips = page.getByRole('tooltip', { includeHidden: true });
    const count = await tooltips.count();
    expect(count).toBeGreaterThanOrEqual(4);
  });

  test('help icon opens tooltip on hover without layout jitter', async ({ page, request }) => {
    const simId = await createSimulation(request, 'E2E Tooltip Hover', 5);
    await page.goto(`/simulations/${simId}`);
    await expect(page.getByTestId('simulation-page')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('metrics-panel')).toBeVisible();

    // Find the first help button (aria-label pattern: "What does X mean?")
    const helpButton = page.getByRole('button', { name: /What does .* mean\?/i }).first();
    await expect(helpButton).toBeVisible();

    // Capture the panel's layout before hover
    const panelBox = await page.getByTestId('metrics-panel').boundingBox();
    expect(panelBox).not.toBeNull();

    // Hover the help button — tooltip should appear
    await helpButton.hover();

    // The tooltip's opacity should now be > 0 (visible)
    // We can't directly measure opacity via locator, but we can verify
    // the tooltip has the aria-hidden="false" attribute.
    // Since the tooltip is always in the DOM, query it and check state.
    const tooltipAfterHover = page
      .getByRole('tooltip', { includeHidden: true })
      .filter({ hasNot: page.locator('[aria-hidden="true"]') })
      .first();
    // At least one tooltip should be visible (aria-hidden=false)
    const visibleCount = await page
      .locator('[role="tooltip"][aria-hidden="false"]')
      .count();
    expect(visibleCount).toBeGreaterThanOrEqual(1);

    // Critical anti-flicker assertion: panel position must not have shifted
    const panelBoxAfter = await page.getByTestId('metrics-panel').boundingBox();
    expect(panelBoxAfter).not.toBeNull();
    expect(panelBoxAfter!.x).toBe(panelBox!.x);
    expect(panelBoxAfter!.y).toBe(panelBox!.y);
    expect(panelBoxAfter!.width).toBe(panelBox!.width);

    // Silence unused reference
    void tooltipAfterHover;
  });

  test('help icon has accessible label matching its term', async ({ page, request }) => {
    const simId = await createSimulation(request, 'E2E Tooltip A11y', 5);
    await page.goto(`/simulations/${simId}`);
    await expect(page.getByTestId('simulation-page')).toBeVisible({ timeout: 10000 });
    await expect(page.getByTestId('metrics-panel')).toBeVisible();

    // All help buttons should have aria-labels in the form "What does X mean?"
    const helpButtons = page.getByRole('button', { name: /What does .* mean\?/i });
    const count = await helpButtons.count();
    expect(count).toBeGreaterThanOrEqual(4);

    // Each aria-label should contain a meaningful term, not "undefined" or ""
    for (let i = 0; i < Math.min(count, 6); i++) {
      const label = await helpButtons.nth(i).getAttribute('aria-label');
      expect(label).toMatch(/What does .+ mean\?/);
      expect(label).not.toMatch(/undefined|null/);
    }

    await request.post(`${API}/simulations/${simId}/stop/`).catch(() => undefined);
  });
});
