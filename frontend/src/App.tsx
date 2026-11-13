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
import { api, describeError, type ErrorInfo, type Frames } from "./api";
import { apiBase, useMock } from "./config";
import { BlinkViewer } from "./blink/BlinkViewer";
import { CoordinatePreview, type Lookup } from "./coords/CoordinatePreview";
import { formatDec, formatRa } from "./coords/format";
import { locate, previewInput, type Location } from "./coords/locate";
import { CoordError } from "./coords/parse";
import { DETECTORS, TARGET_PRESETS, findPresetForTarget } from "./targets";
import { describeWarning } from "./warnings";
import {
  FOV_OPTIONS,
  buildSearch,
  fovToSize,
  parseUrlState,
  type Fov,
} from "./urlState";

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
  /** Cutout width in arcminutes; null means the viewer default. */
  fov: Fov | null;
  /** The text typed in the target field, kept in the URL. */
  q: string;
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
const DEFAULT_FOV_ARCMIN = 18;

/** Map width in degrees: twice the frames' footprint for context, never under 6'. */
const MIN_MAP_FOV_DEG = 0.1;
function mapFov(
  grid: Pick<Frames["grid"], "width" | "pixscale_arcsec"> | null,
) {
  if (!grid) return MIN_MAP_FOV_DEG;
  const footprintDeg = (grid.width * grid.pixscale_arcsec) / 3600;
  return Math.max(MIN_MAP_FOV_DEG, 2 * footprintDeg);
}

function requestFor(
  location: Location,
  detector: number,
  fov: Fov | null,
  q: string,
): Request {
  return {
    fov,
    q,
    ra: location.raDeg,
    dec: location.decDeg,
    targetKey:
      location.kind === "name" ? (location.targetKey ?? undefined) : undefined,
    detector,
  };
}

async function fetchFrames(request: Request): Promise<State> {
  try {
    const size = request.fov === null ? DEFAULT_FOV_ARCMIN / 60 : fovToSize(request.fov);
    return { status: "ready", data: await api.frames({ ...request, size }) };
  } catch (error) {
    return { status: "error", error: describeError(error) };
  }
}

