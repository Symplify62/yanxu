import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/live",
  testMatch: /(mobile-visual|list-layout|no-speech)\.spec\.ts/,
  workers: 1,
  timeout: 30000,
  reporter: [
    ["list"],
    [
      "json",
      {
        outputFile:
          "../.local-data/evidence/mobile-visual-system-20260923/web-tests.json",
      },
    ],
  ],
  use: {
    baseURL: "http://127.0.0.1:5198",
    channel: "chrome",
    headless: true,
    trace: "retain-on-failure",
  },
  outputDir: "../.local-data/evidence/mobile-visual-system-20260923/web-traces",
});
