import { describe, expect, it } from "vitest";
import {
  MIN_SPAN,
  clampView,
  fitView,
  fovOf,
  isFit,
  panView,
  pixelGeometry,
  predictedCentre,
  spanForFov,
  toCanvas,
  viewAround,
  zoomView,
} from "./view";

const grid = { width: 99, height: 99 }; // 10′ at 6.15″/px

describe("fitView / clampView", () => {
  it("fits the whole image", () => {
    expect(fitView(grid)).toEqual({ x0: 0, y0: 0, span: 99 });
    expect(isFit(fitView(grid), grid)).toBe(true);
  });

  it("keeps a window inside the image and its size within limits", () => {
    expect(clampView({ x0: -10, y0: 90, span: 20 }, grid)).toEqual({
      x0: 0,
      y0: 79,
      span: 20,
    });
    expect(clampView({ x0: 5, y0: 5, span: 2 }, grid).span).toBe(MIN_SPAN);
    expect(clampView({ x0: 5, y0: 5, span: 500 }, grid)).toEqual(fitView(grid));
  });

  it("centres a non-square image in a square window", () => {
    expect(fitView({ width: 40, height: 30 })).toEqual({
      x0: 0,
      y0: -5,
      span: 40,
    });
  });
});

describe("field of view", () => {
  it("converts arcminutes to SPHEREx pixels and back", () => {
    expect(spanForFov(5, 6.15)).toBeCloseTo(48.78, 2);
    expect(fovOf({ x0: 0, y0: 0, span: 49 }, 6.15)).toBeCloseTo(5.02, 2);
  });

  it("centres a window on the predicted position", () => {
    // Pixel 49 is the centre of a 99-pixel image; a 21-pixel window starts at 39.
    expect(viewAround(49, 49, 21, grid)).toEqual({ x0: 39, y0: 39, span: 21 });
    // Near the edge the window slides back inside instead of showing nothing.
    expect(viewAround(2, 96, 21, grid)).toEqual({ x0: 0, y0: 78, span: 21 });
  });

  it("averages the predicted positions, ignoring frames without one", () => {
    expect(predictedCentre([[10, 20], null, [14, 22]])).toEqual({
      x: 12,
      y: 21,
    });
    expect(predictedCentre([null, undefined])).toBeNull();
  });
});

describe("zoomView", () => {
  it("zooms about the centre by default", () => {
    const zoomed = zoomView(fitView(grid), 1.5, grid);
    expect(zoomed.span).toBe(66);
    // Windows start on whole pixels, so the centre may move by half a pixel.
    expect(Math.abs(zoomed.x0 + zoomed.span / 2 - 49.5)).toBeLessThanOrEqual(
      0.5,
    );
  });

  it("keeps the pixel under the anchor in place", () => {
    const view = { x0: 20, y0: 20, span: 60 };
    const anchor = { x: 30.5, y: 70.5 };
    const zoomed = zoomView(view, 2, grid, anchor);
    // The anchor sits at the same fraction of the window before and after.
    const before = (anchor.x - view.x0) / view.span;
    const after = (anchor.x - zoomed.x0) / zoomed.span;
    expect(after).toBeCloseTo(before, 1);
  });

  it("always moves at least one pixel and stops at the limits", () => {
    const small = { x0: 40, y0: 40, span: 8 };
    expect(zoomView(small, 1.05, grid).span).toBe(7);
    expect(zoomView({ ...small, span: MIN_SPAN }, 2, grid).span).toBe(MIN_SPAN);
    expect(zoomView(fitView(grid), 1 / 1.5, grid)).toEqual(fitView(grid));
  });
});

describe("panView", () => {
  it("moves by whole pixels and stops at the edges", () => {
    const view = { x0: 40, y0: 40, span: 20 };
    expect(panView(view, 5, -3, grid)).toEqual({ x0: 45, y0: 37, span: 20 });
    expect(panView(view, 500, -500, grid)).toEqual({ x0: 79, y0: 0, span: 20 });
  });

  it("does nothing on a fitted view", () => {
    expect(panView(fitView(grid), 10, 10, grid)).toEqual(fitView(grid));
  });
});

describe("pixelGeometry", () => {
  it("gives whole device pixels per SPHEREx pixel at any devicePixelRatio", () => {
    for (const dpr of [1, 1.25, 1.5, 2, 3]) {
      for (const span of [7, 21, 39, 49, 99]) {
        const { pixelSize, cssWidth } = pixelGeometry(span, 520, dpr);
        expect(Number.isInteger(pixelSize)).toBe(true);
        expect(cssWidth).toBeLessThanOrEqual(520);
        expect(cssWidth * dpr).toBeCloseTo(span * pixelSize, 6);
      }
    }
  });

  it("never drops below one device pixel", () => {
    expect(pixelGeometry(999, 100, 1).pixelSize).toBe(1);
  });
});

describe("toCanvas", () => {
  it("maps a pixel centre into the window", () => {
    const view = { x0: 10, y0: 20, span: 21 };
    expect(toCanvas([17, 19 + 10], view, 10)).toEqual({ cx: 75, cy: 95 });
  });

  it("is null outside the window", () => {
    const view = { x0: 10, y0: 20, span: 21 };
    expect(toCanvas([5, 25], view, 10)).toBeNull();
    expect(toCanvas([15, 45], view, 10)).toBeNull();
  });

  it("matches the full-image formula (x + 0.5) * size on a fitted view", () => {
    expect(toCanvas([17, 19], fitView({ width: 39, height: 39 }), 13)).toEqual({
      cx: 17.5 * 13,
      cy: 19.5 * 13,
    });
  });
});
