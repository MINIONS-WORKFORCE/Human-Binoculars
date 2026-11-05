import { describe, expect, it, vi } from "vitest";
import { drawCrosshair, drawFrame, fitRect } from "./canvas.js";

describe("drawCrosshair", () => {
  const fakeContext = () => {
    const ctx = {
      segments: [],
      beginPath: vi.fn(),
      stroke: vi.fn(),
      fillText: vi.fn(),
    };
    let from;
    ctx.moveTo = (x, y) => (from = [x, y]);
    ctx.lineTo = (x, y) => ctx.segments.push([...from, x, y]);
    return ctx;
  };

  it("draws four ticks that leave the centre clear", () => {
    const ctx = fakeContext();
    drawCrosshair(ctx, 500, 500);

    expect(ctx.segments).toHaveLength(4);
    for (const [x1, y1, x2, y2] of ctx.segments) {
      const near = Math.hypot(x1 - 250, y1 - 250);
      const far = Math.hypot(x2 - 250, y2 - 250);
      expect(near).toBeCloseTo(20); // 4% gap
      expect(far).toBeCloseTo(45); // gap + 5% arm
    }
    expect(ctx.stroke).toHaveBeenCalledOnce();
    expect(ctx.fillText).not.toHaveBeenCalled();
  });

  it("scales line width and label with devicePixelRatio", () => {
    const ctx = fakeContext();
    drawCrosshair(ctx, 1000, 1000, 2, "FOV 5′");

    expect(ctx.lineWidth).toBe(3);
    expect(ctx.font).toMatch(/^24px/);
    expect(ctx.fillText).toHaveBeenCalledWith("FOV 5′", 16, 984);
  });
});

describe("fitRect", () => {
  it.each([
    ["square in square", [100, 100, 512, 512], { x: 0, y: 0, w: 512, h: 512 }],
    ["wide image", [200, 100, 512, 512], { x: 0, y: 128, w: 512, h: 256 }],
    ["tall image", [100, 200, 512, 512], { x: 128, y: 0, w: 256, h: 512 }],
    [
      "small image is scaled up",
      [32, 16, 300, 300],
      { x: 0, y: 75, w: 300, h: 150 },
    ],
    [
      "large image is scaled down",
      [2048, 2048, 400, 300],
      { x: 50, y: 0, w: 300, h: 300 },
    ],
  ])("%s", (_, args, expected) => {
    expect(fitRect(...args)).toEqual(expected);
  });

  it("keeps the aspect ratio and stays inside the box", () => {
    const { x, y, w, h } = fitRect(1234, 567, 640, 480);
    expect(w / h).toBeCloseTo(1234 / 567, 10);
    expect(x).toBeGreaterThanOrEqual(0);
    expect(y).toBeGreaterThanOrEqual(0);
    expect(x + w).toBeLessThanOrEqual(640);
    expect(y + h).toBeLessThanOrEqual(480);
  });
});

describe("drawFrame", () => {
  const fakeContext = () => ({ fillRect: vi.fn(), drawImage: vi.fn() });

  it("clears to black and draws the frame without smoothing", () => {
    const ctx = fakeContext();
    const frame = { bitmap: {}, width: 200, height: 100 };

    drawFrame(ctx, frame, 512, 512);

    expect(ctx.fillStyle).toBe("#000");
    expect(ctx.fillRect).toHaveBeenCalledWith(0, 0, 512, 512);
    expect(ctx.imageSmoothingEnabled).toBe(false);
    expect(ctx.drawImage).toHaveBeenCalledWith(frame.bitmap, 0, 128, 512, 256);
  });

  it("only clears when there is no frame", () => {
    const ctx = fakeContext();
    drawFrame(ctx, undefined, 512, 512);
    expect(ctx.fillRect).toHaveBeenCalled();
    expect(ctx.drawImage).not.toHaveBeenCalled();
  });
});
