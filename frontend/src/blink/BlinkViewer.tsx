// <BlinkViewer frames grid /> : the core of the product. Plays SPHEREx frames of one
// sky position in a loop so a moving star visibly jumps. Self-contained: give it the
// frames from /api/frames and it preloads, draws and controls everything.
import {
  useEffect,
  useMemo,
  useReducer,
  useRef,
  type Dispatch,
  type RefObject,
} from "react";
import type { Frame, Frames } from "../api/client";
import { drawCrosshair, drawImage } from "./canvas";
import {
  FPS_MAX,
  FPS_MIN,
  advanceClock,
  initialPlayer,
  playerReducer,
  type PlayerAction,
} from "./player";
import { usePreloadedFrames } from "./usePreloadedFrames";
import { useZoom, type FovRequest } from "./useZoom";
import {
  MIN_SPAN,
  pixelGeometry,
  predictedCentre,
  toCanvas,
  type GridSize,
  type View,
} from "./view";
import "./blink.css";

export type { FovRequest } from "./useZoom";

export interface BlinkViewerProps {
  frames: readonly Frame[];
  /** pixscale_arcsec lets the viewer show and accept a field of view in arcminutes. */
  grid: Pick<Frames["grid"], "width" | "height"> &
    Partial<Pick<Frames["grid"], "pixscale_arcsec">>;
  detector?: number;
  /** Turns a frame's png / diff_png path into a loadable URL. Keep it stable. */
  imageUrl?: (path: string) => string;
  /** Width the canvas fills, in CSS pixels (it shrinks on narrow screens). */
  displaySize?: number;
  /**
   * Field of view to show, centred on the predicted position. Zooming happens in
   * the browser on the frames already loaded. A new object re-applies it.
   */
  fov?: FovRequest;
  /** Reports the field of view on screen (arcminutes) and whether it is the whole image. */
  onViewChange?: (fovArcmin: number | undefined, fitted: boolean) => void;
  /**
   * Asks /api/frames again. Offered when an image fails, usually FRAME_NOT_FOUND
   * after the backend restarted or evicted it (an <img> cannot read the error code).
   */
  onReload?: () => void;
}

const identity = (path: string) => path;

const KEY_ACTIONS = {
  " ": "toggle",
  ArrowRight: "next",
  ArrowLeft: "prev",
} as const;

/**
 * Keys typed into inputs and selects belong to them (a focused slider uses the
 * arrows). A focused button keeps Space for its own click, but the arrows still
 * step frames, so Play followed by → works without moving focus.
 */
function belongsToControl(target: EventTarget | null, key: string) {
  if (!(target instanceof HTMLElement)) return false;
  if (/^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return true;
  return target.tagName === "BUTTON" && key === " ";
}

/** requestAnimationFrame loop with an accumulated clock (no drifting setInterval). */
function usePlaybackLoop(
  playing: boolean,
  fps: number,
  dispatch: Dispatch<PlayerAction>,
) {
  useEffect(() => {
    if (!playing) return undefined;
    let frameId = 0;
    let last = performance.now();
    let elapsed = 0;
    const step = (now: number) => {
      const clock = advanceClock(elapsed, now - last, fps);
      elapsed = clock.elapsed;
      last = now;
      if (clock.tick) dispatch({ type: "tick" });
      frameId = requestAnimationFrame(step);
    };
    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, [playing, fps, dispatch]);
}

/** Draws the `view` window of the image, then the crosshair if it is inside it. */
function useCanvasDrawing(
  canvasRef: RefObject<HTMLCanvasElement | null>,
  image: HTMLImageElement | undefined,
  predictedPx: Frame["predicted_px"] | undefined,
  showCrosshair: boolean,
  view: View,
  pixelSize: number,
) {
  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;
    const size = view.span * pixelSize;
    if (canvas.width !== size) canvas.width = size;
    if (canvas.height !== size) canvas.height = size;

    drawImage(ctx, image, size, size, view);
    const at = predictedPx ? toCanvas(predictedPx, view, pixelSize) : null;
    if (image && showCrosshair && at) {
      const color =
        getComputedStyle(canvas).getPropertyValue("--color-marker").trim() ||
        "#ffc46b";
      drawCrosshair(ctx, at, pixelSize, color);
    }
  }, [canvasRef, image, predictedPx, showCrosshair, view, pixelSize]);
}

