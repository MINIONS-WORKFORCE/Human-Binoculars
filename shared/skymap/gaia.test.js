import { describe, expect, it, vi } from "vitest";
import {
  GAIA_CATALOG,
  GAIA_LIMIT,
  GAIA_TIMEOUT_MS,
  coneTarget,
  createGaiaLoader,
  mockGaiaSources,
  radiusForFov,
} from "./gaia.js";

// Great-circle distance in degrees.
function separation(ra1, dec1, ra2, dec2) {
  const rad = Math.PI / 180;
  const a =
    Math.sin(((dec2 - dec1) * rad) / 2) ** 2 +
    Math.cos(dec1 * rad) *
      Math.cos(dec2 * rad) *
      Math.sin(((ra2 - ra1) * rad) / 2) ** 2;
  return (2 * Math.asin(Math.sqrt(a))) / rad;
}

describe("coneTarget", () => {
  it("always writes the sign of Dec", () => {
    expect(coneTarget(269.452, 4.693)).toBe("269.452 +4.693");
    expect(coneTarget(133.7951, -7.2451)).toBe("133.7951 -7.2451");
  });
});

describe("radiusForFov", () => {
  it("covers the corners of a square view", () => {
    expect(radiusForFov(0.2)).toBeCloseTo(0.1414, 3);
  });

  it("stays within its limits", () => {
    expect(radiusForFov(0.001)).toBeCloseTo(2 / 60);
    expect(radiusForFov(30)).toBe(0.5);
  });
});

function setup({ sources = [] } = {}) {
  const calls = [];
  const A = {
    catalogFromVizieR: (id, target, radius, options, success, error) => {
      const catalog = { getSources: () => sources };
      calls.push({ id, target, radius, options, success, error, catalog });
      return catalog;
    },
    catalog: (options) => {
      const added = [];
      return { options, added, addSources: (list) => added.push(...list) };
    },
    source: (ra, dec, data) => ({ ra, dec, data }),
  };
  const aladin = { addCatalog: vi.fn(), removeOverlay: vi.fn() };
  const onStatus = vi.fn();
  const timers = [];
  const loader = createGaiaLoader(A, aladin, {
    color: "#ffc46b",
    onStatus,
    setTimer: (fn, ms) => {
      timers.push({ fn, ms });
      return timers.length;
    },
  });
  return { calls, aladin, onStatus, loader, timers };
}

const VIEW = { raDeg: 269.452, decDeg: 4.693, fovDeg: 0.2 };

describe("createGaiaLoader", () => {
  it("asks VizieR for Gaia DR3 with a limit and adds the catalog", () => {
    const { calls, aladin, onStatus, loader } = setup();
    loader.load(VIEW);
    expect(calls[0].id).toBe(GAIA_CATALOG);
    expect(calls[0].target).toBe("269.452 +4.693");
    expect(calls[0].options.limit).toBe(GAIA_LIMIT);
    expect(aladin.addCatalog).toHaveBeenCalledWith(calls[0].catalog);
    expect(onStatus).toHaveBeenLastCalledWith({ state: "loading" });
  });

  it("reports the number of sources", () => {
    const { calls, onStatus, loader } = setup({ sources: [{}, {}] });
    loader.load(VIEW);
    calls[0].success(calls[0].catalog);
    expect(onStatus).toHaveBeenLastCalledWith({
      state: "ok",
      count: 2,
      truncated: false,
    });
  });

  it("reports an empty result and a failure differently", () => {
    const { calls, onStatus, loader } = setup();
    loader.load(VIEW);
    calls[0].success(calls[0].catalog);
    expect(onStatus.mock.lastCall[0].state).toBe("empty");
    loader.load(VIEW);
    calls[1].error();
    expect(onStatus.mock.lastCall[0].state).toBe("error");
  });

  it("flags a result cut off at the limit", () => {
    const { calls, onStatus, loader } = setup({
      sources: new Array(GAIA_LIMIT).fill({}),
    });
    loader.load(VIEW);
    calls[0].success(calls[0].catalog);
    expect(onStatus.mock.lastCall[0].truncated).toBe(true);
  });

  it("removes the old overlay and ignores its late answer", () => {
    const { calls, aladin, onStatus, loader } = setup({ sources: [{}] });
    loader.load(VIEW);
    loader.load(VIEW);
    expect(aladin.removeOverlay).toHaveBeenCalledWith(calls[0].catalog);
    calls[0].success(calls[0].catalog);
    calls[0].error();
    expect(onStatus).toHaveBeenLastCalledWith({ state: "loading" });
  });

  it("says when VizieR is slow, but not for an older request", () => {
    const { timers, onStatus, loader } = setup();
    loader.load(VIEW);
    expect(timers[0].ms).toBe(GAIA_TIMEOUT_MS);
    timers[0].fn();
    expect(onStatus).toHaveBeenLastCalledWith({ state: "slow" });
    loader.load(VIEW);
    timers[0].fn();
    expect(onStatus).toHaveBeenLastCalledWith({ state: "loading" });
  });
});

describe("mockGaiaSources", () => {
  it("puts every synthetic star inside the cone of the view", () => {
    for (const [ra, dec] of [
      [269.452, 4.693],
      [248.1676, 66.755], // high Dec: RA spread must widen
      [0.01, -30], // RA wraps around 0
    ]) {
      const stars = mockGaiaSources(ra, dec, 0.2);
      expect(stars).toHaveLength(40);
      for (const star of stars) {
        expect(star.raDeg).toBeGreaterThanOrEqual(0);
        expect(star.raDeg).toBeLessThan(360);
        expect(
          separation(ra, dec, star.raDeg, star.decDeg),
        ).toBeLessThanOrEqual(radiusForFov(0.2) * 1.01);
      }
    }
  });

  it("gives the same stars for the same position", () => {
    expect(mockGaiaSources(133.7951, -7.2451, 0.1)).toEqual(
      mockGaiaSources(133.7951, -7.2451, 0.1),
    );
  });
});

describe("createGaiaLoader: synthetic and off", () => {
  it("draws synthetic stars without calling VizieR", () => {
    const { calls, aladin, onStatus, loader } = setup();
    const catalog = loader.load(VIEW, { source: "mock" });
    expect(calls).toHaveLength(0);
    expect(aladin.addCatalog).toHaveBeenCalledWith(catalog);
    expect(catalog.options.name).toBe("Gaia DR3 (synthetic)");
    expect(catalog.added).toHaveLength(40);
    expect(catalog.added[0].data.note).toMatch(/synthetic/);
    expect(onStatus).toHaveBeenLastCalledWith({
      state: "ok",
      count: 40,
      truncated: false,
      synthetic: true,
    });
  });

  it("switching to synthetic drops a VizieR answer still on its way", () => {
    const { calls, onStatus, loader } = setup({ sources: [{}] });
    loader.load(VIEW);
    loader.load(VIEW, { source: "mock" });
    calls[0].success(calls[0].catalog);
    expect(onStatus.mock.lastCall[0].synthetic).toBe(true);
  });

  it("clear removes the overlay and ignores late answers", () => {
    const { calls, aladin, onStatus, loader } = setup({ sources: [{}] });
    loader.load(VIEW);
    loader.clear();
    expect(aladin.removeOverlay).toHaveBeenCalledWith(calls[0].catalog);
    calls[0].success(calls[0].catalog);
    expect(onStatus).toHaveBeenLastCalledWith({ state: "off" });
  });
});