export default function App() {
  // The URL can name the view to open: ?q=<target text>&fov=<arcmin>&det=D<n>.
  const [fromUrl] = useState(() => parseUrlState(window.location.search));
  const [text, setText] = useState(fromUrl.q ?? FIRST.name);
  const [detector, setDetector] = useState(fromUrl.detector ?? 6);
  const [fov, setFov] = useState<Fov | null>(fromUrl.fov);
  // A name lookup belongs to the text it was made for; typing again hides it.
  const [lookup, setLookup] = useState<{ input: string; result: Lookup }>({
    input: "",
    result: { status: "idle" },
  });
  // null while a q from the URL is still being turned into a position.
  const [request, setRequest] = useState<Request | null>(
    fromUrl.q
      ? null
      : {
          ra: FIRST.ra,
          dec: FIRST.dec,
          targetKey: FIRST.key,
          detector: fromUrl.detector ?? 6,
          fov: fromUrl.fov,
          q: FIRST.name,
        },
  );
  const [state, setState] = useState<State>({ status: "loading" });

  const preview = useMemo(() => previewInput(text), [text]);
  const currentLookup: Lookup =
    lookup.input === text ? lookup.result : { status: "idle" };

  // Only the latest request may update the page; a slower earlier one is ignored.
  useEffect(() => {
    if (!request) return undefined;
    let current = true;
    void fetchFrames(request).then((next) => {
      if (current) setState(next);
    });
    return () => {
      current = false;
    };
  }, [request]);

  // Keep the URL equal to the view on screen, so reloading the page reopens it.
  useEffect(() => {
    if (!request) return;
    const search = buildSearch({
      q: request.q,
      fov: request.fov,
      detector: request.detector,
    });
    if (search !== window.location.search) {
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}${search}`,
      );
    }
  }, [request]);

  const load = (next: Request) => {
    setState({ status: "loading" });
    setRequest(next);
  };
  // A copy is a new object, so the effect above sends the same request again.
  const reload = () => {
    if (request) load({ ...request });
  };

  // First load from a URL that names a target: turn its text into a position.
  useEffect(() => {
    const input = fromUrl.q;
    if (!input) return undefined;
    let current = true;
    locate(input, api.resolve).then(
      (location) => {
        if (!current) return;
        setLookup({ input, result: { status: "found", location } });
        load(requestFor(location, detector, fov, input));
      },
      (error: unknown) => {
        if (!current) return;
        if (!(error instanceof CoordError)) throw error;
        // Say why the link did not work, then open the default target.
        setLookup({ input, result: { status: "error", error } });
        load({
          ra: FIRST.ra,
          dec: FIRST.dec,
          targetKey: FIRST.key,
          detector,
          fov,
          q: FIRST.name,
        });
      },
    );
    return () => {
      current = false;
    };
    // Runs once, with the values the URL gave.
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const input = text;
    if (preview.status === "needs-lookup") {
      setLookup({ input, result: { status: "looking" } });
    }
    try {
      const location = await locate(input, api.resolve);
      setLookup({ input, result: { status: "found", location } });
      load(requestFor(location, detector, fov, input));
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
            onChange={(e) => {
              const next = Number(e.target.value);
              setDetector(next);
              if (request) load({ ...request, detector: next });
            }}
          >
            {DETECTORS.map((d) => (
              <option key={d} value={d}>
                D{d}
              </option>
            ))}
          </select>
        </label>
        <label>
          Field of view
          <select
            value={fov ?? ""}
            onChange={(e) => {
              const next = e.target.value
                ? (Number(e.target.value) as Fov)
                : null;
              setFov(next);
              if (request) load({ ...request, fov: next });
            }}
          >
            <option value="">Default ({DEFAULT_FOV_ARCMIN}′)</option>
            {FOV_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option}′
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
                load({
                  ra: t.ra,
                  dec: t.dec,
                  targetKey: t.key,
                  detector,
                  fov,
                  q: t.name,
                });
              }}
            >
              {t.name}
            </button>
          ))}
        </div>
      </form>

      <div className="workspace">
        <section aria-label="Blink viewer">
          {state.status === "loading" && <LoadingFrames />}
          {state.status === "error" && (
            <FramesError error={state.error} onRetry={reload} />
          )}
          {state.status === "ready" && (
            <FrameSummary data={state.data} onReload={reload} />
          )}
        </section>
        {request && (
          <Suspense fallback={<PanelLoading>Loading sky map…</PanelLoading>}>
            <SkyPanel
              ra={request.ra}
              dec={request.dec}
              fovDeg={mapFov(state.status === "ready" ? state.data.grid : null)}
            />
          </Suspense>
        )}
      </div>

      {request && (
        <Suspense fallback={<PanelLoading>Loading photometry…</PanelLoading>}>
          <PhotometryPanel
            ra={request.ra}
            dec={request.dec}
            targetKey={request.targetKey}
          />
        </Suspense>
      )}
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

/** Show elapsed time while waiting for frames. */
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
        <> {seconds} s elapsed. Waiting for the NASA archive.</>
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
  const preset = findPresetForTarget(target);

  return (
    <>
      <p className="summary" data-testid="frame-summary">
        <strong>{data.frames.length} frames</strong> ·{" "}
        {target.name ?? "custom position"} · RA {formatRa(target.ra)} Dec{" "}
        {formatDec(target.dec)} · detector D{data.detector} · grid {grid.width}×
        {grid.height} at {grid.pixscale_arcsec}″/px
      </p>
      {data.warnings.length > 0 && (
        <ul className="warnings" data-testid="frame-warnings">
          {data.warnings.map((code) => (
            <li key={code} role="status">
              <strong>Warning:</strong> {describeWarning(code)}{" "}
              <code>{code}</code>
            </li>
          ))}
        </ul>
      )}
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
      {preset && (
        <section
          className="target-conclusion-card"
          data-testid="target-conclusion"
          aria-label="Scientific Conclusion"
        >
          <header className="target-conclusion-header">
            <span className="badge badge-conclusion">
              Scientific Conclusion
            </span>
            <strong className="target-conclusion-name">{preset.name}</strong>
            <span className="target-conclusion-type">
              ({preset.objectType})
            </span>
          </header>
          <p>Background information; the displayed frames have not independently confirmed these claims.</p>
          <p className="target-conclusion-text">{preset.conclusion}</p>
        </section>
      )}
    </>
  );
}