/** "5.0′" or, under a minute, "40″". */
function formatFov(arcmin: number): string {
  return arcmin >= 1 ? `${arcmin.toFixed(1)}′` : `${Math.round(arcmin * 60)}″`;
}

function formatUtc(iso: string): string {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return `${date.toISOString().slice(0, 16).replace("T", " ")} UTC`;
}

export function BlinkViewer({
  frames,
  grid,
  detector,
  imageUrl = identity,
  displaySize = 520,
  fov,
  onViewChange,
  onReload,
}: BlinkViewerProps) {
  const preload = usePreloadedFrames(frames, imageUrl);
  const ready = preload.status === "ready";
  const [player, dispatch] = useReducer(playerReducer, 0, initialPlayer);
  const { index, playing, fps, mode, showCrosshair } = player;
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Frames become playable only when every image is decoded; then start the blink.
  useEffect(() => {
    dispatch({ type: "load", count: ready ? frames.length : 0 });
    if (ready) dispatch({ type: "play" });
  }, [ready, frames]);

  usePlaybackLoop(playing, fps, dispatch);

  const frame = frames[index];
  const images = ready ? preload[mode] : [];
  // A stable object, so the zoom listeners are not re-attached on every frame tick.
  const gridSize = useMemo<GridSize>(
    () => ({ width: grid.width, height: grid.height }),
    [grid.width, grid.height],
  );
  const zoom = useZoom({
    canvasRef,
    grid: gridSize,
    pixscaleArcsec: grid.pixscale_arcsec,
    centre: predictedCentre(frames.map((f) => f.predicted_px)),
    fov,
    framesKey: frames,
  });
  const { view } = zoom;
  const { pixelSize, cssWidth } = pixelGeometry(
    view.span,
    displaySize,
    window.devicePixelRatio || 1,
  );
  useCanvasDrawing(
    canvasRef,
    images[index],
    frame?.predicted_px,
    showCrosshair,
    view,
    pixelSize,
  );

  useEffect(() => {
    onViewChange?.(zoom.fovArcmin, zoom.fitted);
  }, [onViewChange, zoom.fovArcmin, zoom.fitted]);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (!(event.key in KEY_ACTIONS)) return;
      if (belongsToControl(event.target, event.key)) return;
      const type = KEY_ACTIONS[event.key as keyof typeof KEY_ACTIONS];
      event.preventDefault();
      dispatch({ type });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const count = ready ? frames.length : 0;
  const disabled = count < 2;
  const hasPrediction = frames.some((f) => f.predicted_px);

  return (
    <section className="blink" aria-label="Blink viewer">
      <p className="blink-hint" data-testid="blink-hint">
        {mode === "diff"
          ? "Difference image: A bright–dark dipole pair may indicate motion, but wavelength, alignment and image quality also affect the result."
          : "The crosshair marks the predicted position, not a confirmed detection."}
      </p>

      <div className="blink-stage" style={{ maxWidth: cssWidth }}>
        <canvas
          ref={canvasRef}
          className={zoom.fitted ? "blink-canvas" : "blink-canvas is-zoomed"}
          role="img"
          aria-label={
            frame && ready
              ? `${mode === "diff" ? "Difference image" : "Image"}, frame ${index + 1} of ${count}, ${formatUtc(frame.iso)}`
              : "Frames are loading"
          }
          data-testid="blink-canvas"
          data-view={`${view.x0},${view.y0},${view.span}`}
          {...zoom.pointerHandlers}
        />
        {preload.status === "loading" && (
          <div className="blink-overlay" role="status">
            <span>
              Loading images {preload.loaded} / {preload.total}
            </span>
            <progress value={preload.loaded} max={preload.total} />
          </div>
        )}
        {preload.status === "error" && (
          <div className="blink-overlay blink-overlay-error" role="alert">
            <span>An image failed to load. Load the frames again.</span>
            {onReload && (
              <button type="button" onClick={onReload}>
                Reload frames
              </button>
            )}
          </div>
        )}
      </div>

      <div className="blink-info" aria-live={playing ? "off" : "polite"}>
        <strong data-testid="frame-counter">
          Frame {count ? index + 1 : 0} / {count}
        </strong>
        {frame && (
          <>
            <span data-testid="frame-date">{formatUtc(frame.iso)}</span>
            <span data-testid="frame-wavelength">
              {frame.wavelength_um.toFixed(2)} µm
            </span>
            {detector !== undefined && <span>Detector D{detector}</span>}
          </>
        )}
      </div>
      {count === 1 && (
        <p className="blink-single" role="note" data-testid="single-frame">
          Only one visit of this spot is available, so there is nothing to blink
          yet. Try another detector, or check back when SPHEREx has looked
          again.
        </p>
      )}

      <div className="blink-zoom" role="group" aria-label="Zoom">
        <button
          type="button"
          className="secondary"
          onClick={zoom.zoomOut}
          disabled={zoom.fitted}
          aria-label="Zoom out"
          title="Zoom out (−)"
        >
          −
        </button>
        <button
          type="button"
          className="secondary"
          onClick={zoom.zoomIn}
          disabled={view.span <= MIN_SPAN}
          aria-label="Zoom in"
          title="Zoom in (+)"
        >
          +
        </button>
        <button
          type="button"
          className="secondary"
          onClick={zoom.fit}
          disabled={zoom.fitted}
          title="Show the whole image (0)"
        >
          Fit
        </button>
        <span className="blink-zoom-readout" data-testid="zoom-readout">
          {zoom.fovArcmin !== undefined && (
            <>View {formatFov(zoom.fovArcmin)}</>
          )}
          {zoom.fitted ? (
            " · whole image"
          ) : (
            <> · ×{zoom.magnification.toFixed(1)} · drag to move</>
          )}
        </span>
      </div>

      <div className="blink-controls">
        <button
          type="button"
          className="secondary"
          onClick={() => dispatch({ type: "prev" })}
          disabled={disabled}
          aria-label="Previous frame"
        >
          ◀
        </button>
        <button
          type="button"
          className="blink-play"
          onClick={() => dispatch({ type: "toggle" })}
          disabled={disabled}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? "❚❚ Pause" : "▶ Play"}
        </button>
        <button
          type="button"
          className="secondary"
          onClick={() => dispatch({ type: "next" })}
          disabled={disabled}
          aria-label="Next frame"
        >
          ▶
        </button>

        <div className="blink-toggle" role="group" aria-label="Image type">
          {(["original", "diff"] as const).map((value) => (
            <button
              key={value}
              type="button"
              aria-pressed={mode === value}
              onClick={() => dispatch({ type: "setMode", mode: value })}
            >
              {value === "original" ? "Original" : "Difference"}
            </button>
          ))}
        </div>

        <label className="blink-check">
          <input
            type="checkbox"
            checked={showCrosshair}
            disabled={!hasPrediction}
            onChange={() => dispatch({ type: "toggleCrosshair" })}
          />
          Crosshair
        </label>
      </div>

      <div className="blink-sliders">
        <label>
          <span>Frame</span>
          <input
            type="range"
            min={0}
            max={Math.max(0, count - 1)}
            step={1}
            value={index}
            disabled={disabled}
            onChange={(e) =>
              dispatch({ type: "seek", index: Number(e.target.value) })
            }
          />
        </label>
        <label>
          <span>
            Speed <strong>{fps} fps</strong>
          </span>
          <input
            type="range"
            min={FPS_MIN}
            max={FPS_MAX}
            step={1}
            value={fps}
            onChange={(e) => dispatch({ type: "setFps", fps: e.target.value })}
          />
        </label>
      </div>

      <p className="blink-keys">
        Keys: Space play/pause · ← → previous/next frame · + − zoom · 0 whole
        image · Mouse wheel zooms, drag moves
        {!hasPrediction &&
          " · No crosshair: pick a named target to get a predicted position"}
      </p>
    </section>
  );
}
