// Page: type a target (name or coordinates), then see its SPHEREx frames blink
// (/api/frames), where it sits on the sky with Gaia DR3 (Aladin Lite), and its
// light curve and spectrum (/api/photometry).
import {
  lazy,
  Suspense,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { api, friendlyMessage, ApiError, type Frames } from "./api";
import { apiBase, useMock } from "./config";
import { BlinkViewer } from "./blink/BlinkViewer";
import { CoordinatePreview, type Lookup } from "./coords/CoordinatePreview";
import { formatDec, formatRa } from "./coords/format";
import { locate, previewInput, type Location } from "./coords/locate";
import { CoordError } from "./coords/parse";
import { DETECTORS, TARGET_PRESETS } from "./targets";

type State =
  | { status: "loading" }
  | { status: "error"; message: string; code: string }
  | { status: "ready"; data: Frames };

interface Request {
  ra: number;
  dec: number;
  /** Only known targets have one; without it the API sends no predicted_px. */
  targetKey?: string;
  detector: number;
}

// Plotly and Aladin Lite are large, so their panels load after the viewer is usable.
const PhotometryPanel = lazy(() =>
  import("./science/PhotometryPanel").then((m) => ({
    default: m.PhotometryPanel,
  })),
);
const SkyPanel = lazy(() =>
  import("./science/SkyPanel").then((m) => ({ default: m.SkyPanel })),
);

const FIRST = TARGET_PRESETS[0];

/** Map width in degrees: twice the frames' footprint for context, never under 6'. */
const MIN_MAP_FOV_DEG = 0.1;
function mapFov(
  grid: Pick<Frames["grid"], "width" | "pixscale_arcsec"> | null,
) {
  if (!grid) return MIN_MAP_FOV_DEG;
  const footprintDeg = (grid.width * grid.pixscale_arcsec) / 3600;
  return Math.max(MIN_MAP_FOV_DEG, 2 * footprintDeg);
}

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
    return {
      status: "error",
      message: friendlyMessage(error),
      code: error instanceof ApiError ? error.code : "UNKNOWN",
    };
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

      <div className="workspace">
        <section aria-label="Blink viewer">
          {state.status === "loading" && (
            <p className="muted" role="status">
              Loading frames…
            </p>
          )}
          {state.status === "error" && (
            <p className="error" role="alert">
              {state.message} <code>{state.code}</code>
            </p>
          )}
          {state.status === "ready" && <FrameSummary data={state.data} />}
        </section>
        <Suspense fallback={<PanelLoading>Loading sky map…</PanelLoading>}>
          <SkyPanel
            ra={request.ra}
            dec={request.dec}
            fovDeg={mapFov(state.status === "ready" ? state.data.grid : null)}
          />
        </Suspense>
      </div>

      <Suspense fallback={<PanelLoading>Loading photometry…</PanelLoading>}>
        <PhotometryPanel
          ra={request.ra}
          dec={request.dec}
          targetKey={request.targetKey}
        />
      </Suspense>
    </main>
  );
}

function PanelLoading({ children }: { children: string }) {
  return (
    <p className="muted" role="status">
      {children}
    </p>
  );
}

function FrameSummary({ data }: { data: Frames }) {
  const { grid, target } = data;
  return (
    <>
      <p className="summary" data-testid="frame-summary">
        <strong>{data.frames.length} frames</strong> ·{" "}
        {target.name ?? "custom position"} · RA {formatRa(target.ra)} Dec{" "}
        {formatDec(target.dec)} · detector D{data.detector} · grid {grid.width}×
        {grid.height} at {grid.pixscale_arcsec}″/px
        {data.warnings.length > 0 && (
          <> · warnings: {data.warnings.join(", ")}</>
        )}
      </p>
      <BlinkViewer
        frames={data.frames}
        grid={grid}
        detector={data.detector}
        imageUrl={api.imageUrl}
      />
    </>
  );
}
