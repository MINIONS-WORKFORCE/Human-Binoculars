import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { useMock } from "./config";
import "../../shared/design-tokens.css";
import "./index.css";

async function enableMocking() {
  if (!useMock) {
    // If mocking was previously enabled in this browser, actively clean up
    // the registered service worker and stale image cache so requests hit the real API.
    if (typeof navigator !== "undefined" && "serviceWorker" in navigator) {
      try {
        const registrations = await navigator.serviceWorker.getRegistrations();
        for (const registration of registrations) {
          await registration.unregister();
        }
      } catch (error) {
        console.warn("[App] Could not unregister service worker:", error);
      }
    }
    if (typeof window !== "undefined" && "caches" in window) {
      try {
        const keys = await caches.keys();
        for (const key of keys) {
          await caches.delete(key);
        }
      } catch (error) {
        console.warn("[App] Could not clear cache storage:", error);
      }
    }
    return;
  }
  try {
    const { startMocking } = await import("./mocks/browser");
    await startMocking();
  } catch (error) {
    // No service worker (blocked, private window, old browser): still render the
    // page, so API calls fail visibly with the normal error states instead of a
    // blank screen. The error e2e test relies on this to route API calls itself.
    console.error("[MSW] Mocking could not start:", error);
  }
}

enableMocking().then(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
