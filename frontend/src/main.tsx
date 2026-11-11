import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { useMock } from "./config";
import "../../shared/design-tokens.css";
import "./index.css";

async function enableMocking() {
  if (!useMock) return;
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
