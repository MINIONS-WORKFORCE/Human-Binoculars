// Gaia DR3 overlay for Aladin Lite. Sources come from VizieR through A.catalogFromVizieR.
// Gaia positions are for epoch 2016.0, so a fast mover sits away from where it appears
// in images taken at another date. That offset is real, not a bug.

export const GAIA_CATALOG = "I/355/gaiadr3";
export const GAIA_LIMIT = 5000; // Aladin's default is 100000, too heavy for a demo
export const GAIA_TIMEOUT_MS = 30000; // same threshold as "IRSA is slow" in the risk table

const MIN_RADIUS_DEG = 2 / 60;
const MAX_RADIUS_DEG = 0.5;

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
 * Replaces the overlay with Gaia sources around a position.
 * onStatus gets { state: "loading" | "ok" | "empty" | "slow" | "error", count?, truncated? }.
 * Returns the loader for the next call, so a newer request drops an older one.
 */
export function createGaiaLoader(
  A,
  aladin,
  { color, onStatus, setTimer = setTimeout },
) {
  let current = null;
  let request = 0;

  function load({ raDeg, decDeg, fovDeg }) {
    const id = ++request;
    if (current) aladin.removeOverlay(current);
    onStatus({ state: "loading" });

    const timer = setTimer(() => {
      if (id === request) onStatus({ state: "slow" });
    }, GAIA_TIMEOUT_MS);

    const catalog = A.catalogFromVizieR(
      GAIA_CATALOG,
      coneTarget(raDeg, decDeg),
      radiusForFov(fovDeg),
      {
        name: "Gaia DR3",
        limit: GAIA_LIMIT,
        color,
        hoverColor: "#ffffff",
        sourceSize: 12,
        shape: "circle",
        onClick: "showPopup",
      },
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

    current = catalog;
    aladin.addCatalog(catalog);
    return catalog;
  }

  return { load };
}
