import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Read VITE_* variables from the shared .env at the repo root
  envDir: fileURLToPath(new URL("../..", import.meta.url)),
});
