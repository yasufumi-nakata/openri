import { defineConfig, devices } from "@playwright/test";
import { existsSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const localPython = [".venv/bin/python", ".venv-claude/bin/python"]
  .map((candidate) => resolve(repoRoot, candidate))
  .find((candidate) => existsSync(candidate));
const openriPython = process.env.OPENRI_PYTHON ?? localPython ?? "python3";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30000,
  use: {
    baseURL: "http://127.0.0.1:5173",
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: `PYTHONPATH=backend ${openriPython} -m uvicorn openri.api:app --host 127.0.0.1 --port 8008`,
      url: "http://127.0.0.1:8008/api/health",
      cwd: "..",
      reuseExistingServer: false,
    },
    {
      command: "npm run dev -- --host 127.0.0.1 --port 5173",
      url: "http://127.0.0.1:5173",
      cwd: ".",
      reuseExistingServer: false,
    },
  ],
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } },
  ],
});
