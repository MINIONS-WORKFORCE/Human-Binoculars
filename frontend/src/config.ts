// Mocks are on by default in `npm run dev` so the frontend works without a backend.
// VITE_USE_MOCK=false in dev talks to the real API; VITE_USE_MOCK=true in a build
// ships a demo that runs entirely on api_samples/.
const flag = import.meta.env.VITE_USE_MOCK;

export const useMock =
  flag === "true" || (import.meta.env.DEV && flag !== "false");

// With mocks on, requests stay on this origin and the service worker answers them.
export const apiBase = useMock ? "" : (import.meta.env.VITE_API_BASE_URL ?? "");
