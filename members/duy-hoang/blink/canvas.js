// Drawing helpers for the blink canvas.

/** Largest rectangle with the image's aspect ratio that fits in the box, centred. */
export function fitRect(imageWidth, imageHeight, boxWidth, boxHeight) {
  const scale = Math.min(boxWidth / imageWidth, boxHeight / imageHeight);
  const w = imageWidth * scale;
  const h = imageHeight * scale;
  return { x: (boxWidth - w) / 2, y: (boxHeight - h) / 2, w, h };
}

/** Black background, then the frame scaled to fit without smoothing (keeps pixels sharp). */
export function drawFrame(ctx, frame, boxWidth, boxHeight) {
  ctx.fillStyle = "#000";
  ctx.fillRect(0, 0, boxWidth, boxHeight);
  if (!frame) return;
  const { x, y, w, h } = fitRect(
    frame.width,
    frame.height,
    boxWidth,
    boxHeight,
  );
  ctx.imageSmoothingEnabled = false;
  ctx.drawImage(frame.bitmap, x, y, w, h);
}

/**
 * Four short ticks around the centre, with a gap so the target itself stays visible,
 * and an optional label in the bottom-left corner. `ratio` is devicePixelRatio.
 */
export function drawCrosshair(ctx, boxWidth, boxHeight, ratio = 1, label = "") {
  const cx = boxWidth / 2;
  const cy = boxHeight / 2;
  const size = Math.min(boxWidth, boxHeight);
  const gap = size * 0.04;
  const arm = size * 0.05;

  ctx.strokeStyle = "rgba(80, 255, 120, 0.85)";
  ctx.lineWidth = 1.5 * ratio;
  ctx.beginPath();
  for (const [dx, dy] of [
    [1, 0],
    [-1, 0],
    [0, 1],
    [0, -1],
  ]) {
    ctx.moveTo(cx + dx * gap, cy + dy * gap);
    ctx.lineTo(cx + dx * (gap + arm), cy + dy * (gap + arm));
  }
  ctx.stroke();

  if (label) {
    ctx.fillStyle = "rgba(80, 255, 120, 0.85)";
    ctx.font = `${12 * ratio}px system-ui, sans-serif`;
    ctx.fillText(label, 8 * ratio, boxHeight - 8 * ratio);
  }
}
