import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import "../../../../shared/design-tokens.css";
import "./style.css";
import {
  LightcurveChart,
  SpectrumChart,
} from "../../../../shared/charts/Charts.jsx";
import { DETECTORS } from "../../../../shared/charts/chartData.js";
import {
  LIGHTCURVE_EMPTY,
  LIGHTCURVE_SAMPLE,
  LIGHTCURVE_WITH_WARNINGS,
  SPECTRUM_EMPTY,
  SPECTRUM_SAMPLE,
  SPECTRUM_WITH_WARNINGS,
} from "./samples.js";

const SAMPLES = [
  {
    id: "normal",
    label: "Normal",
    spectrum: SPECTRUM_SAMPLE,
    lightcurve: LIGHTCURVE_SAMPLE,
  },
  {
    id: "warnings",
    label: "With warnings",
    spectrum: SPECTRUM_WITH_WARNINGS,
    lightcurve: LIGHTCURVE_WITH_WARNINGS,
  },
  {
    id: "empty",
    label: "No data",
    spectrum: SPECTRUM_EMPTY,
    lightcurve: LIGHTCURVE_EMPTY,
  },
];

function Choice({ pressed, onClick, children }) {
  return (
    <button
      type="button"
      className="button"
      aria-pressed={pressed}
      onClick={onClick}
    >
      {children}
    </button>
  );
}

function App() {
  const [tab, setTab] = useState("spectrum");
  const [sampleId, setSampleId] = useState("normal");
  const [detector, setDetector] = useState("D3");
  const sample = SAMPLES.find((item) => item.id === sampleId);

  return (
    <main className="page">
      <h1 className="title">Selected point</h1>
      <p className="subtitle">Demo with synthetic samples, not SPHEREx data.</p>

      <div className="row" role="group" aria-label="Sample">
        {SAMPLES.map((item) => (
          <Choice
            key={item.id}
            pressed={item.id === sampleId}
            onClick={() => setSampleId(item.id)}
          >
            {item.label}
          </Choice>
        ))}
      </div>

      <section className="panel">
        <div className="row" role="group" aria-label="Chart">
          <Choice
            pressed={tab === "spectrum"}
            onClick={() => setTab("spectrum")}
          >
            Spectrum
          </Choice>
          <Choice
            pressed={tab === "lightcurve"}
            onClick={() => setTab("lightcurve")}
          >
            Light curve
          </Choice>
        </div>

        {tab === "spectrum" ? (
          <>
            <div className="row" role="group" aria-label="Detector in view">
              {DETECTORS.map(({ id }) => (
                <Choice
                  key={id}
                  pressed={id === detector}
                  onClick={() => setDetector(id)}
                >
                  {id}
                </Choice>
              ))}
            </div>
            <SpectrumChart data={sample.spectrum} selectedDetector={detector} />
          </>
        ) : (
          <LightcurveChart data={sample.lightcurve} />
        )}
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
