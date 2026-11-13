import { useEffect, useRef, useState } from "react";
import A from "aladin-lite";
import "./skymap.css";
import { GAIA_LIMIT, coneTarget, createGaiaLoader } from "./gaia.js";

function statusText(status) {
  switch (status.state) {
    case "loading":
      return "Loading Gaia DR3 from VizieR…";
    case "ok":
      if (status.synthetic) {
        return `${status.count} synthetic Gaia-like stars (offline demo, not real measurements).`;
      }
      return status.truncated
        ? `Showing the first ${GAIA_LIMIT} Gaia sources. Zoom in and reload for the rest.`
        : `${status.count} Gaia sources in this view.`;
    case "empty":
      return "No Gaia sources here. Try a wider view.";
    case "slow":
      return "VizieR is taking too long, so Gaia sources are not shown yet.";
    case "error":
      return "Could not reach VizieR, so Gaia sources are not shown.";
    case "off":
      return "Gaia layer is off.";
    default:
      return "";
  }
}

const readMarkerColor = () =>
  getComputedStyle(document.documentElement)
    .getPropertyValue("--color-marker")
    .trim();

/**
 * Aladin Lite sky map that jumps to the given position whenever it changes.
 * raDeg, decDeg: centre in ICRS degrees. fovDeg: width of the view in degrees.
 * gaia: "vizier" (real Gaia DR3), "mock" (synthetic stars, works offline) or "off".
 * Needs shared/design-tokens.css on the page.
 */
export function SkyMap({
  raDeg,
  decDeg,
  fovDeg = 10 / 60,
  gaia = "vizier",
  survey = "P/2MASS/color",
  onSwitchGaia,
}) {
  const mapRef = useRef(null);
  const view = useRef(null);
  const [ready, setReady] = useState(false);
  const [mapError, setMapError] = useState(false);
  const [status, setStatus] = useState({ state: "idle" });
  const [center, setCenter] = useState("");

  // Aladin is created once; the next effect moves it.
  useEffect(() => {
    let cancelled = false;
    const el = mapRef.current;
    A.init
      .then(() => {
        if (cancelled) return;
        const aladin = A.aladin(el, {
          survey,
          fov: fovDeg,
          target: coneTarget(raDeg, decDeg),
          cooFrame: "ICRSd",
        });
        const loader = createGaiaLoader(A, aladin, {
          color: readMarkerColor(),
          onStatus: setStatus,
        });
        view.current = { aladin, loader };
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) setMapError(true);
      });
    return () => {
      cancelled = true;
      el.replaceChildren();
    };
    // Created once with the first props; later props are applied below.
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!ready) return;
    const { aladin, loader } = view.current;
    aladin.gotoRaDec(raDeg, decDeg);
    aladin.setFoV(fovDeg);
    const [ra, dec] = aladin.getRaDec();
    setCenter(`${ra.toFixed(5)} ${dec.toFixed(5)}`);
    if (gaia === "off") loader.clear();
    else loader.load({ raDeg, decDeg, fovDeg }, { source: gaia });
  }, [ready, raDeg, decDeg, fovDeg, gaia]);

  function reloadView() {
    const { aladin, loader } = view.current;
    const [ra, dec] = aladin.getRaDec();
    loader.load(
      { raDeg: ra, decDeg: dec, fovDeg: aladin.getFov()[0] },
      { source: gaia },
    );
  }

  const failed = status.state === "error" || status.state === "slow";

  return (
    <div className="skymap" data-center={center}>
      <div ref={mapRef} className="skymap__map" aria-label="Sky map" />
      {mapError && (
        <p role="alert" className="skymap__message skymap__message--danger">
          The sky map needs WebGL 2, which this browser did not provide.
        </p>
      )}
      <div className="skymap__bar">
        <p
          role="status"
          className={
            failed
              ? "skymap__message skymap__message--warning"
              : "skymap__message"
          }
          data-gaia-state={status.state}
        >
          {statusText(status)}
        </p>
        {status.state === "error" && gaia === "vizier" && onSwitchGaia ? (
          <button
            type="button"
            className="skymap__button"
            onClick={() => onSwitchGaia("mock")}
          >
            Use offline stars
          </button>
        ) : gaia !== "off" && (
          <button
            type="button"
            className="skymap__button"
            disabled={!ready}
            onClick={reloadView}
          >
            Load Gaia for this view
          </button>
        )}
      </div>
    </div>
  );
}
