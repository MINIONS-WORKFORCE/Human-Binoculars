import { StrictMode, useEffect, useMemo, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { BlinkViewer } from "../../blink/BlinkViewer.jsx";
import { releaseFrames } from "../../blink/loadFrames.js";
import { formatDec, formatRa } from "../../coords/format.js";
import { locate } from "../../coords/resolve.js";
import { TARGETS } from "../../coords/targets.js";
import { FOV_CHOICES, readQuery, writeQuery } from "./query.js";
import { SOURCES, sourceById } from "./sources.js";

const EXAMPLES = ["08h55m10.831s-7d14m42.53s", ...TARGETS.map((t) => t.name)];

const SOURCE_LABEL = {
  input: "typed coordinates",
  local: "challenge target table",
  mast: "MAST name lookup",
};

function PositionSummary({ view }) {
  const { position, fov, src } = view;
  return (
    <div style={{ display: "grid", gap: 4, marginBottom: 12 }}>
      <div>
        <strong>{position.name ?? "Typed position"}</strong>
        {position.objectType ? ` · ${position.objectType}` : ""}
      </div>
      <div style={{ fontFamily: "ui-monospace, monospace", fontSize: 14 }}>
        RA {formatRa(position.raDeg)} Dec {formatDec(position.decDeg)} (
        {position.raDeg.toFixed(5)}°, {position.decDeg.toFixed(5)}°)
      </div>
      <div style={{ fontSize: 14, opacity: 0.75 }}>
        From {SOURCE_LABEL[position.source]} · FOV {fov}′ ·{" "}
        {sourceById(src).note}
      </div>
      {position.epoch === 2000 && (
        <div style={{ fontSize: 14, color: "#b9770e" }}>
          Position is for the year 2000. Fast-moving stars (Barnard&apos;s Star
          moves ~10″ a year) may be off-centre.
        </div>
      )}
    </div>
  );
}

function App() {
  const initial = useMemo(() => readQuery(window.location.search), []);
  const [input, setInput] = useState(initial.q);
  const [fov, setFov] = useState(initial.fov);
  const [src, setSrc] = useState(initial.src);
  const [frames, setFrames] = useState([]);
  const [view, setView] = useState(null); // what the frames on screen show
  const [status, setStatus] = useState({ state: "idle" });
  const pending = useRef(null);

  // Free old bitmaps once the new ones are on screen.
  useEffect(() => () => releaseFrames(frames), [frames]);

  async function search(query) {
    pending.current?.abort(); // a newer search wins
    const controller = new AbortController();
    pending.current = controller;
    setStatus({ state: "loading" });

    try {
      const position = await locate(query.q);
      if (controller.signal.aborted) return;
      const source = sourceById(query.src);
      const loaded = await source.load(
        {
          raDeg: position.raDeg,
          decDeg: position.decDeg,
          fovArcmin: query.fov,
        },
        { signal: controller.signal },
      );
      if (controller.signal.aborted) {
        releaseFrames(loaded);
        return;
      }
      setFrames(loaded);
      setView({ position, fov: query.fov, src: query.src });
      setStatus({ state: "idle" });
      window.history.replaceState(null, "", writeQuery(query));
    } catch (error) {
      if (controller.signal.aborted) return;
      setStatus({
        state: "error",
        code: error.code ?? "LOAD_FAILED",
        message: error.message,
      });
    }
  }

  function run(q = input) {
    setInput(q);
    search({ q, fov, src });
  }

  useEffect(() => {
    if (initial.q) search(initial);
    return () => pending.current?.abort();
  }, [initial]);

  const overlay = useMemo(
    () =>
      view
        ? { label: `FOV ${view.fov}′ · ${sourceById(view.src).label}` }
        : null,
    [view],
  );

  return (
    <main
      style={{
        fontFamily: "system-ui",
        padding: 16,
        maxWidth: 560,
        colorScheme: "light dark",
      }}
    >
      <h1 style={{ fontSize: 24, marginTop: 0 }}>Sky viewer</h1>
      <p style={{ marginTop: 0 }}>
        Enter coordinates or an object name, then watch the images blink.
        Anything that moves or changes brightness between frames is worth a
        closer look.
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault();
          run();
        }}
        style={{ display: "grid", gap: 8 }}
      >
        <div style={{ display: "flex", gap: 8 }}>
          <input
            value={input}
            onChange={(event) => setInput(event.target.value)}
            placeholder={`133.795 -7.245, 08h55m10.831s -7d14m42.53s or "Barnard's Star"`}
            aria-label="Coordinates or object name"
            style={{ flex: 1, minWidth: 0, padding: 8, fontSize: 16 }}
          />
          <button type="submit" style={{ padding: "8px 16px", fontSize: 16 }}>
            Go
          </button>
        </div>
        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <label>
            Field of view{" "}
            <select
              value={fov}
              onChange={(event) => setFov(Number(event.target.value))}
            >
              {FOV_CHOICES.map((choice) => (
                <option key={choice} value={choice}>
                  {choice}′
                </option>
              ))}
            </select>
          </label>
          <label>
            Images{" "}
            <select
              value={src}
              onChange={(event) => setSrc(event.target.value)}
            >
              {SOURCES.map((source) => (
                <option
                  key={source.id}
                  value={source.id}
                  disabled={!source.enabled}
                >
                  {source.label}
                </option>
              ))}
            </select>
          </label>
        </div>
      </form>

      <p style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
        {EXAMPLES.map((example) => (
          <button key={example} type="button" onClick={() => run(example)}>
            {example}
          </button>
        ))}
      </p>

      {status.state === "loading" && <p>Loading…</p>}
      {status.state === "error" && (
        <p role="alert" style={{ color: "#c0392b" }}>
          <code>{status.code}</code> {status.message}
        </p>
      )}

      {view && <PositionSummary view={view} />}
      <BlinkViewer frames={frames} overlay={overlay} />
    </main>
  );
}

createRoot(document.getElementById("root")).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
