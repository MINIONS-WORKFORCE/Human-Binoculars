// Which part of the frames the canvas shows. The API is asked once for the widest
// field; zooming and panning only change this window, so they need no request.
//
// A view is a square window of `span` SPHEREx pixels whose top-left pixel is
// (x0, y0), in the PNG's convention (origin top-left). All three are integers, so
// every SPHEREx pixel still covers a whole number of screen pixels: square, crisp.

export interface View {
  x0: number;
  y0: number;
  span: number;
}

export interface GridSize {
  width: number;
  height: number;
}

/** Never zoom in further than this many SPHEREx pixels across (about 40″). */
export const MIN_SPAN = 7;
/** Each + / − press or wheel notch zooms by this factor. */
export const ZOOM_STEP = 1.5;

const fullSpan = (grid: GridSize) => Math.max(grid.width, grid.height);

/** Keeps the window inside the image; a window as large as the image is centred. */
export function clampView(view: View, grid: GridSize): View {
  const span = Math.min(
    fullSpan(grid),
    Math.max(MIN_SPAN, Math.round(view.span)),
  );
  const axis = (start: number, size: number) =>
    span >= size
      ? Math.round((size - span) / 2)
      : Math.min(size - span, Math.max(0, Math.round(start)));
  return {
    x0: axis(view.x0, grid.width),
    y0: axis(view.y0, grid.height),
    span,
  };
}

/** The whole image. */
export function fitView(grid: GridSize): View {
  return clampView({ x0: 0, y0: 0, span: fullSpan(grid) }, grid);
}

/** A window `span` pixels wide centred on (cx, cy), in pixel-centre coordinates. */
export function viewAround(
  cx: number,
  cy: number,
  span: number,
  grid: GridSize,
): View {
  const s = Math.round(span);
  return clampView(
    { x0: cx + 0.5 - s / 2, y0: cy + 0.5 - s / 2, span: s },
    grid,
  );
}

/** SPHEREx pixels across a field of view in arcminutes. */
export function spanForFov(fovArcmin: number, pixscaleArcsec: number): number {
  return (fovArcmin * 60) / pixscaleArcsec;
}

/** The field of view a window shows, in arcminutes. */
export function fovOf(view: View, pixscaleArcsec: number): number {
  return (view.span * pixscaleArcsec) / 60;
}

/**
 * Zooms by `factor` (> 1 zooms in) keeping the pixel under `anchor` in place, so
 * the spot under the mouse or between two fingers stays put. Without an anchor the
 * centre stays put.
 */
export function zoomView(
  view: View,
  factor: number,
  grid: GridSize,
  anchor: { x: number; y: number } = {
    x: view.x0 + view.span / 2,
    y: view.y0 + view.span / 2,
  },
): View {
  let span = Math.round(view.span / factor);
  // Rounding must not swallow a step on small windows.
  if (span === view.span) span += factor > 1 ? -1 : 1;
  const scale = span / view.span;
  return clampView(
    {
      x0: anchor.x - (anchor.x - view.x0) * scale,
      y0: anchor.y - (anchor.y - view.y0) * scale,
      span,
    },
    grid,
  );
}

/** Moves the window by whole SPHEREx pixels (positive = towards larger x / y). */
export function panView(
  view: View,
  dx: number,
  dy: number,
  grid: GridSize,
): View {
  return clampView({ ...view, x0: view.x0 + dx, y0: view.y0 + dy }, grid);
}

export const isFit = (view: View, grid: GridSize) =>
  view.span >= fullSpan(grid);

/**
 * Whole device pixels per SPHEREx pixel so the window fills about `targetCss`
 * CSS pixels, and the CSS width that shows the canvas at exactly that size.
 * Rounding down keeps the canvas no wider than its box on any devicePixelRatio.
 */
export function pixelGeometry(span: number, targetCss: number, dpr: number) {
  const pixelSize = Math.max(1, Math.floor((targetCss * dpr) / span));
  return { pixelSize, cssWidth: (span * pixelSize) / dpr };
}

/** Where an image pixel centre lands on the canvas, or null when outside the window. */
export function toCanvas(
  px: readonly [number, number],
  view: View,
  pixelSize: number,
): { cx: number; cy: number } | null {
  const [x, y] = px;
  const u = x - view.x0;
  const v = y - view.y0;
  if (u < -0.5 || v < -0.5 || u > view.span - 0.5 || v > view.span - 0.5)
    return null;
  return { cx: (u + 0.5) * pixelSize, cy: (v + 0.5) * pixelSize };
}

/** The mean predicted position over the frames, where zooming should centre. */
export function predictedCentre(
  positions: ReadonlyArray<readonly [number, number] | null | undefined>,
): { x: number; y: number } | null {
  const known = positions.filter((p): p is readonly [number, number] => !!p);
  if (!known.length) return null;
  const sum = known.reduce((acc, [x, y]) => [acc[0] + x, acc[1] + y], [0, 0]);
  return { x: sum[0] / known.length, y: sum[1] / known.length };
}
