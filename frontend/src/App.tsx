// Page: type a target (name or coordinates), then see its SPHEREx frames blink
// (/api/frames), where it sits on the sky with Gaia DR3 (Aladin Lite), and its
// light curve and spectrum (/api/photometry).
import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
  type FormEvent,
} from "react";
import { api, describeError, type ErrorInfo, type Frames } from "./api";
import { apiBase, useMock } from "./config";
import { BlinkViewer, type FovRequest } from "./blink/BlinkViewer";
import { CoordinatePreview, type Lookup } from "./coords/CoordinatePreview";
import { formatDec, formatRa } from "./coords/format";
import { locate, previewInput, type Location } from "./coords/locate";
import { CoordError } from "./coords/parse";
import { DETECTORS, TARGET_PRESETS, findPresetForTarget } from "./targets";
import { describeWarning } from "./warnings";
import { Intro } from "./Intro";
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

/**
 * The API is asked once per target and detector, always for the widest field of
 * view. Choosing a smaller field only zooms the viewer in the browser, so it is
 * instant and never waits for the server to render the frames again.
 */
const FETCH_FOV: Fov = 10;
const FETCH_SIZE = fovToSize(FETCH_FOV);

/** The Field of view menu entry for what the viewer shows now. */
function fovChoice(shown: { arcmin: number | undefined; fitted: boolean }) {
  if (shown.fitted) return String(FETCH_FOV);
  const match = FOV_OPTIONS.find(
    (option) =>
      shown.arcmin !== undefined && Math.abs(shown.arcmin - option) < 0.35,
  );
  return match === undefined ? "custom" : String(match);
}

/** Map width in degrees: twice the frames' footprint for context, never under 6'. */
const MIN_MAP_FOV_DEG = 0.1;
function mapFov(
  grid: Pick<Frames["grid"], "width" | "pixscale_arcsec"> | null,
) {
  if (!grid) return MIN_MAP_FOV_DEG;
  const footprintDeg = (grid.width * grid.pixscale_arcsec) / 3600;
  return Math.max(MIN_MAP_FOV_DEG, 2 * footprintDeg);
}

function requestFor(location: Location, detector: number, q: string): Request {
  return {
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
    return {
      status: "ready",
      data: await api.frames({ ...request, size: FETCH_SIZE }),
    };
  } catch (error) {
    return { status: "error", error: describeError(error) };
  }
}

export default function App() {
  // The URL can name the view to open: ?q=<target text>&fov=<arcmin>&det=D<n>.
  const [fromUrl] = useState(() => parseUrlState(window.location.search));
  const [text, setText] = useState(fromUrl.q ?? FIRST.name);
  const [detector, setDetector] = useState(fromUrl.detector ?? 6);
  // The field of view picked last (kept in the URL), the request the viewer zooms
  // to, and what it shows now (after + / −, wheel or pinch it may differ).
  const [fov, setFov] = useState<Fov | null>(fromUrl.fov);
  const [fovRequest, setFovRequest] = useState<FovRequest>({
    arcmin: fromUrl.fov,
  });
  const [shownFov, setShownFov] = useState<{
    arcmin: number | undefined;
    fitted: boolean;
  }>({ arcmin: undefined, fitted: fromUrl.fov === null });
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
      fov,
      detector: request.detector,
    });
    if (search !== window.location.search) {
      window.history.replaceState(
        null,
        "",
        `${window.location.pathname}${search}`,
      );
    }
  }, [request, fov]);

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
        load(requestFor(location, detector, input));
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
      load(requestFor(location, detector, input));
    } catch (error) {
      if (!(error instanceof CoordError)) throw error;
      setLookup({ input, result: { status: "error", error } });
    }
  }

  const invalid =
    preview.status === "invalid" || currentLookup.status === "error";

  const onViewChange = useCallback(
    (arcmin: number | undefined, fitted: boolean) =>
      setShownFov({ arcmin, fitted }),
    [],
  );

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

      <Intro />

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
            value={fovChoice(shownFov)}
            onChange={(e) => {
              // Zooms the frames already loaded: no new request.
              const next = Number(e.target.value) as Fov;
              setFov(next === FETCH_FOV ? null : next);
              setFovRequest({ arcmin: next === FETCH_FOV ? null : next });
            }}
          >
            {[...FOV_OPTIONS].reverse().map((option) => (
              <option key={option} value={option}>
                {option === FETCH_FOV ? "Whole image" : `${option}′`}
              </option>
            ))}
            <option value="custom" disabled hidden>
              Custom zoom
            </option>
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
            <FrameSummary
              data={state.data}
              onReload={reload}
              fov={fovRequest}
              onViewChange={onViewChange}
            />
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
  fov,
  onViewChange,
}: {
  data: Frames;
  onReload: () => void;
  fov: FovRequest;
  onViewChange: (arcmin: number | undefined, fitted: boolean) => void;
}) {
  const { grid, target } = data;
  const preset = findPresetForTarget(target);

  return (
    <>
      <p className="summary" data-testid="frame-summary">
        <strong>
          {data.frames.length} {data.frames.length === 1 ? "frame" : "frames"}
        </strong>{" "}
        · {target.name ?? "custom position"} · RA {formatRa(target.ra)} Dec{" "}
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
          fov={fov}
          onViewChange={onViewChange}
          onReload={onReload}
        />
      )}
      {preset && (
        <section
          className="target-conclusion-card"
          data-testid="target-conclusion"
          aria-label="About this target"
        >
          <header className="target-conclusion-header">
            <span className="badge badge-conclusion">About this target</span>
            <strong className="target-conclusion-name">{preset.name}</strong>
            <span className="target-conclusion-type">
              ({preset.objectType})
            </span>
          </header>
          <p className="target-conclusion-note">
            What astronomers already know, and what to look for. It comes from
            published studies, not from the frames above.
          </p>
          <p className="target-conclusion-text">{preset.conclusion}</p>
        </section>
      )}
    </>
  );
}
