// Gaia DR3 overlay for Aladin Lite. Real sources come from VizieR through
// A.catalogFromVizieR; "mock" draws synthetic Gaia-like stars so the map works offline.
// Gaia positions are for epoch 2016.0, so a fast mover sits away from where it appears
// in images taken at another date. That offset is real, not a bug.

export const GAIA_CATALOG = "I/355/gaiadr3";
export const GAIA_LIMIT = 5000; // Aladin's default is 100000, too heavy for a demo
export const GAIA_TIMEOUT_MS = 30000; // same threshold as "IRSA is slow" in the risk table
export const GAIA_SOURCES = ["vizier", "mock", "off"];

const MIN_RADIUS_DEG = 2 / 60;
const MAX_RADIUS_DEG = 0.5;
const MOCK_COUNT = 40;

/** 269.452, 4.693 -> "269.452 +4.693", the form VizieR's -c parameter reads reliably. */
export function coneTarget(raDeg, decDeg) {
  const sign = decDeg < 0 ? "-" : "+";
  return `${raDeg} ${sign}${Math.abs(decDeg)}`;
}

/** Cone that covers a square view of this width: half its diagonal, within limits. */
export function radiusForFov(fovDeg) {
  const radius = (fovDeg * Math.SQRT2) / 2;
  return Math.min(MAX_RADIUS_DEG, Math.max(MIN_RADIUS_DEG, radius));
}

/**
 * Synthetic Gaia-like stars spread over the cone, for working without VizieR.
 * The same position always gives the same stars. Never real measurements.
 */
export function mockGaiaSources(raDeg, decDeg, fovDeg, count = MOCK_COUNT) {
  const radius = radiusForFov(fovDeg);
  let seed =
    (Math.floor(Math.abs(raDeg * 1000 + decDeg * 7919)) % 2147483646) + 1;
  const random = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  const cosDec = Math.max(Math.cos((decDeg * Math.PI) / 180), 0.01);

  return Array.from({ length: count }, (_, index) => {
    // sqrt keeps the stars evenly spread over the disc instead of bunched at the centre
    const distance = radius * Math.sqrt(random());
    const angle = 2 * Math.PI * random();
    return {
      id: `synthetic-${index + 1}`,
      raDeg: (raDeg + (distance * Math.cos(angle)) / cosDec + 360) % 360,
      decDeg: Math.max(-90, Math.min(90, decDeg + distance * Math.sin(angle))),
      gmag: Number((12 + 8 * random()).toFixed(2)),
    };
  });
}

/**
 * Replaces the overlay with Gaia sources around a position.
 * onStatus gets { state: "loading" | "ok" | "empty" | "slow" | "error" | "off",
 * count?, truncated?, synthetic? }. A newer request drops the answer of an older one.
 */
export function createGaiaLoader(
  A,
  aladin,
  { color, onStatus, setTimer = setTimeout },
) {
  let current = null;
  let request = 0;

  const style = {
    color,
    hoverColor: "#ffffff",
    sourceSize: 12,
    shape: "circle",
    onClick: "showPopup",
  };

  function replace(catalog) {
    if (current) aladin.removeOverlay(current);
    current = catalog;
    if (catalog) aladin.addCatalog(catalog);
  }

  function loadMock({ raDeg, decDeg, fovDeg }) {
    const stars = mockGaiaSources(raDeg, decDeg, fovDeg);
    const catalog = A.catalog({ ...style, name: "Gaia DR3 (synthetic)" });
    replace(catalog);
    catalog.addSources(
      stars.map((star) =>
        A.source(star.raDeg, star.decDeg, {
          Source: star.id,
          Gmag: star.gmag,
          note: "synthetic, not a Gaia measurement",
        }),
      ),
    );
    onStatus({
      state: "ok",
      count: stars.length,
      truncated: false,
      synthetic: true,
    });
    return catalog;
  }

  function loadVizier({ raDeg, decDeg, fovDeg }, id) {
    onStatus({ state: "loading" });
    const timer = setTimer(() => {
      if (id === request) onStatus({ state: "slow" });
    }, GAIA_TIMEOUT_MS);

    const catalog = A.catalogFromVizieR(
      GAIA_CATALOG,
      coneTarget(raDeg, decDeg),
      radiusForFov(fovDeg),
      { ...style, name: "Gaia DR3", limit: GAIA_LIMIT },
      (loaded) => {
        clearTimeout(timer);
        if (id !== request) return;
        const count = loaded.getSources().length;
        onStatus({
          state: count ? "ok" : "empty",
          count,
          truncated: count >= GAIA_LIMIT,
        });
      },
      () => {
        clearTimeout(timer);
        if (id === request) onStatus({ state: "error" });
      },
    );
    replace(catalog);
    return catalog;
  }

  /** source: "vizier" (default) or "mock". Returns the new catalog. */
  function load(view, { source = "vizier" } = {}) {
    const id = ++request;
    return source === "mock" ? loadMock(view) : loadVizier(view, id);
  }

  function clear() {
    request++;
    replace(null);
    onStatus({ state: "off" });
  }

  return { load, clear };
}
