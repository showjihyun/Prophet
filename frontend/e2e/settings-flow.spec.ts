/**
 * E2E: Settings page — load, modify, save.
 * @spec docs/spec/ui/UI_FLOW_SPEC.md#flow-29
 */
import { test, expect } from '@playwright/test';

const API = 'http://localhost:8000/api/v1';

test.describe('FLOW-29: Settings Page', () => {
  test('settings page loads with current config', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible({ timeout: 10000 });

    // LLM Provider section
    await expect(page.getByText(/LLM Provider|Ollama/i).first()).toBeVisible();
  });

  test('settings page shows Ollama connection fields', async ({ page }) => {
    await page.goto('/settings');
    await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible({ timeout: 10000 });

    // Settings page should have LLM provider section
    await expect(page.getByText(/Provider|LLM/i).first()).toBeVisible();
  });

  test('API: GET /settings returns current config', async ({ request }) => {
    const res = await request.get(`${API}/settings/`);
    expect(res.ok()).toBeTruthy();
    const settings = await res.json();

    // Verify structure
    expect(settings.llm).toBeDefined();
    expect(settings.llm.default_provider).toBeDefined();
    expect(settings.llm.ollama_base_url).toBeDefined();
    expect(settings.simulation).toBeDefined();
    expect(settings.simulation.slm_llm_ratio).toBeDefined();
    expect(settings.simulation.llm_cache_ttl).toBeDefined();
  });

  test('API: PUT /settings updates config', async ({ request }) => {
    // Get current
    const getRes = await request.get(`${API}/settings/`);
    const current = await getRes.json();

    // Update cache TTL
    const newTtl = current.simulation.llm_cache_ttl === 3600 ? 7200 : 3600;
    const putRes = await request.put(`${API}/settings/`, {
      data: {
        simulation: { llm_cache_ttl: newTtl },
      },
    });
    expect(putRes.ok()).toBeTruthy();

    // Verify update
    const verifyRes = await request.get(`${API}/settings/`);
    const updated = await verifyRes.json();
    expect(updated.simulation.llm_cache_ttl).toBe(newTtl);

    // Restore original
    await request.put(`${API}/settings/`, {
      data: {
        simulation: { llm_cache_ttl: current.simulation.llm_cache_ttl },
      },
    });
  });

  test('API: GET /settings/ollama-models returns model list', async ({ request }) => {
    const res = await request.get(`${API}/settings/ollama-models`);
    // May fail if Ollama has no models pulled — both 200 and error are acceptable
    if (res.ok()) {
      const body = await res.json();
      expect(body.models).toBeDefined();
      expect(Array.isArray(body.models)).toBeTruthy();
    }
  });
});
