import { StrictMode, useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import A from "aladin-lite";
import "../../../../shared/design-tokens.css";
import "./style.css";
import { TARGETS } from "../../../duy-hoang/coords/targets.js";
import { GAIA_LIMIT, coneTarget, createGaiaLoader } from "./gaia.js";

const START_FOV_DEG = 10 / 60;

function statusText(status) {
  switch (status.state) {
    case "loading":
      return "Loading Gaia DR3 from VizieR…";
    case "ok":
      return status.truncated
        ? `Showing the first ${GAIA_LIMIT} Gaia sources. Zoom in and reload for the rest.`
        : `${status.count} Gaia sources in this view.`;
    case "empty":
      return "No Gaia sources here. Try a wider view.";
    case "slow":
      return "VizieR is taking too long, so Gaia sources are not shown yet.";
    case "error":
      return "Could not reach VizieR, so Gaia sources are not shown.";
    default:
      return "";
  }
}

function App() {
  const mapRef = useRef(null);
  const view = useRef({ aladin: null, loader: null, catalog: null });
  const [ready, setReady] = useState(false);
  const [mapError, setMapError] = useState(false);
  const [status, setStatus] = useState({ state: "idle" });
  const [showGaia, setShowGaia] = useState(true);
  const [targetId, setTargetId] = useState(TARGETS[0].id);

  useEffect(() => {
    let cancelled = false;
    const el = mapRef.current;
    A.init
      .then(() => {
        if (cancelled) return;
        const start = TARGETS[0];
        const aladin = A.aladin(el, {
          survey: "P/2MASS/color",
          fov: START_FOV_DEG,
          target: coneTarget(start.raDeg, start.decDeg),
          cooFrame: "ICRSd",
        });
        const color = getComputedStyle(document.documentElement)
          .getPropertyValue("--color-marker")
          .trim();
        const loader = createGaiaLoader(A, aladin, {
          color,
          onStatus: setStatus,
        });
        view.current = {
          aladin,
          loader,
          catalog: loader.load({
            raDeg: start.raDeg,
            decDeg: start.decDeg,
            fovDeg: START_FOV_DEG,
          }),
        };
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) setMapError(true);
      });
    return () => {
      cancelled = true;
      el.replaceChildren();
    };
  }, []);

  function load(position) {
    const catalog = view.current.loader.load(position);
    view.current.catalog = catalog;
    if (!showGaia) catalog.hide();
  }

  function flyTo(target) {
    setTargetId(target.id);
    const { aladin } = view.current;
    aladin.gotoRaDec(target.raDeg, target.decDeg);
    load({
      raDeg: target.raDeg,
      decDeg: target.decDeg,
      fovDeg: aladin.getFov()[0],
    });
  }

  function reloadView() {
    const { aladin } = view.current;
    const [raDeg, decDeg] = aladin.getRaDec();
    load({ raDeg, decDeg, fovDeg: aladin.getFov()[0] });
  }

  function toggleGaia(event) {
    const { checked } = event.target;
    setShowGaia(checked);
    if (checked) view.current.catalog?.show();
    else view.current.catalog?.hide();
  }

  const failed = status.state === "error" || status.state === "slow";

  return (
    <main className="page">
      <section className="map-column">
        <div ref={mapRef} className="map" aria-label="Sky map" />
        {mapError && (
          <p role="alert" className="message message-danger">
            The sky map needs WebGL 2, which this browser did not provide.
          </p>
        )}
      </section>

      <aside className="panel">
        <h1 className="title">Sky map + Gaia DR3</h1>

        <h2 className="heading">Test targets</h2>
        <div className="targets">
          {TARGETS.map((target) => (
            <button
              key={target.id}
              type="button"
              disabled={!ready}
              aria-pressed={target.id === targetId}
              className="button"
              onClick={() => flyTo(target)}
            >
              {target.name}
            </button>
          ))}
        </div>

        <h2 className="heading">Gaia overlay</h2>
        <label className="check">
          <input
            type="checkbox"
            checked={showGaia}
            disabled={!ready}
            onChange={toggleGaia}
          />
          Show Gaia DR3 sources
        </label>
        <button
          type="button"
          className="button"
          disabled={!ready}
          onClick={reloadView}
        >
          Load Gaia for this view
        </button>
        <p
          role="status"
          className={failed ? "message message-warning" : "message"}
          data-gaia-state={status.state}
        >
          {statusText(status)}
        </p>

        <p className="note">
          Gaia positions are for 2016 and the background is 2MASS, from around
          2000. A fast mover such as Barnard&apos;s Star sits away from its
          marker, and that offset is real.
        </p>
        <p className="note">
          The sky map and Gaia both come from CDS in France. If the map stays
          grey, CDS cannot be reached from this network.
        </p>
      </aside>
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
