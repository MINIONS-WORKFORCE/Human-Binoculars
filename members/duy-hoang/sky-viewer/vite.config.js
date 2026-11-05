import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Read VITE_* variables from the shared .env at the repo root
  envDir: fileURLToPath(new URL("../../..", import.meta.url)),
  server: {
    proxy: {
      // MAST Name Lookup has no CORS headers; /mast/api/v0/invoke -> https://mast.stsci.edu/api/v0/invoke
      "/mast": {
        target: "https://mast.stsci.edu",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/mast/, ""),
      },
    },
  },
});
