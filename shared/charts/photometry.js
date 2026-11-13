// Turns an E6 /api/photometry response into a Plotly figure and table rows.
// Rules from the API contract wiki: detected=false (SNR < 3) is drawn as an upper limit
// at 3 × err_mjy instead of a point; a flagged point is drawn hollow but still shown;
// the reference star shares the list (is_reference_star). The same points plot over
// time (mjd) or by wavelength (wavelength_um).

import {
  addDetectorBands,
  baseLayout,
  dateTickFormat,
  formatValue,
  mjdToIso,
} from "./chartData.js";

export const UPPER_LIMIT_SIGMA = 3;
export const X_AXES = { time: "Over time", wavelength: "By wavelength" };

/** "point", "flagged" or "limit"; null when the point has nothing to draw. */
export function markKind(point) {
  if (!point.detected) return point.err_mjy == null ? null : "limit";
  if (point.flux_mjy == null) return null;
  return point.flagged ? "flagged" : "point";
}

/** Height of the mark: the flux, or 3 × err_mjy for an upper limit. */
export function plottedFlux(point) {
  return point.detected ? point.flux_mjy : UPPER_LIMIT_SIGMA * point.err_mjy;
}

export function selectPoints(response, detector = null) {
  return response.points.filter(
    (point) => detector == null || point.detector === detector,
  );
}

export function photometrySummary(response, { detector = null } = {}) {
  const points = selectPoints(response, detector);
  const target = points.filter((point) => !point.is_reference_star);
  return {
    plotted: points.filter(markKind).length,
    skipped: points.filter((point) => !markKind(point)).length,
    upperLimits: target.filter((point) => markKind(point) === "limit").length,
    flagged: target.filter((point) => markKind(point) === "flagged").length,
    detectors: new Set(target.map((point) => point.detector)).size,
    hasReference: points.some((point) => point.is_reference_star),
  };
}

function fluxText(point) {
  if (markKind(point) === "limit") {
    return `< ${formatValue(plottedFlux(point))} mJy (${UPPER_LIMIT_SIGMA}σ upper limit)`;
  }
  return point.err_mjy == null
    ? `${formatValue(point.flux_mjy)} mJy, no uncertainty`
    : `${formatValue(point.flux_mjy)} ± ${formatValue(point.err_mjy)} mJy`;
}

function hoverDetails(point) {
  return [
    fluxText(point),
    `D${point.detector} · ${point.wavelength_um.toFixed(2)} µm`,
    `MJD ${point.mjd.toFixed(2)} · survey ${point.survey} · ${point.release}`,
    `SNR ${formatValue(point.snr)}${point.flagged ? " · flagged pixels in aperture" : ""}`,
  ];
}

const HOVER =
  "<b>%{customdata[0]}</b><br>%{customdata[1]}<br>%{customdata[2]}" +
  "<br>%{customdata[3]}<extra>%{fullData.name}</extra>";

function trace(points, { name, color, kind, x, theme }) {
  const limit = kind === "limit";
  const symbol = {
    point: "circle",
    flagged: "circle-open",
    limit: "arrow-bar-down",
  }[kind];
  return {
    type: "scatter",
    mode: "markers",
    name,
    x: points.map(x),
    y: points.map(plottedFlux),
    customdata: points.map(hoverDetails),
    hovertemplate: HOVER,
    marker: {
      size: limit ? 12 : 9,
      symbol,
      color,
      // A surface ring keeps overlapping filled points apart.
      line:
        kind === "point"
          ? { width: 1.5, color: theme.surface }
          : { width: 2, color },
    },
    error_y: limit
      ? { visible: false }
      : {
          type: "data",
          array: points.map((point) => point.err_mjy),
          visible: true,
          thickness: 1,
          width: 0,
          color,
        },
  };
}

function seriesFor(points, { label, color, x, theme }) {
  const byKind = (kind) => points.filter((point) => markKind(point) === kind);
  return [
    { kind: "point", name: label },
    { kind: "flagged", name: `${label}, flagged pixels` },
    { kind: "limit", name: `${label}, upper limit (${UPPER_LIMIT_SIGMA}σ)` },
  ]
    .map(({ kind, name }) => ({ kind, name, points: byKind(kind) }))
    .filter((group) => group.points.length)
    .map(({ kind, name, points: group }) =>
      trace(group, { name, color, kind, x, theme }),
    );
}

/**
 * xAxis: "time" (mjd, shown as dates) or "wavelength" (wavelength_um, with D1–D6 bands).
 * detector: 1–6 to keep one detector, or null for all of them.
 */
export function photometryFigure(
  response,
  { xAxis = "time", detector = null, theme },
) {
  const points = selectPoints(response, detector);
  const x =
    xAxis === "wavelength"
      ? (point) => point.wavelength_um
      : (point) => mjdToIso(point.mjd);

  const data = [
    ...seriesFor(
      points.filter((point) => !point.is_reference_star),
      {
        label: response.target?.name ?? "Target",
        color: theme.accent,
        x,
        theme,
      },
    ),
    ...seriesFor(
      points.filter((point) => point.is_reference_star),
      { label: "Reference star", color: theme.muted, x, theme },
    ),
  ];

  const showLegend = data.length > 1;
  if (xAxis === "wavelength") {
    const layout = baseLayout(theme, {
      xTitle: "Wavelength (µm)",
      yTitle: "Flux (mJy)",
      showLegend,
      top: 28,
    });
    addDetectorBands(layout, theme, detector == null ? null : `D${detector}`);
    return { data, layout };
  }

  const layout = baseLayout(theme, {
    xTitle: "Observation date",
    yTitle: "Flux (mJy)",
    showLegend,
    top: 12,
  });
  layout.xaxis.type = "date";
  layout.xaxis.tickformat = dateTickFormat(
    points.filter(markKind).map((point) => point.mjd),
  );
  layout.xaxis.nticks = 6;
  return { data, layout };
}

function statusCell(point) {
  const kind = markKind(point);
  if (kind === "limit") return "Upper limit";
  if (kind === "flagged") return "Flagged";
  if (kind === "point") return "Detected";
  return "No value";
}

export const PHOTOMETRY_COLUMNS = [
  "Date",
  "MJD",
  "Detector",
  "Wavelength (µm)",
  "Source",
  "Flux (mJy)",
  "Uncertainty (mJy)",
  "SNR",
  "Status",
];

export function photometryRows(response, { detector = null } = {}) {
  return [...selectPoints(response, detector)]
    .sort((a, b) => a.mjd - b.mjd || a.detector - b.detector)
    .map((point) => [
      mjdToIso(point.mjd).slice(0, 10),
      point.mjd.toFixed(2),
      `D${point.detector}`,
      point.wavelength_um.toFixed(2),
      point.is_reference_star ? "Reference" : "Target",
      markKind(point) === "limit"
        ? `< ${formatValue(plottedFlux(point))}`
        : formatValue(point.flux_mjy),
      formatValue(point.err_mjy),
      formatValue(point.snr),
      statusCell(point),
    ]);
}
