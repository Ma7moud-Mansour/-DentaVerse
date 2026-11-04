import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: process.env.CI ? 90000 : 75000,
  use: {
    baseURL: "http://127.0.0.1:5174",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        channel: "msedge",
        launchOptions: {
          args: ["--use-angle=swiftshader", "--enable-unsafe-swiftshader"],
        },
      },
    },
  ],
  webServer: [
    {
      command: "..\\.venv\\Scripts\\python.exe ..\\tools\\e2e_server.py",
      url: "http://127.0.0.1:8001/api/health",
      reuseExistingServer: false,
      env: {
        DENTAVERSE_DB: process.env.DENTAVERSE_TEST_DB || "../data/e2e.db",
        DENTAVERSE_TCP_PORT: "8767",
      },
    },
    {
      command: "npm run dev",
      url: "http://127.0.0.1:5174",
      reuseExistingServer: false,
      env: {
        DENTAVERSE_UI_PORT: "5174",
        DENTAVERSE_API_URL: "http://127.0.0.1:8001",
      },
    },
  ],
});
