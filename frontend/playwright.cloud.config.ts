import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "tests/cloud",
  timeout: 60000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:5190",
    channel: "chrome",
    headless: true,
    trace: "retain-on-failure",
  },
  outputDir: "../.local-data/evidence/cloud-browser/results",
  webServer: {
    command:
      'cd ../backend && YANXU_STORAGE=qiniu QINIU_DELIVERY_ENABLED=true YANXU_DATA_DIR="$PWD/../.local-data/cloud-smoke" uv run uvicorn yanxu.api:create_app --factory --host 127.0.0.1 --port 5190',
    url: "http://127.0.0.1:5190/api/health",
    reuseExistingServer: false,
  },
});
