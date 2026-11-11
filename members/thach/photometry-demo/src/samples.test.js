import { describe, expect, it } from "vitest";
import { SHARED_SAMPLE, SYNTHETIC_RDRA } from "./samples.js";
import { photometrySummary } from "../../../../shared/charts/photometry.js";

describe.each([
  ["shared sample", SHARED_SAMPLE],
  ["synthetic R Dra", SYNTHETIC_RDRA],
])("%s follows the E6 contract rules", (_, sample) => {
  it("marks detected exactly when SNR is at least 3", () => {
    for (const point of sample.points) {
      if (point.snr != null) expect(point.detected).toBe(point.snr >= 3);
    }
  });

  it("keeps fluxes in mJy with non-negative uncertainties, never 0 for a missing value", () => {
    for (const point of sample.points) {
      if (point.err_mjy != null) expect(point.err_mjy).toBeGreaterThan(0);
      if (point.flux_mjy == null) expect(point.err_mjy).toBeNull();
      expect(point.detector).toBeGreaterThanOrEqual(1);
      expect(point.detector).toBeLessThanOrEqual(6);
    }
  });
});

describe("synthetic R Dra covers every chart rule", () => {
  it("has upper limits, a flagged point, a missing value and a reference star", () => {
    expect(photometrySummary(SYNTHETIC_RDRA)).toMatchObject({
      upperLimits: 2,
      flagged: 1,
      skipped: 1,
      hasReference: true,
      detectors: 6,
    });
  });
});
