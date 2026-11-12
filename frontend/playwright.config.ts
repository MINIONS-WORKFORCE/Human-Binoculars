import { defineConfig, devices } from "@playwright/test";

const PORT = 4173;

// End-to-end tests run against the production build with MSW mocks baked in
// (`vite build --mode mock`), so they need no backend and test what gets deployed.
export default defineConfig({
  testDir: "e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: `http://localhost:${PORT}`,
    trace: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        // PW_CHANNEL=msedge (or chrome) reuses an installed browser instead of the
        // downloaded Chromium, handy on machines where the download is blocked.
        channel: process.env.PW_CHANNEL || undefined,
      },
    },
  ],
  webServer: {
    command: `${process.platform === "win32" ? "npm.cmd" : "npm"} run build:mock && ${process.platform === "win32" ? "npx.cmd" : "npx"} vite preview --port ${PORT} --strictPort`,
    url: `http://localhost:${PORT}`,
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
