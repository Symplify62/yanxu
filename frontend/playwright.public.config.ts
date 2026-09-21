import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/live",
  timeout: 60000,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "../.local-data/evidence/public/results.json" }]],
  use: {
    baseURL: "https://yanxu.qjl666.xyz",
    channel: "chrome",
    headless: true,
    viewport: { width: 1280, height: 900 },
    trace: "retain-on-failure",
  },
  outputDir: "../.local-data/evidence/public/test-results",
});
