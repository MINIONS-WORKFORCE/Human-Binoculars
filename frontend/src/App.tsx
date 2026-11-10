// Temporary page for Issue 18: proves the skeleton can call /api/frames and show
// the frames. The blink viewer (canvas, playback, crosshair) replaces the image grid next.
import { useEffect, useState } from "react";
import { api, friendlyMessage, ApiError, type Frames } from "./api";
import { apiBase, useMock } from "./config";
import { DETECTORS, TARGET_PRESETS } from "./targets";

type State =
  | { status: "loading" }
  | { status: "error"; message: string; code: string }
  | { status: "ready"; data: Frames };

interface Request {
  targetKey: string;
  detector: number;
}

const SCALE = 6;

async function fetchFrames({ targetKey, detector }: Request): Promise<State> {
  // An unknown key is sent as-is, so the page can show the 404 path too.
  const preset = TARGET_PRESETS.find((t) => t.key === targetKey) ?? {
    ra: 269.4521,
    dec: 4.6934,
  };
  try {
    const data = await api.frames({
      ra: preset.ra,
      dec: preset.dec,
      targetKey,
      detector,
    });
    return { status: "ready", data };
  } catch (error) {
    return {
      status: "error",
      message: friendlyMessage(error),
      code: error instanceof ApiError ? error.code : "UNKNOWN",
    };
  }
}

export default function App() {
  const [targetKey, setTargetKey] = useState(TARGET_PRESETS[0].key);
  const [detector, setDetector] = useState(6);
  const [request, setRequest] = useState<Request>({
    targetKey: TARGET_PRESETS[0].key,
    detector: 6,
  });
  const [state, setState] = useState<State>({ status: "loading" });

  // Only the latest request may update the page; a slower earlier one is ignored.
  useEffect(() => {
    let current = true;
    void fetchFrames(request).then((next) => {
      if (current) setState(next);
    });
    return () => {
      current = false;
    };
  }, [request]);

  const load = (next: Request) => {
    setState({ status: "loading" });
    setRequest(next);
  };

  return (
    <main className="page">
      <header className="header">
        <h1>SPHEREx Sky Viewer</h1>
        <span className={useMock ? "badge badge-mock" : "badge"}>
          {useMock
            ? "Mock API · api_samples/"
            : `API · ${apiBase || "same origin"}`}
        </span>
      </header>

      <form
        className="controls"
        onSubmit={(event) => {
          event.preventDefault();
          load({ targetKey, detector });
        }}
      >
        <label>
          Target
          <select
            value={targetKey}
            onChange={(e) => setTargetKey(e.target.value)}
          >
            {TARGET_PRESETS.map((t) => (
              <option key={t.key} value={t.key}>
                {t.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Detector
          <select
            value={detector}
            onChange={(e) => setDetector(Number(e.target.value))}
          >
            {DETECTORS.map((d) => (
              <option key={d} value={d}>
                D{d}
              </option>
            ))}
          </select>
        </label>
        <button type="submit">Load frames</button>
        <button
          type="button"
          className="secondary"
          onClick={() => load({ targetKey: "planet-x", detector })}
        >
          Try an unknown target
        </button>
      </form>

      <section aria-live="polite">
        {state.status === "loading" && <p className="muted">Loading frames…</p>}
        {state.status === "error" && (
          <p className="error" role="alert">
            {state.message} <code>{state.code}</code>
          </p>
        )}
        {state.status === "ready" && <FrameList data={state.data} />}
      </section>
    </main>
  );
}

function FrameList({ data }: { data: Frames }) {
  const { grid } = data;
  return (
    <>
      <p className="summary">
        <strong>{data.frames.length} frames</strong> ·{" "}
        {data.target.name ?? "custom position"} · detector D{data.detector} ·
        grid {grid.width}×{grid.height} at {grid.pixscale_arcsec}″/px
        {data.warnings.length > 0 && (
          <> · warnings: {data.warnings.join(", ")}</>
        )}
      </p>
      <ol className="frames">
        {data.frames.map((frame, index) => (
          <li key={frame.id} className="frame">
            <div className="images">
              <figure>
                <img
                  src={api.imageUrl(frame.png)}
                  width={grid.width * SCALE}
                  height={grid.height * SCALE}
                  alt={`Frame ${index + 1}, ${frame.iso}`}
                />
                <figcaption>Original</figcaption>
              </figure>
              <figure>
                <img
                  src={api.imageUrl(frame.diff_png)}
                  width={grid.width * SCALE}
                  height={grid.height * SCALE}
                  alt={`Difference image for frame ${index + 1}`}
                />
                <figcaption>Difference</figcaption>
              </figure>
            </div>
            <dl>
              <dt>UTC</dt>
              <dd>{frame.iso.replace("T", " ").replace("Z", "")}</dd>
              <dt>Wavelength</dt>
              <dd>{frame.wavelength_um} µm</dd>
              <dt>Predicted px</dt>
              <dd>
                {frame.predicted_px
                  ? `(${frame.predicted_px.join(", ")})`
                  : "none"}
              </dd>
              <dt>Release</dt>
              <dd>
                {frame.release.toUpperCase()} · survey {frame.survey}
              </dd>
            </dl>
          </li>
        ))}
      </ol>
    </>
  );
}
