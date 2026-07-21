import { defineConfig } from "@playwright/test";

const python = process.env.PYTHON_EXECUTABLE || "python";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: false,
  workers: 1,
  reporter: "line",
  use: {
    baseURL: "http://127.0.0.1:8032",
    browserName: "chromium",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: {
    command: `${python} -m uvicorn app.main:app --host 127.0.0.1 --port 8032`,
    url: "http://127.0.0.1:8032/api/health",
    env: {
      ...process.env,
      CONFIGURATOR_DB: `/tmp/configurator-e2e-${process.pid}.db`,
      SEED_DEMO_DATA: "true",
      PYTHONPATH: ".",
    },
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
