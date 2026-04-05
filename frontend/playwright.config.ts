/**
 * Playwright E2E configuration.
 * @spec docs/spec/09_HARNESS_SPEC.md
 */
import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 60000,
  retries: 1,
  workers: 1,  // Sequential execution to avoid API race conditions
  fullyParallel: false,
  use: {
    baseURL: 'http://localhost:5173',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'on-first-retry',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
  webServer: undefined, // Using Docker Compose, no need to start dev server
});
