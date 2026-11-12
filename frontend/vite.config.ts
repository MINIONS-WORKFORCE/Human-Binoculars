import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The frontend lives in <repo>/frontend but reads two things from the repo root:
// the shared .env (VITE_* variables) and the synthetic samples in api_samples/.
const repoRoot = fileURLToPath(new URL("..", import.meta.url));

export default defineConfig({
  plugins: [react()],
  // shared/ sits outside frontend/, so its imports would otherwise resolve from the
  // repo root (two copies of React, and no packages at all in CI's frontend-only install).
  resolve: {
    dedupe: ["react", "react-dom", "plotly.js-basic-dist-min", "aladin-lite"],
  },
  envDir: repoRoot,
  server: {
    fs: { allow: [repoRoot] },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    setupFiles: ["src/test/setup.ts"],
  },
});
