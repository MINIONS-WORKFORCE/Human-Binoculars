// Turns /api/spectrum and /api/lightcurve responses into Plotly figures and table rows.
// Measurements are drawn as points with error bars and never joined: a line would imply
// values between observations. A null flux is a rejected measurement, never a zero.

export const DETECTORS = [
  { id: "D1", min: 0.75, max: 1.09 },
  { id: "D2", min: 1.1, max: 1.62 },
  { id: "D3", min: 1.63, max: 2.41 },
  { id: "D4", min: 2.42, max: 3.82 },
  { id: "D5", min: 3.83, max: 4.41 },
  { id: "D6", min: 4.42, max: 5.0 },
];

const WAVELENGTH_RANGE = [0.75, 5.0];
const MJD_UNIX_EPOCH = 40587;
const MS_PER_DAY = 86400000;

/** Three significant figures, no trailing zeros; "–" for a missing value. */
export function formatValue(value) {
  return value == null ? "–" : String(Number(value.toPrecision(3)));
}

/** 60800.5 -> "2025-05-05T12:00:00.000Z" */
export function mjdToIso(mjd) {
  return new Date((mjd - MJD_UNIX_EPOCH) * MS_PER_DAY).toISOString();
}

/** "SPHEREx-D6" -> "D6" */
export function detectorId(bandpassName) {
  return String(bandpassName).replace(/^SPHEREx-/, "");
}

export const rejectedCount = (points) =>
  points.filter((point) => point.flux == null).length;

const warningText = (point) =>
  point.warnings.map((warning) => warning.message).join(" ");

const errorText = (point, unit) =>
  point.flux_error == null
    ? `${unit}, no uncertainty available`
    : `± ${formatValue(point.flux_error)} ${unit}`;

function trace(points, { x, name, color, symbol, ring, details, hoverX }) {
  return {
    type: "scatter",
    mode: "markers",
    name,
    x: points.map(x),
    y: points.map((point) => point.flux),
    customdata: points.map(details),
    hovertemplate:
      `<b>${hoverX}</b><br>%{y:.3g} %{customdata[0]}` +
      `<br>%{customdata[1]}%{customdata[2]}<extra></extra>`,
    marker: {
      size: 9,
      symbol,
      color,
      line: ring,
    },
    error_y: {
      type: "data",
      array: points.map((point) => point.flux_error),
      visible: true,
      thickness: 1,
      width: 0,
      color,
    },
  };
}

// Points with a warning get their own series, so they differ by shape and label, not only color.
function traces(points, options, theme) {
  const measured = points.filter((point) => point.flux != null);
  const clean = measured.filter((point) => point.warnings.length === 0);
  const warned = measured.filter((point) => point.warnings.length > 0);
  const series = [];
  if (clean.length) {
    series.push(
      trace(clean, {
        ...options,
        name: "Measured",
        color: theme.accent,
        symbol: "circle",
        // A ring in the surface color keeps overlapping points apart.
        ring: { width: 1.5, color: theme.surface },
      }),
    );
  }
  if (warned.length) {
    series.push(
      trace(warned, {
        ...options,
        name: "Measured, has a warning",
        color: theme.warning,
        symbol: "circle-open",
        ring: { width: 2, color: theme.warning },
      }),
    );
  }
  return { series, showLegend: series.length > 1 };
}

function baseLayout(theme, { xTitle, yTitle, showLegend, top }) {
  const axisFont = { color: theme.muted, size: 12, family: theme.fontMono };
  const titleFont = { color: theme.muted, size: 12 };
  return {
    autosize: true,
    paper_bgcolor: "rgba(0,0,0,0)",
    plot_bgcolor: "rgba(0,0,0,0)",
    font: { family: theme.fontSans, color: theme.text, size: 14 },
    margin: { l: 56, r: 8, t: top, b: showLegend ? 84 : 48 },
    hovermode: "closest",
    dragmode: false,
    showlegend: showLegend,
    legend: {
      orientation: "h",
      x: 0,
      y: -0.2,
      yanchor: "top",
      font: { color: theme.text, size: 12 },
    },
    hoverlabel: {
      bgcolor: theme.raised,
      bordercolor: theme.control,
      font: { color: theme.text, family: theme.fontSans, size: 12 },
      align: "left",
    },
    xaxis: {
      title: { text: xTitle, font: titleFont, standoff: 8 },
      tickfont: axisFont,
      showgrid: false,
      zeroline: false,
      linecolor: theme.control,
      ticks: "outside",
      tickcolor: theme.control,
    },
    yaxis: {
      title: { text: yTitle, font: titleFont, standoff: 8 },
      tickfont: axisFont,
      gridcolor: theme.border,
      zeroline: true,
      zerolinecolor: theme.control,
      linecolor: theme.control,
    },
  };
}

