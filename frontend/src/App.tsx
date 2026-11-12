// Demo page: type a target (name or coordinates), load /api/frames, blink them.
// Thạch's real page will import BlinkViewer the same way.
import { useEffect, useMemo, useState, type FormEvent } from "react";
import { api, describeError, type ErrorInfo, type Frames } from "./api";
import { apiBase, useMock } from "./config";
import { BlinkViewer } from "./blink/BlinkViewer";
import { CoordinatePreview, type Lookup } from "./coords/CoordinatePreview";
import { formatDec, formatRa } from "./coords/format";
import { locate, previewInput, type Location } from "./coords/locate";
import { CoordError } from "./coords/parse";
import { DETECTORS, TARGET_PRESETS } from "./targets";

type State =
  | { status: "loading" }
  | { status: "error"; error: ErrorInfo }
  | { status: "ready"; data: Frames };

/** After this many seconds the loading line explains that the archive can be slow. */
const SLOW_AFTER_S = 3;

interface Request {
  ra: number;
  dec: number;
  /** Only known targets have one; without it the API sends no predicted_px. */
  targetKey?: string;
  detector: number;
}

const FIRST = TARGET_PRESETS[0];

function requestFor(location: Location, detector: number): Request {
  return {
    ra: location.raDeg,
    dec: location.decDeg,
    targetKey:
      location.kind === "name" ? (location.targetKey ?? undefined) : undefined,
    detector,
  };
}

async function fetchFrames(request: Request): Promise<State> {
  try {
    return { status: "ready", data: await api.frames(request) };
  } catch (error) {
    return { status: "error", error: describeError(error) };
  }
}

export default function App() {
  const [text, setText] = useState(FIRST.name);
  const [detector, setDetector] = useState(6);
  // A name lookup belongs to the text it was made for; typing again hides it.
  const [lookup, setLookup] = useState<{ input: string; result: Lookup }>({
    input: "",
    result: { status: "idle" },
  });
  const [request, setRequest] = useState<Request>({
    ra: FIRST.ra,
    dec: FIRST.dec,
    targetKey: FIRST.key,
    detector: 6,
  });
  const [state, setState] = useState<State>({ status: "loading" });

  const preview = useMemo(() => previewInput(text), [text]);
  const currentLookup: Lookup =
    lookup.input === text ? lookup.result : { status: "idle" };

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
  // A copy is a new object, so the effect above sends the same request again.
  const reload = () => load({ ...request });

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const input = text;
    if (preview.status === "needs-lookup") {
      setLookup({ input, result: { status: "looking" } });
    }
    try {
      const location = await locate(input, api.resolve);
      setLookup({ input, result: { status: "found", location } });
      load(requestFor(location, detector));
    } catch (error) {
      if (!(error instanceof CoordError)) throw error;
      setLookup({ input, result: { status: "error", error } });
    }
  }

  const invalid =
    preview.status === "invalid" || currentLookup.status === "error";

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

      <form className="controls" onSubmit={onSubmit}>
        <div className="target-field">
          <label htmlFor="target">Target</label>
          <input
            id="target"
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Barnard's Star  or  269.4521 4.6934"
            autoComplete="off"
            spellCheck={false}
            aria-describedby="target-hint"
            aria-invalid={invalid}
          />
          <p id="target-hint" className="target-hint">
            A name, or coordinates as decimal degrees (
            <code>269.4521 4.6934</code>) or hours / degrees (
            <code>17h57m48.5s +04d41m36s</code>).
          </p>
        </div>
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
        <button type="submit" disabled={currentLookup.status === "looking"}>
          Load frames
        </button>

        <CoordinatePreview preview={preview} lookup={currentLookup} />

        <div className="presets" role="group" aria-label="Challenge targets">
          {TARGET_PRESETS.map((t) => (
            <button
              key={t.key}
              type="button"
              className="secondary chip"
              onClick={() => {
                setText(t.name);
                load({ ra: t.ra, dec: t.dec, targetKey: t.key, detector });
              }}
            >
              {t.name}
            </button>
          ))}
        </div>
      </form>

      <section>
        {state.status === "loading" && <LoadingFrames />}
        {state.status === "error" && (
          <FramesError error={state.error} onRetry={reload} />
        )}
        {state.status === "ready" && (
          <FrameSummary data={state.data} onReload={reload} />
        )}
      </section>
    </main>
  );
}

/** "Loading frames…", then a seconds counter: a live IRSA query can take 2 minutes. */
function LoadingFrames() {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    const started = performance.now();
    const id = setInterval(
      () => setSeconds(Math.floor((performance.now() - started) / 1000)),
      1000,
    );
    return () => clearInterval(id);
  }, []);
  return (
    <p className="muted loading" role="status" data-testid="frames-loading">
      <span className="spinner" aria-hidden="true" />
      Loading frames…
      {seconds >= SLOW_AFTER_S && (
        <> {seconds} s. The NASA archive can take up to 2 minutes.</>
      )}
    </p>
  );
}

function FramesError({
  error,
  onRetry,
}: {
  error: ErrorInfo;
  onRetry: () => void;
}) {
  return (
    <div className="error" role="alert" data-testid="frames-error">
      <p>
        {error.message} <code>{error.code}</code>
      </p>
      {error.retry && (
        <button type="button" className="secondary" onClick={onRetry}>
          Try again
        </button>
      )}
    </div>
  );
}

function FrameSummary({
  data,
  onReload,
}: {
  data: Frames;
  onReload: () => void;
}) {
  const { grid, target } = data;
  return (
    <>
      <p className="summary" data-testid="frame-summary">
        <strong>
          {data.frames.length} {data.frames.length === 1 ? "frame" : "frames"}
        </strong>{" "}
        · {target.name ?? "custom position"} · RA {formatRa(target.ra)} Dec{" "}
        {formatDec(target.dec)} · detector D{data.detector} · grid {grid.width}×
        {grid.height} at {grid.pixscale_arcsec}″/px
        {data.warnings.length > 0 && (
          <> · warnings: {data.warnings.join(", ")}</>
        )}
      </p>
      {data.frames.length === 0 ? (
        // The contract's answer when images exist but every one was filtered out.
        <p className="muted" role="status" data-testid="frames-empty">
          No frames are left for these settings. Try another detector.
        </p>
      ) : (
        <BlinkViewer
          frames={data.frames}
          grid={grid}
          detector={data.detector}
          imageUrl={api.imageUrl}
          onReload={onReload}
        />
      )}
    </>
  );
}
