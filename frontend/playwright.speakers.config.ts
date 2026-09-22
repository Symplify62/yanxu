import { defineConfig } from "@playwright/test";
import base from "./playwright.config";

export default defineConfig(base, {
  testDir: "tests/speaker-prototype",
  reporter: [["list"]],
  outputDir: "../.local-data/evidence/speaker-redesign/test-results",
  use: {
    ...base.use,
    baseURL: "http://127.0.0.1:5180",
    reducedMotion: "reduce",
  },
  webServer: {
    command: "npm run dev:speakers",
    url: "http://127.0.0.1:5180/speaker-prototype.html",
    reuseExistingServer: true,
    timeout: 30000,
  },
});
