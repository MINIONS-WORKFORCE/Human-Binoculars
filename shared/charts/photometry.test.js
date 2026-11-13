import { describe, expect, it } from "vitest";
import SAMPLE from "../../api_samples/photometry_rdra.json";
import {
  UPPER_LIMIT_SIGMA,
  markKind,
  photometryFigure,
  photometryRows,
  photometrySummary,
  plottedFlux,
} from "./photometry.js";

const theme = {
  surface: "#141a22",
  accent: "#4a96f0",
  muted: "#a9b4c0",
  raised: "#1e2733",
  border: "#2e3a48",
  control: "#7c8a9c",
  text: "#e8edf2",
  fontSans: "Inter",
  fontMono: "Mono",
};

function point(overrides = {}) {
  return {
    frame_id: "f",
    mjd: 60801,
    wavelength_um: 1.4,
    detector: 2,
    release: "qr2",
    survey: 1,
    flux_mjy: 10,
    err_mjy: 1,
    snr: 10,
    detected: true,
    flagged: false,
    is_reference_star: false,
    ...overrides,
  };
}

const response = (points) => ({
  api_version: "0.1",
  target: { ra: 248.1675, dec: 66.755, name: "R Draconis", target_key: "rdra" },
  reference_star: null,
  points,
  variability: null,
});

const LIMIT = point({ flux_mjy: 1.2, err_mjy: 0.8, snr: 1.5, detected: false });

describe("the shared sample (api_samples/photometry_rdra.json)", () => {
  it("draws its six detections over time with error bars", () => {
    const { data, layout } = photometryFigure(SAMPLE, { theme });
    expect(data).toHaveLength(1);
    expect(data[0].y).toEqual([11, 12, 13, 14, 15, 16]);
    expect(data[0].error_y.array).toEqual([1, 1, 1, 1, 1, 1]);
    expect(data[0].x[0]).toBe("2025-05-06T00:00:00.000Z"); // MJD 60801
    expect(layout.xaxis.type).toBe("date");
    expect(layout.showlegend).toBe(false);
  });

  it("switches the same points to a wavelength axis with the D1–D6 bands", () => {
    const { data, layout } = photometryFigure(SAMPLE, {
      xAxis: "wavelength",
      theme,
    });
    expect(data[0].x).toEqual(SAMPLE.points.map((p) => p.wavelength_um));
    expect(layout.xaxis.title.text).toBe("Wavelength (µm)");
    expect(layout.xaxis.range).toEqual([0.75, 5.0]);
    expect(layout.shapes).toHaveLength(6);
  });

  it("names the target in the legend and counts every point", () => {
    expect(photometryFigure(SAMPLE, { theme }).data[0].name).toBe("R Draconis");
    expect(photometrySummary(SAMPLE)).toMatchObject({
      plotted: 6,
      skipped: 0,
      upperLimits: 0,
      detectors: 6,
    });
  });
});

describe("upper limits", () => {
  it("draws a non-detection at 3 × err_mjy, not at its measured flux", () => {
    expect(markKind(LIMIT)).toBe("limit");
    expect(plottedFlux(LIMIT)).toBeCloseTo(UPPER_LIMIT_SIGMA * 0.8);
    const { data } = photometryFigure(response([LIMIT]), { theme });
    expect(data[0].y[0]).toBeCloseTo(2.4);
    expect(data[0].marker.symbol).toBe("arrow-bar-down");
    expect(data[0].error_y.visible).toBe(false);
    expect(data[0].name).toBe("R Draconis, upper limit (3σ)");
  });

  it("skips a non-detection without an uncertainty", () => {
    const missing = point({
      detected: false,
      err_mjy: null,
      flux_mjy: null,
      snr: null,
    });
    expect(markKind(missing)).toBeNull();
    expect(photometrySummary(response([missing, point()]))).toMatchObject({
      plotted: 1,
      skipped: 1,
    });
  });

  it("shows the limit in the table as a bound", () => {
    expect(photometryRows(response([LIMIT]))[0]).toEqual([
      "2025-05-06",
      "60801.00",
      "D2",
      "1.40",
      "Target",
      "< 2.4",
      "0.8",
      "1.5",
      "Upper limit",
    ]);
  });
});

describe("flags, reference star and missing values", () => {
  it("draws flagged points hollow but still draws them", () => {
    const { data } = photometryFigure(
      response([point(), point({ flagged: true, mjd: 60802 })]),
      { theme },
    );
    expect(data.map((trace) => trace.marker.symbol)).toEqual([
      "circle",
      "circle-open",
    ]);
    expect(data[1].y).toEqual([10]);
  });

  it("gives the reference star its own muted series", () => {
    const { data, layout } = photometryFigure(
      response([point(), point({ is_reference_star: true, flux_mjy: 5 })]),
      { theme },
    );
    expect(data.map((trace) => trace.name)).toEqual([
      "R Draconis",
      "Reference star",
    ]);
    expect(data[1].marker.color).toBe(theme.muted);
    expect(layout.showlegend).toBe(true);
  });

  it("never draws a missing flux as zero", () => {
    const { data } = photometryFigure(
      response([point(), point({ flux_mjy: null, mjd: 60802 })]),
      { theme },
    );
    expect(data[0].y).toEqual([10]);
  });
});

describe("detector filter", () => {
  const points = [
    point({ detector: 2 }),
    point({ detector: 3, wavelength_um: 2.0 }),
  ];

  it("keeps one detector and outlines its band", () => {
    const { data, layout } = photometryFigure(response(points), {
      xAxis: "wavelength",
      detector: 3,
      theme,
    });
    expect(data[0].x).toEqual([2.0]);
    expect(layout.shapes[2].line.color).toBe(theme.accent);
    expect(photometrySummary(response(points), { detector: 3 }).plotted).toBe(
      1,
    );
  });

  it("counts detectors so mixed wavelengths can be pointed out", () => {
    expect(photometrySummary(response(points)).detectors).toBe(2);
  });
});
