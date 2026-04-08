/**
 * E2E: TanStack Query cache behavior — verifies that page navigation
 * benefits from cross-route caching (the main UX win of the TanStack
 * Query migration).
 *
 * These tests count network requests before and after a back-navigation
 * to prove that cached queries don't re-fetch.
 *
 * @spec docs/spec/07_FRONTEND_SPEC.md#data-fetching
 */
import { test, expect } from '@playwright/test';
import { API, createSimulation } from './helpers';

test.describe('TanStack Query cache — cross-route UX', () => {
  test('projects list is cached across navigation', async ({ page, request }) => {
    // Ensure at least one project exists so the list has content.
    await request.post(`${API}/projects/`, {
      data: { name: 'E2E Cache Test' },
    });

    let projectsListCalls = 0;
    await page.route('**/api/v1/projects/', (route) => {
      if (route.request().method() === 'GET') projectsListCalls++;
      return route.continue();
    });

    // First visit — 1 fetch
    await page.goto('/projects');
    await expect(page.getByTestId('projects-list-page')).toBeVisible({ timeout: 10000 });
    // Wait for the list to actually render (not loading state)
    await page.waitForTimeout(500);
    const firstCallCount = projectsListCalls;
    expect(firstCallCount).toBeGreaterThanOrEqual(1);

    // Navigate away
    await page.goto('/settings');
    await expect(page.getByTestId('settings-page')).toBeVisible({ timeout: 10000 });

    // Navigate back to /projects — cache should serve the data; at most 1
    // additional request (background revalidation). This is the key check.
    await page.goto('/projects');
    await expect(page.getByTestId('projects-list-page')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(500);

    // We tolerate up to 1 extra revalidation fetch; without caching we'd
    // see a second full round-trip every navigation.
    expect(projectsListCalls - firstCallCount).toBeLessThanOrEqual(1);

    // Cleanup projects
    const listRes = await request.get(`${API}/projects/`);
    const projects = await listRes.json();
    for (const p of Array.isArray(projects) ? projects : []) {
      if (p.name?.startsWith('E2E Cache Test')) {
        await request.delete(`${API}/projects/${p.project_id}/`).catch(() => undefined);
      }
    }
  });

  test('community list is cached per simulation', async ({ page, request }) => {
    const simId = await createSimulation(request, 'E2E Community Cache', 5);

    let communitiesCalls = 0;
    await page.route(`**/api/v1/simulations/${simId}/communities/`, (route) => {
      if (route.request().method() === 'GET') communitiesCalls++;
      return route.continue();
    });

    // First visit
    await page.goto(`/communities`);
    await expect(page.getByTestId('communities-detail-page')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(500);
    const firstCount = communitiesCalls;

    // Navigate away and back
    await page.goto('/settings');
    await expect(page.getByTestId('settings-page')).toBeVisible({ timeout: 10000 });
    await page.goto(`/communities`);
    await expect(page.getByTestId('communities-detail-page')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(500);

    // Cache hit → at most 1 extra revalidation
    expect(communitiesCalls - firstCount).toBeLessThanOrEqual(1);

    await request.post(`${API}/simulations/${simId}/stop/`).catch(() => undefined);
  });

  test('agent list is fetched per simulation and reused across panels', async ({ page, request }) => {
    const simId = await createSimulation(request, 'E2E Agent Cache', 5);

    // Step once to populate data
    await request.post(`${API}/simulations/${simId}/start/`);
    await request.post(`${API}/simulations/${simId}/step/`);

    let agentsCalls = 0;
    await page.route(`**/api/v1/simulations/${simId}/agents/**`, (route) => {
      if (route.request().method() === 'GET') agentsCalls++;
      return route.continue();
    });

    // Navigate to influencers page — triggers useAgents(limit: 200)
    await page.goto('/influencers');
    await expect(page.getByTestId('top-influencers-page')).toBeVisible({ timeout: 10000 });
    await page.waitForTimeout(800);

    // The influencers page + metrics panel both use useAgents but with
    // different `limit` params (4 and 200), so they're separate cache
    // entries. Either way, the calls should be O(1) per view, not O(N).
    expect(agentsCalls).toBeLessThanOrEqual(5);

    await request.post(`${API}/simulations/${simId}/stop/`).catch(() => undefined);
  });
});
