import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

// The frontend lives in <repo>/frontend but reads two things from the repo root:
// the shared .env (VITE_* variables) and the synthetic samples in api_samples/.
const repoRoot = fileURLToPath(new URL("..", import.meta.url));
const frontendNodeModules = fileURLToPath(new URL("./node_modules", import.meta.url));

export default defineConfig({
  plugins: [react()],
  // shared/ sits outside frontend/, so its imports resolve using these aliases
  // to avoid missing packages or duplicate React copies.
  resolve: {
    alias: {
      "plotly.js-basic-dist-min": `${frontendNodeModules}/plotly.js-basic-dist-min`,
      "aladin-lite": `${frontendNodeModules}/aladin-lite`,
      react: `${frontendNodeModules}/react`,
      "react-dom": `${frontendNodeModules}/react-dom`,
    },
    dedupe: ["react", "react-dom", "plotly.js-basic-dist-min", "aladin-lite"],
  },
  optimizeDeps: {
    include: ["plotly.js-basic-dist-min", "aladin-lite"],
  },
  envDir: repoRoot,
  server: {
    fs: { allow: [repoRoot] },
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: "node",
    include: ["src/**/*.test.ts"],
    setupFiles: ["src/test/setup.ts"],
  },
});
