import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/account",
  timeout: 45000,
  expect: { timeout: 10000 },
  workers: 1,
  reporter: [["list"]],
  outputDir: "../.local-data/evidence/identity-voice/web-test-results",
  use: {
    baseURL: process.env.YANXU_ACCOUNT_TEST_URL || "http://127.0.0.1:5197",
    channel: "chrome",
    headless: true,
    viewport: { width: 1280, height: 900 },
    trace: "off",
    screenshot: "only-on-failure",
    reducedMotion: "reduce",
  },
});