export function spectrumFigure(response, { selected = null, theme }) {
  const unit = response.flux_unit ?? "";
  const { series, showLegend } = traces(
    response.points,
    {
      x: (point) => point.wavelength_um,
      unit,
      hoverX: "%{x:.2f} µm",
      details: (point) => [
        errorText(point, unit),
        detectorId(point.energy_bandpassname),
        point.warnings.length ? `<br>Warning: ${warningText(point)}` : "",
      ],
    },
    theme,
  );

  const layout = baseLayout(theme, {
    xTitle: "Wavelength (µm)",
    yTitle: `Flux (${unit})`,
    showLegend,
    top: 28,
  });
  layout.xaxis.range = WAVELENGTH_RANGE;
  layout.xaxis.tickvals = [1, 2, 3, 4, 5];

  // Detector bands to scale; every other one is shaded so the edges can be read.
  layout.shapes = DETECTORS.map((detector, index) => ({
    type: "rect",
    layer: "below",
    xref: "x",
    yref: "paper",
    x0: detector.min,
    x1: detector.max,
    y0: 0,
    y1: 1,
    fillcolor: index % 2 ? theme.raised : "rgba(0,0,0,0)",
    line:
      detector.id === selected
        ? { color: theme.accent, width: 2 }
        : { width: 0 },
  }));
  layout.annotations = DETECTORS.map((detector) => ({
    xref: "x",
    yref: "paper",
    x: (detector.min + detector.max) / 2,
    y: 1,
    yanchor: "bottom",
    showarrow: false,
    text: detector.id === selected ? `<b>${detector.id}</b>` : detector.id,
    font: {
      size: 12,
      color: detector.id === selected ? theme.text : theme.muted,
    },
  }));

  return { data: series, layout };
}

export function lightcurveFigure(response, { theme }) {
  const unit = response.flux_unit ?? "";
  const { series, showLegend } = traces(
    response.points,
    {
      x: (point) => mjdToIso(point.time_mjd),
      unit,
      hoverX: "%{x|%Y-%m-%d}",
      details: (point) => [
        errorText(point, unit),
        `MJD ${point.time_mjd.toFixed(2)}`,
        point.warnings.length ? `<br>Warning: ${warningText(point)}` : "",
      ],
    },
    theme,
  );

  const layout = baseLayout(theme, {
    xTitle: "Observation date",
    yTitle: `Flux (${unit})`,
    showLegend,
    top: 12,
  });
  layout.xaxis.type = "date";
  layout.xaxis.tickformat = "%b %Y";
  layout.xaxis.nticks = 6;

  return { data: series, layout };
}

const fluxCell = (point) =>
  point.flux == null ? "Rejected" : formatValue(point.flux);

export function spectrumRows(response) {
  return [...response.points]
    .sort((a, b) => a.wavelength_um - b.wavelength_um)
    .map((point) => [
      point.wavelength_um.toFixed(2),
      detectorId(point.energy_bandpassname),
      fluxCell(point),
      formatValue(point.flux_error),
      warningText(point) || "–",
    ]);
}

export function lightcurveRows(response) {
  return [...response.points]
    .sort((a, b) => a.time_mjd - b.time_mjd)
    .map((point) => [
      mjdToIso(point.time_mjd).slice(0, 10),
      point.time_mjd.toFixed(2),
      fluxCell(point),
      formatValue(point.flux_error),
      warningText(point) || "–",
    ]);
}
