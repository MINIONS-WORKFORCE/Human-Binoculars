import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";
import { useMock } from "./config";
import "../../shared/design-tokens.css";
import "./index.css";

async function enableMocking() {
  if (!useMock) return;
  const { startMocking } = await import("./mocks/browser");
  await startMocking();
}

enableMocking().then(() => {
  createRoot(document.getElementById("root")!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
