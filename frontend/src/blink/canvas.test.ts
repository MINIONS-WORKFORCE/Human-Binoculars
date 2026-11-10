import { describe, expect, it } from "vitest";
import { crosshairPosition, drawCrosshair, drawImage } from "./canvas";

describe("crosshairPosition: (x + 0.5) * scale", () => {
  it.each([1, 2, 6, 10, 13])(
    "stays on the centre of pixel (17, 19) at %i canvas pixels per SPHEREx pixel",
    (scale) => {
      const { cx, cy } = crosshairPosition([17, 19], scale);
      expect(cx).toBe(17.5 * scale);
      expect(cy).toBe(19.5 * scale);
      // The centre lies strictly inside the pixel's square [x*s, (x+1)*s).
      expect(Math.floor(cx / scale)).toBe(17);
      expect(Math.floor(cy / scale)).toBe(19);
      expect(cx - 17 * scale).toBe(scale / 2);
    },
  );

  it("maps the corners of a 39 x 39 grid with the PNG top-left origin", () => {
    expect(crosshairPosition([0, 0], 10)).toEqual({ cx: 5, cy: 5 });
    expect(crosshairPosition([38, 38], 10)).toEqual({ cx: 385, cy: 385 });
    // y grows downwards: a larger y is lower on the canvas (no FITS flip here).
    expect(crosshairPosition([0, 30], 10).cy).toBeGreaterThan(
      crosshairPosition([0, 5], 10).cy,
    );
  });

  it("keeps sub-pixel predictions", () => {
    expect(crosshairPosition([17.25, 19.75], 10)).toEqual({
      cx: 177.5,
      cy: 202.5,
    });
  });
});

/** Records the calls a 2D context receives. */
function recordingContext() {
  const calls: Array<[string, ...unknown[]]> = [];
  const ctx = new Proxy(
    { imageSmoothingEnabled: true } as Record<string, unknown>,
    {
      get(target, prop: string) {
        if (prop in target) return target[prop];
        return (...args: unknown[]) => calls.push([prop, ...args]);
      },
      set(target, prop: string, value) {
        target[prop] = value;
        calls.push([`set:${prop}`, value]);
        return true;
      },
    },
  );
  return { ctx: ctx as unknown as CanvasRenderingContext2D, calls };
}

describe("drawImage", () => {
  it("turns smoothing off before scaling the image to the whole canvas", () => {
    const { ctx, calls } = recordingContext();
    const image = {} as CanvasImageSource;
    drawImage(ctx, image, 390, 390);
    const names = calls.map((c) => c[0]);
    expect(names.indexOf("set:imageSmoothingEnabled")).toBeLessThan(
      names.indexOf("drawImage"),
    );
    expect(ctx.imageSmoothingEnabled).toBe(false);
    expect(calls.find((c) => c[0] === "drawImage")).toEqual([
      "drawImage",
      image,
      0,
      0,
      390,
      390,
    ]);
  });

  it("only paints black when the image is missing", () => {
    const { ctx, calls } = recordingContext();
    drawImage(ctx, undefined, 390, 390);
    expect(calls.map((c) => c[0])).toEqual(["set:fillStyle", "fillRect"]);
  });
});

describe("drawCrosshair", () => {
  it("leaves a gap of 1.5 pixels around the centre so the star stays visible", () => {
    const { ctx, calls } = recordingContext();
    drawCrosshair(ctx, { cx: 175, cy: 195 }, 10, "#ffc46b");
    const moves = calls.filter((c) => c[0] === "moveTo").slice(0, 4);
    expect(moves).toEqual([
      ["moveTo", 190, 195],
      ["moveTo", 160, 195],
      ["moveTo", 175, 210],
      ["moveTo", 175, 180],
    ]);
    expect(calls).toContainEqual(["set:strokeStyle", "#ffc46b"]);
  });
});
