import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

function App() {
  return (
    <main style={{ fontFamily: "system-ui", padding: 24 }}>
      <h1>SPHEREx training starter</h1>
      <p>API base URL: {import.meta.env.VITE_API_BASE_URL ?? "(not set, copy .env.example to .env)"}</p>
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
