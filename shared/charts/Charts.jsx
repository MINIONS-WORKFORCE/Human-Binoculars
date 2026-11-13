import { useEffect, useMemo, useRef, useState } from "react";
import Plotly from "plotly.js-basic-dist-min";
import "./charts.css";
import {
  DETECTORS,
  lightcurveFigure,
  lightcurveRows,
  rejectedCount,
  spectrumFigure,
  spectrumRows,
} from "./chartData.js";
import {
  PHOTOMETRY_COLUMNS,
  UPPER_LIMIT_SIGMA,
  X_AXES,
  photometryFigure,
  photometryRows,
  photometrySummary,
} from "./photometry.js";

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

function DataTable({ columns, rows }) {
  return (
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
            {rows.map((row, rowIndex) => (
              <tr key={rowIndex}>
                {row.map((cell, index) => (
                  <td key={columns[index]}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
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
      <DataTable columns={columns} rows={rows} />
    </figure>
  );
}

const plural = (count, one, many) => `${count} ${count === 1 ? one : many}`;

function photometryCaption(data, summary) {
  const parts = [
    `${data.target?.name ?? "Target"} · ${plural(summary.plotted, "measurement", "measurements")}`,
  ];
  if (summary.upperLimits) {
    parts.push(
      `${plural(summary.upperLimits, "upper limit", "upper limits")} (${UPPER_LIMIT_SIGMA}σ, SNR below 3)`,
    );
  }
  if (summary.flagged) {
    parts.push(`${summary.flagged} flagged (hollow)`);
  }
  if (summary.skipped) {
    parts.push(`${summary.skipped} without a value, not plotted`);
  }
  return `${parts.join(" · ")}.`;
}

function variabilityText(variability) {
  if (!variability) return null;
  const {
    chi2_reduced: chi2,
    dof,
    is_variable: variable,
    method,
  } = variability;
  return `Variability test (${method}): reduced χ² ${chi2} over ${dof} degrees of freedom, reported as ${variable ? "variable" : "not variable"}.`;
}

/**
 * data: an E6 /api/photometry response. The viewer switches between a light curve
 * (x = mjd) and a spectrum (x = wavelength_um) and can keep a single detector.
 */
export function PhotometryChart({ data, defaultXAxis = "time" }) {
  const [xAxis, setXAxis] = useState(defaultXAxis);
  const [detector, setDetector] = useState(null);
  const figure = useMemo(
    () => photometryFigure(data, { xAxis, detector, theme: readTheme() }),
    [data, xAxis, detector],
  );
  const summary = photometrySummary(data, { detector });
  const mixed = xAxis === "time" && summary.detectors > 1;
  const variability = variabilityText(data.variability);

  return (
    <figure className="flux-chart">
      <div className="flux-chart__controls">
        <div role="group" aria-label="X axis" className="flux-chart__toggle">
          {Object.entries(X_AXES).map(([value, label]) => (
            <button
              key={value}
              type="button"
              aria-pressed={xAxis === value}
              onClick={() => setXAxis(value)}
            >
              {label}
            </button>
          ))}
        </div>
        <label className="flux-chart__select">
          Detector
          <select
            value={detector ?? ""}
            onChange={(event) =>
              setDetector(
                event.target.value ? Number(event.target.value) : null,
              )
            }
          >
            <option value="">All</option>
            {DETECTORS.map(({ id }) => (
              <option key={id} value={id.slice(1)}>
                {id}
              </option>
            ))}
          </select>
        </label>
      </div>

      {summary.plotted ? (
        <Plot
          figure={figure}
          label={`${xAxis === "time" ? "Light curve" : "Spectrum"} with ${summary.plotted} measurements. The data table below lists every value.`}
        />
      ) : (
        <p className="flux-chart__empty">No measurements for this detector.</p>
      )}
      <figcaption className="flux-chart__caption">
        {photometryCaption(data, summary)}
      </figcaption>
      {mixed && (
        <p className="flux-chart__note">
          These points come from {summary.detectors} detectors at different
          wavelengths. Pick one detector to compare like with like over time.
        </p>
      )}
      {variability && <p className="flux-chart__note">{variability}</p>}
      <DataTable
        columns={PHOTOMETRY_COLUMNS}
        rows={photometryRows(data, { detector })}
      />
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
