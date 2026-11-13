import { StrictMode, useState } from "react";
import { createRoot } from "react-dom/client";
import "../../../../shared/design-tokens.css";
import "./style.css";
import { SkyMap } from "../../../../shared/skymap/SkyMap.jsx";
import { locate } from "../../../duy-hoang/coords/resolve.js";
import { formatDec, formatRa } from "../../../duy-hoang/coords/format.js";
import { TARGETS } from "../../../duy-hoang/coords/targets.js";

const FOV_ARCMIN = [2, 5, 10];
const GAIA_CHOICES = [
  { value: "mock", label: "Synthetic (offline)" },
  { value: "vizier", label: "VizieR (live)" },
  { value: "off", label: "Off" },
];

const start = TARGETS[0];

function App() {
  const [input, setInput] = useState(start.name);
  const [position, setPosition] = useState({
    raDeg: start.raDeg,
    decDeg: start.decDeg,
    name: start.name,
  });
  const [fovArcmin, setFovArcmin] = useState(10);
  const [gaia, setGaia] = useState("mock");
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  async function go(query) {
    setInput(query);
    setBusy(true);
    setError(null);
    try {
      const found = await locate(query);
      setPosition({
        raDeg: found.raDeg,
        decDeg: found.decDeg,
        name: found.name,
      });
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <section className="map-column">
        <SkyMap
          raDeg={position.raDeg}
          decDeg={position.decDeg}
          fovDeg={fovArcmin / 60}
          gaia={gaia}
        />
      </section>

      <aside className="panel">
        <h1 className="title">Sky map + Gaia DR3</h1>

        <form
          className="form"
          onSubmit={(event) => {
            event.preventDefault();
            go(input);
          }}
        >
          <label htmlFor="position" className="heading">
            Coordinates or object name
          </label>
          <div className="row">
            <input
              id="position"
              className="input"
              value={input}
              onChange={(event) => setInput(event.target.value)}
              aria-invalid={error ? "true" : "false"}
              aria-describedby="position-help"
            />
            <button type="submit" className="button" disabled={busy}>
              Go
            </button>
          </div>
          <p
            id="position-help"
            className={error ? "message message-danger" : "note"}
          >
            {error ??
              "Decimal degrees, h/m/s d/m/s or an object name. The map jumps there."}
          </p>
        </form>

        <p className="position" data-position>
          {position.name ? `${position.name} · ` : ""}RA{" "}
          {formatRa(position.raDeg)} · Dec {formatDec(position.decDeg)}
        </p>

        <h2 className="heading">Test targets</h2>
        <div className="targets">
          {TARGETS.map((target) => (
            <button
              key={target.id}
              type="button"
              aria-pressed={target.name === position.name}
              className="button"
              onClick={() => go(target.name)}
            >
              {target.name}
            </button>
          ))}
        </div>

        <div className="row">
          <label className="field">
            Field of view
            <select
              value={fovArcmin}
              onChange={(event) => setFovArcmin(Number(event.target.value))}
            >
              {FOV_ARCMIN.map((value) => (
                <option key={value} value={value}>
                  {value}′
                </option>
              ))}
            </select>
          </label>
        </div>

        <fieldset className="choices">
          <legend className="heading">Gaia DR3 layer</legend>
          {GAIA_CHOICES.map((choice) => (
            <label key={choice.value} className="check">
              <input
                type="radio"
                name="gaia"
                value={choice.value}
                checked={gaia === choice.value}
                onChange={() => setGaia(choice.value)}
              />
              {choice.label}
            </label>
          ))}
        </fieldset>

        <p className="note">
          Synthetic stars are made up so the map can be tried offline. Live Gaia
          positions are for 2016 and the background is 2MASS, from around 2000,
          so a fast mover such as Barnard&apos;s Star sits away from its marker.
          The map and Gaia both come from CDS in France: if the map stays grey,
          CDS cannot be reached from this network.
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
