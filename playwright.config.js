import { defineConfig } from '@playwright/test';
export default defineConfig({
  testDir: './tests/browser',
  timeout: 30000,
  fullyParallel: true,
  use: { baseURL: 'http://127.0.0.1:5173', channel: process.env.ATLAS_BROWSER_CHANNEL || undefined, viewport: { width: 1440, height: 1000 } },
  webServer: { command: 'npm run dev -- --port 5173 --strictPort', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI },
  outputDir: process.env.ATLAS_TEST_OUTPUT || 'work/browser-tests',
});
