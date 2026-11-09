import { describe, expect, it } from "vitest";
import {
  DETECTORS,
  detectorId,
  formatValue,
  lightcurveFigure,
  lightcurveRows,
  mjdToIso,
  rejectedCount,
  spectrumFigure,
  spectrumRows,
} from "./chartData.js";

const theme = {
  surface: "#141a22",
  accent: "#4a96f0",
  warning: "#ffc46b",
  raised: "#1e2733",
  border: "#2e3a48",
  control: "#7c8a9c",
  text: "#e8edf2",
  muted: "#a9b4c0",
  fontSans: "Inter",
  fontMono: "Mono",
};

const WARNING = { code: "SATURATED", message: "Core is saturated." };

function spectrumPoint(wavelength, flux, overrides = {}) {
  return {
    wavelength_um: wavelength,
    flux,
    flux_error: 0.1,
    energy_bandpassname: "SPHEREx-D6",
    t_min: 61000,
    t_max: 61000,
    source_obs_publisher_dids: ["ivo://example"],
    warnings: [],
    ...overrides,
  };
}

const spectrum = (points) => ({ flux_unit: "mJy", points });
const lightcurve = (points) => ({ flux_unit: "mJy", points });

function lightcurvePoint(mjd, flux, overrides = {}) {
  return {
    time_mjd: mjd,
    t_min: mjd,
    t_max: mjd,
    flux,
    flux_error: 0.1,
    source_obs_publisher_dids: ["ivo://example"],
    warnings: [],
    ...overrides,
  };
}

describe("helpers", () => {
  it("formats values without trailing zeros, and marks a missing one", () => {
    expect(formatValue(1.2345)).toBe("1.23");
    expect(formatValue(1)).toBe("1");
    expect(formatValue(null)).toBe("–");
  });

  it("converts MJD to a calendar date", () => {
    expect(mjdToIso(40587)).toBe("1970-01-01T00:00:00.000Z");
    expect(mjdToIso(60800.5)).toBe("2025-05-05T12:00:00.000Z");
  });

  it("shortens the bandpass name", () => {
    expect(detectorId("SPHEREx-D6")).toBe("D6");
  });

  it("counts rejected measurements", () => {
    expect(rejectedCount([spectrumPoint(1, null), spectrumPoint(2, 1)])).toBe(
      1,
    );
  });
});

describe("spectrumFigure", () => {
  it("plots a rejected measurement as nothing, never as zero", () => {
    const { data } = spectrumFigure(
      spectrum([spectrumPoint(4.5, 1), spectrumPoint(4.6, null)]),
      { theme },
    );
    expect(data).toHaveLength(1);
    expect(data[0].y).toEqual([1]);
    expect(data[0].x).toEqual([4.5]);
  });

  it("uses points with error bars and no connecting line", () => {
    const { data } = spectrumFigure(spectrum([spectrumPoint(4.5, 1)]), {
      theme,
    });
    expect(data[0].mode).toBe("markers");
    expect(data[0].error_y.array).toEqual([0.1]);
  });

  it("gives warned points their own shape and a legend", () => {
    const { data, layout } = spectrumFigure(
      spectrum([
        spectrumPoint(4.5, 1),
        spectrumPoint(4.6, 2, { warnings: [WARNING] }),
      ]),
      { theme },
    );
    expect(data.map((series) => series.marker.symbol)).toEqual([
      "circle",
      "circle-open",
    ]);
    expect(layout.showlegend).toBe(true);
  });

  it("needs no legend for one series", () => {
    const { layout } = spectrumFigure(spectrum([spectrumPoint(4.5, 1)]), {
      theme,
    });
    expect(layout.showlegend).toBe(false);
  });

  it("draws all six detectors to scale and outlines the selected one", () => {
    const { layout } = spectrumFigure(spectrum([spectrumPoint(4.5, 1)]), {
      selected: "D6",
      theme,
    });
    expect(layout.shapes).toHaveLength(DETECTORS.length);
    expect(layout.shapes[0].x0).toBe(0.75);
    expect(layout.shapes[5].x1).toBe(5);
    expect(layout.shapes[5].line.color).toBe(theme.accent);
    expect(layout.shapes[0].line.width).toBe(0);
    expect(layout.annotations[5].text).toBe("<b>D6</b>");
  });

  it("labels the y axis with the unit from the response", () => {
    const { layout } = spectrumFigure(
      { flux_unit: "Jy", points: [spectrumPoint(4.5, 1)] },
      { theme },
    );
    expect(layout.yaxis.title.text).toBe("Flux (Jy)");
  });

  it("handles a missing uncertainty and an empty response", () => {
    const { data } = spectrumFigure(
      spectrum([spectrumPoint(4.5, 1, { flux_error: null })]),
      { theme },
    );
    expect(data[0].customdata[0][0]).toBe("mJy, no uncertainty available");
    expect(
      spectrumFigure({ flux_unit: null, points: [] }, { theme }).data,
    ).toEqual([]);
  });
});

describe("lightcurveFigure", () => {
  it("uses a date axis and leaves rejected measurements out", () => {
    const { data, layout } = lightcurveFigure(
      lightcurve([lightcurvePoint(60800.5, 1), lightcurvePoint(60900, null)]),
      { theme },
    );
    expect(layout.xaxis.type).toBe("date");
    expect(data[0].x).toEqual(["2025-05-05T12:00:00.000Z"]);
    expect(data[0].y).toEqual([1]);
    expect(data[0].mode).toBe("markers");
  });
});

describe("table rows", () => {
  it("sorts the spectrum and keeps rejected measurements visible", () => {
    const rows = spectrumRows(
      spectrum([
        spectrumPoint(4.6, null),
        spectrumPoint(4.5, 1, { warnings: [WARNING] }),
      ]),
    );
    expect(rows).toEqual([
      ["4.50", "D6", "1", "0.1", "Core is saturated."],
      ["4.60", "D6", "Rejected", "0.1", "–"],
    ]);
  });

  it("sorts the light curve by time", () => {
    const rows = lightcurveRows(
      lightcurve([lightcurvePoint(60900, 2), lightcurvePoint(60800.5, 1)]),
    );
    expect(rows.map((row) => row[0])).toEqual(["2025-05-05", "2025-08-13"]);
  });
});
