import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import "../../../../shared/design-tokens.css";
import "./style.css";
import { PhotometryChart } from "../../../../shared/charts/Charts.jsx";
import { SHARED_SAMPLE, SYNTHETIC_RDRA } from "./samples.js";

const SAMPLES = [
  {
    id: "shared",
    label: "api_samples/photometry_rdra.json",
    data: SHARED_SAMPLE,
  },
  {
    id: "synthetic",
    label: "Limits, flags and reference star",
    data: SYNTHETIC_RDRA,
  },
];

function App() {
  const [sampleId, setSampleId] = useState("synthetic");
  const sample = SAMPLES.find((item) => item.id === sampleId);

  return (
    <main className="page">
      <h1 className="title">Brightness of R Draconis</h1>
      <p className="subtitle">
        Demo with synthetic E6 samples, not SPHEREx measurements.
      </p>

      <div className="row" role="group" aria-label="Sample">
        {SAMPLES.map((item) => (
          <button
            key={item.id}
            type="button"
            className="button"
            aria-pressed={item.id === sampleId}
            onClick={() => setSampleId(item.id)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <section className="panel">
        {/* key resets the axis and detector choice when the sample changes */}
        <PhotometryChart key={sample.id} data={sample.data} />
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
