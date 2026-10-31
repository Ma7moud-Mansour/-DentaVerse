import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  timeout: 30000,
  use: { baseURL: 'http://127.0.0.1:5173', trace: 'retain-on-failure', screenshot: 'only-on-failure' },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'], channel: 'msedge', launchOptions: { args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] } } }],
  webServer: [
    { command: '..\\.venv\\Scripts\\python.exe -m uvicorn backend.app:app --app-dir .. --host 127.0.0.1 --port 8000', url: 'http://127.0.0.1:8000/api/health', reuseExistingServer: !process.env.CI,
      env: { DENTAVERSE_DB: process.env.DENTAVERSE_TEST_DB || '../data/e2e.db' } },
    { command: 'npm run dev', url: 'http://127.0.0.1:5173', reuseExistingServer: !process.env.CI },
  ],
});
