// Drawing helpers for the blink canvas. All coordinates are canvas backing-store
// pixels: one SPHEREx pixel covers `pixelSize` of them (zoom x devicePixelRatio).

export interface Point {
  cx: number;
  cy: number;
}

/**
 * Centre of SPHEREx pixel (x, y) on a canvas where one pixel is `pixelSize` wide.
 * predicted_px uses the PNG convention (origin top-left, zero-based pixel centres,
 * y already flipped from FITS), so only the half-pixel offset and the zoom apply.
 */
export function crosshairPosition(
  px: readonly [number, number],
  pixelSize: number,
): Point {
  const [x, y] = px;
  return { cx: (x + 0.5) * pixelSize, cy: (y + 0.5) * pixelSize };
}

/** The part of the image to show: a square of `span` pixels from (x0, y0). */
export interface SourceWindow {
  x0: number;
  y0: number;
  span: number;
}

/**
 * Image (or the `source` window of it) scaled to fill the canvas with
 * nearest-neighbour sampling: square pixels. A window reaching past the image
 * edge is clipped by the browser and leaves black, as for a non-square image.
 */
export function drawImage(
  ctx: CanvasRenderingContext2D,
  image: CanvasImageSource | undefined,
  width: number,
  height: number,
  source?: SourceWindow,
) {
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, width, height);
  if (!image) return;
  // Smoothing would invent detail SPHEREx never measured.
  ctx.imageSmoothingEnabled = false;
  if (source) {
    const { x0, y0, span } = source;
    ctx.drawImage(image, x0, y0, span, span, 0, 0, width, height);
  } else {
    ctx.drawImage(image, 0, 0, width, height);
  }
}

/**
 * Four ticks around the predicted position with a gap in the middle, so the star
 * itself stays visible. A dark outline keeps it readable on bright pixels.
 */
export function drawCrosshair(
  ctx: CanvasRenderingContext2D,
  { cx, cy }: Point,
  pixelSize: number,
  color: string,
) {
  const gap = pixelSize * 1.5;
  const arm = pixelSize * 2.5;
  const segments: Array<[number, number]> = [
    [1, 0],
    [-1, 0],
    [0, 1],
    [0, -1],
  ];
  const path = () => {
    ctx.beginPath();
    for (const [dx, dy] of segments) {
      ctx.moveTo(cx + dx * gap, cy + dy * gap);
      ctx.lineTo(cx + dx * (gap + arm), cy + dy * (gap + arm));
    }
  };
  const line = Math.max(1, pixelSize * 0.25);
  ctx.lineCap = "butt";
  ctx.strokeStyle = "rgba(0, 0, 0, 0.8)";
  ctx.lineWidth = line + 2;
  path();
  ctx.stroke();
  ctx.strokeStyle = color;
  ctx.lineWidth = line;
  path();
  ctx.stroke();
}
