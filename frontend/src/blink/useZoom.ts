// Zoom and pan for the blink canvas, entirely in the browser: the frames were
// fetched once at the widest field, so looking closer never calls the API.
//   + / − buttons and keys, 0 or Fit for the whole image, mouse wheel (zooms about
//   the pointer), drag to pan, two-finger pinch on touch screens.
import {
  useEffect,
  useRef,
  useState,
  type PointerEvent,
  type RefObject,
} from "react";
import {
  ZOOM_STEP,
  fitView,
  fovOf,
  isFit,
  panView,
  spanForFov,
  viewAround,
  zoomView,
  type GridSize,
  type View,
} from "./view";

/** A requested field of view. A new object re-applies it, even with the same value. */
export interface FovRequest {
  /** Arcminutes; null or anything as wide as the image means the whole image. */
  arcmin: number | null;
}

interface Options {
  canvasRef: RefObject<HTMLCanvasElement | null>;
  grid: GridSize;
  pixscaleArcsec: number | undefined;
  /** Where a field of view centres: the star's predicted pixel, if known. */
  centre: { x: number; y: number } | null;
  fov: FovRequest | undefined;
  /** Identity of the frame set; new frames start again from `fov`. */
  framesKey: unknown;
}

function viewFor(
  fov: FovRequest | undefined,
  grid: GridSize,
  pixscale: number | undefined,
  centre: { x: number; y: number } | null,
): View {
  if (!fov?.arcmin || !pixscale) return fitView(grid);
  const c = centre ?? { x: (grid.width - 1) / 2, y: (grid.height - 1) / 2 };
  return viewAround(c.x, c.y, spanForFov(fov.arcmin, pixscale), grid);
}

/** The image pixel (continuous coordinates) under a point on the canvas. */
function imagePoint(
  canvas: HTMLCanvasElement,
  view: View,
  clientX: number,
  clientY: number,
) {
  const rect = canvas.getBoundingClientRect();
  return {
    x: view.x0 + ((clientX - rect.left) / rect.width) * view.span,
    y: view.y0 + ((clientY - rect.top) / rect.height) * view.span,
  };
}

export function useZoom({
  canvasRef,
  grid,
  pixscaleArcsec,
  centre,
  fov,
  framesKey,
}: Options) {
  const [view, setView] = useState<View>(() =>
    viewFor(fov, grid, pixscaleArcsec, centre),
  );
  // A new FOV request or new frames reset the window (state reset during render,
  // the pattern React recommends over a synchronous setState in an effect).
  const [applied, setApplied] = useState({ fov, framesKey });
  if (applied.fov !== fov || applied.framesKey !== framesKey) {
    setApplied({ fov, framesKey });
    setView(viewFor(fov, grid, pixscaleArcsec, centre));
  }

  // Event handlers read the latest view without re-subscribing on every change.
  const viewRef = useRef(view);
  useEffect(() => {
    viewRef.current = view;
  }, [view]);

  const zoomBy = (factor: number, anchor?: { x: number; y: number }) =>
    setView((v) => zoomView(v, factor, grid, anchor));
  const zoomIn = () => zoomBy(ZOOM_STEP);
  const zoomOut = () => zoomBy(1 / ZOOM_STEP);
  const fit = () => setView(fitView(grid));

  // Mouse wheel: needs a non-passive listener to stop the page from scrolling.
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;
    const onWheel = (event: WheelEvent) => {
      if (event.deltaY === 0) return;
      event.preventDefault();
      const anchor = imagePoint(
        canvas,
        viewRef.current,
        event.clientX,
        event.clientY,
      );
      setView((v) =>
        zoomView(v, event.deltaY < 0 ? ZOOM_STEP : 1 / ZOOM_STEP, grid, anchor),
      );
    };
    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", onWheel);
  }, [canvasRef, grid]);

  // Drag to pan (one pointer), pinch to zoom (two pointers).
  const pointers = useRef(new Map<number, { x: number; y: number }>());
  const carry = useRef({ x: 0, y: 0 }); // sub-pixel drag not applied yet
  const pinch = useRef<number | null>(null); // finger distance at the last step

  const onPointerDown = (event: PointerEvent<HTMLCanvasElement>) => {
    pointers.current.set(event.pointerId, {
      x: event.clientX,
      y: event.clientY,
    });
    carry.current = { x: 0, y: 0 };
    pinch.current = null;
    try {
      // Keep receiving moves when the pointer leaves the canvas mid-drag.
      event.currentTarget.setPointerCapture(event.pointerId);
    } catch {
      // Not capturable (already released): the drag still works over the canvas.
    }
  };

  const onPointerMove = (event: PointerEvent<HTMLCanvasElement>) => {
    const last = pointers.current.get(event.pointerId);
    if (!last) return;
    const canvas = event.currentTarget;
    const now = { x: event.clientX, y: event.clientY };
    pointers.current.set(event.pointerId, now);
    const current = viewRef.current;

    if (pointers.current.size >= 2) {
      const [a, b] = [...pointers.current.values()];
      const distance = Math.hypot(a.x - b.x, a.y - b.y);
      if (pinch.current === null) {
        pinch.current = distance;
        return;
      }
      const factor = distance / pinch.current;
      // Act only on a clear change, so a steady hold does not jitter.
      if (Math.abs(Math.log(factor)) < Math.log(1.12)) return;
      const anchor = imagePoint(
        canvas,
        current,
        (a.x + b.x) / 2,
        (a.y + b.y) / 2,
      );
      setView(zoomView(current, factor, grid, anchor));
      pinch.current = distance;
      return;
    }

    const rect = canvas.getBoundingClientRect();
    const perPixel = rect.width / current.span; // CSS pixels per SPHEREx pixel
    const dx = carry.current.x - (now.x - last.x) / perPixel;
    const dy = carry.current.y - (now.y - last.y) / perPixel;
    const stepX = Math.trunc(dx);
    const stepY = Math.trunc(dy);
    carry.current = { x: dx - stepX, y: dy - stepY };
    if (stepX || stepY) setView(panView(current, stepX, stepY, grid));
  };

  const onPointerUp = (event: PointerEvent<HTMLCanvasElement>) => {
    pointers.current.delete(event.pointerId);
    pinch.current = null;
  };

  // Keys: + and − zoom, 0 fits. Typing in a field keeps its keys.
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && /^(INPUT|TEXTAREA|SELECT)$/.test(target.tagName)) return;
      if (event.ctrlKey || event.metaKey || event.altKey) return;
      const factor =
        event.key === "+" || event.key === "="
          ? ZOOM_STEP
          : event.key === "-" || event.key === "_"
            ? 1 / ZOOM_STEP
            : null;
      if (factor !== null) {
        event.preventDefault();
        setView((v) => zoomView(v, factor, grid));
      } else if (event.key === "0") {
        event.preventDefault();
        setView(fitView(grid));
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [grid]);

  const fitted = isFit(view, grid);
  return {
    view,
    fitted,
    /** The field of view on screen, in arcminutes (undefined without a pixel scale). */
    fovArcmin:
      pixscaleArcsec === undefined ? undefined : fovOf(view, pixscaleArcsec),
    /** Magnification relative to the whole image. */
    magnification: Math.max(grid.width, grid.height) / view.span,
    zoomIn,
    zoomOut,
    fit,
    pointerHandlers: {
      onPointerDown,
      onPointerMove,
      onPointerUp,
      onPointerCancel: onPointerUp,
    },
  };
}
