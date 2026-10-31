import { tmpdir } from "node:os";
import { join } from "node:path";
import { defineConfig } from "@playwright/test";

// A fresh database for each run, shared with the workers through the environment.
process.env.E2E_DB ??= join(
  tmpdir(),
  `undercover-e2e-${String(Date.now())}.db`,
);

export default defineConfig({
  testDir: "e2e",
  outputDir: "e2e/test-results",
  reporter: "list",
  workers: 1,
  use: { baseURL: "http://localhost:5173" },
  webServer: [
    {
      command: "uv run -m uvicorn backend.main:app --port 8000",
      url: "http://127.0.0.1:8000/api/health",
      reuseExistingServer: false,
      env: { UNDERCOVER_DB: process.env.E2E_DB, UNDERCOVER_STUB_AGENT: "1" },
    },
    {
      command: "npx vite dashboard --port 5173 --strictPort",
      url: "http://localhost:5173",
      reuseExistingServer: true,
    },
  ],
});
