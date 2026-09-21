import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/live",
  timeout: 30000,
  workers: 1,
  reporter: [
    ["list"],
    ["json", { outputFile: "../.local-data/evidence/web/results.json" }],
  ],
  use: {
    baseURL: "http://127.0.0.1:5189",
    channel: "chrome",
    headless: true,
    viewport: { width: 1280, height: 900 },
    trace: "retain-on-failure",
  },
  outputDir: "../.local-data/evidence/web/test-results",
});
