import { useEffect, useMemo, useRef } from "react";
import Plotly from "plotly.js-basic-dist-min";
import "./charts.css";
import {
  lightcurveFigure,
  lightcurveRows,
  rejectedCount,
  spectrumFigure,
  spectrumRows,
} from "./chartData.js";

const PLOT_CONFIG = { displayModeBar: false, responsive: true };

// Plotly draws to canvas/SVG and cannot read CSS variables, so it gets their values.
function readTheme() {
  const styles = getComputedStyle(document.documentElement);
  const token = (name) => styles.getPropertyValue(name).trim();
  return {
    surface: token("--color-surface"),
    accent: token("--color-accent"),
    warning: token("--color-warning"),
    raised: token("--color-raised"),
    border: token("--color-border"),
    control: token("--color-control"),
    text: token("--color-text"),
    muted: token("--color-muted"),
    fontSans: token("--font-sans"),
    fontMono: token("--font-mono"),
  };
}

function Plot({ figure, label }) {
  const ref = useRef(null);

  useEffect(() => {
    Plotly.react(ref.current, figure.data, figure.layout, PLOT_CONFIG);
  }, [figure]);

  useEffect(() => {
    const el = ref.current;
    return () => Plotly.purge(el);
  }, []);

  return (
    <div ref={ref} className="flux-chart__plot" role="img" aria-label={label} />
  );
}

function ChartCard({ data, figure, label, caption, columns, rows }) {
  const rejected = rejectedCount(data.points);

  if (data.points.length === 0) {
    const message =
      data.warnings.find((warning) => warning.code === "NO_DATA")?.message ??
      "No measurements for this position.";
    return <p className="flux-chart__empty">{message}</p>;
  }

  return (
    <figure className="flux-chart">
      <Plot figure={figure} label={label} />
      <figcaption className="flux-chart__caption">
        {caption}
        {rejected > 0 &&
          ` ${rejected} rejected ${rejected === 1 ? "measurement is" : "measurements are"} not plotted.`}
      </figcaption>
      {data.warnings.map((warning) => (
        <p key={warning.code} role="status" className="flux-chart__warning">
          Warning: {warning.message}
        </p>
      ))}
      <details className="flux-chart__details">
        <summary>Show data table</summary>
        <div className="flux-chart__table-box">
          <table className="flux-chart__table">
            <thead>
              <tr>
                {columns.map((column) => (
                  <th key={column} scope="col">
                    {column}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row[0] + row[1]}>
                  {row.map((cell, index) => (
                    <td key={columns[index]}>{cell}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}

/** data: a /api/spectrum response. selectedDetector: "D1".."D6" to outline, optional. */
export function SpectrumChart({ data, selectedDetector = null }) {
  const figure = useMemo(
    () =>
      spectrumFigure(data, { selected: selectedDetector, theme: readTheme() }),
    [data, selectedDetector],
  );
  return (
    <ChartCard
      data={data}
      figure={figure}
      label={`Spectrum with ${data.points.length} measurements. The data table below lists every value.`}
      caption={`Method: ${data.measurement_method} · Release: ${data.query.obs_collection}.`}
      columns={[
        "Wavelength (µm)",
        "Detector",
        `Flux (${data.flux_unit})`,
        "Uncertainty",
        "Warning",
      ]}
      rows={spectrumRows(data)}
    />
  );
}

/** data: a /api/lightcurve response. */
export function LightcurveChart({ data }) {
  const figure = useMemo(
    () => lightcurveFigure(data, { theme: readTheme() }),
    [data],
  );
  const passband =
    data.wavelength_min_um == null
      ? ""
      : `Passband ${data.wavelength_min_um.toFixed(2)}–${data.wavelength_max_um.toFixed(2)} µm · `;
  return (
    <ChartCard
      data={data}
      figure={figure}
      label={`Light curve with ${data.points.length} measurements. The data table below lists every value.`}
      caption={`${passband}Method: ${data.measurement_method} · Release: ${data.query.obs_collection}.`}
      columns={[
        "Date",
        "MJD",
        `Flux (${data.flux_unit})`,
        "Uncertainty",
        "Warning",
      ]}
      rows={lightcurveRows(data)}
    />
  );
}
