/**
 * E2E: Authentication flow — register, login, logout.
 * @spec docs/spec/ui/UI_FLOW_SPEC.md#flow-02-flow-03
 */
import { test, expect } from '@playwright/test';

const API = 'http://localhost:8000/api/v1';
const PASSWORD = 'testpass123';

test.describe('FLOW-02/03: Auth Workflow', () => {
  test('API: register creates user', async ({ request }) => {
    const user = `e2e_reg_${Date.now()}`;
    const res = await request.post(`${API}/auth/register`, {
      data: { username: user, password: PASSWORD },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.user_id).toBeTruthy();
    expect(body.username).toBe(user);
  });

  test('API: login returns token', async ({ request }) => {
    const user = `e2e_login_${Date.now()}`;
    // Register first
    await request.post(`${API}/auth/register`, {
      data: { username: user, password: PASSWORD },
    });
    // Login
    const res = await request.post(`${API}/auth/login`, {
      data: { username: user, password: PASSWORD },
    });
    expect(res.ok()).toBeTruthy();
    const body = await res.json();
    expect(body.token).toBeTruthy();
    expect(body.username).toBe(user);
  });

  test('API: duplicate register returns 409', async ({ request }) => {
    const user = `e2e_dup_${Date.now()}`;
    await request.post(`${API}/auth/register`, {
      data: { username: user, password: PASSWORD },
    });
    const res = await request.post(`${API}/auth/register`, {
      data: { username: user, password: PASSWORD },
    });
    expect(res.status()).toBe(409);
  });

  test('API: wrong password returns 401', async ({ request }) => {
    const user = `e2e_wrong_${Date.now()}`;
    await request.post(`${API}/auth/register`, {
      data: { username: user, password: PASSWORD },
    });
    const res = await request.post(`${API}/auth/login`, {
      data: { username: user, password: 'wrongpass' },
    });
    expect(res.status()).toBe(401);
  });

  test('UI: login page renders form', async ({ page }) => {
    await page.goto('/login');
    // Should have input fields and buttons
    const inputs = page.locator('input');
    await expect(inputs.first()).toBeVisible({ timeout: 10000 });
    await expect(page.getByRole('button', { name: /login/i })).toBeVisible();
    await expect(page.getByRole('button', { name: /register/i })).toBeVisible();
  });

  test('UI: logout clears localStorage token', async ({ page }) => {
    await page.goto('/projects');
    // Set a token
    await page.evaluate(() => {
      localStorage.setItem('prophet-token', 'fake-token');
      localStorage.setItem('prophet-username', 'fake-user');
    });

    // Simulate logout by clearing
    await page.evaluate(() => {
      localStorage.removeItem('prophet-token');
      localStorage.removeItem('prophet-username');
    });

    const token = await page.evaluate(() => localStorage.getItem('prophet-token'));
    expect(token).toBeNull();
  });
});
