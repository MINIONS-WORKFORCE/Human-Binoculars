import { describe, expect, it } from "vitest";
import {
  FPS_DEFAULT,
  FPS_MAX,
  FPS_MIN,
  advanceClock,
  initialPlayer,
  playerReducer,
} from "./player.js";

const run = (state, ...actions) => actions.reduce(playerReducer, state);
const playing3 = () => initialPlayer(3);

// Feed the clock `seconds` of steady animation frames and count the frame changes.
function ticksOver(seconds, fps, frameMs) {
  let elapsed = 0;
  let ticks = 0;
  for (let t = 0; t < seconds * 1000; t += frameMs) {
    const clock = advanceClock(elapsed, frameMs, fps);
    elapsed = clock.elapsed;
    if (clock.tick) ticks++;
  }
  return ticks;
}

describe("advanceClock", () => {
  it.each([
    [0.5, 1000 / 60, 5],
    [2, 1000 / 60, 20],
    [3, 1000 / 60, 30], // 333 ms is not a whole number of 16.7 ms frames
    [10, 1000 / 60, 100],
    [10, 1000 / 144, 100],
  ])(
    "%s fps at %s ms per frame gives %s changes in 10 s",
    (fps, frameMs, expected) => {
      expect(ticksOver(10, fps, frameMs)).toBeCloseTo(expected, -0.5);
    },
  );

  it("waits until a full interval has passed", () => {
    expect(advanceClock(0, 400, 2)).toEqual({ tick: false, elapsed: 400 });
    expect(advanceClock(400, 100, 2)).toEqual({ tick: true, elapsed: 0 });
  });

  it("changes at most one frame after a long pause (background tab)", () => {
    const clock = advanceClock(0, 10_000, 2);
    expect(clock.tick).toBe(true);
    expect(clock.elapsed).toBeLessThanOrEqual(500);
  });

  it("ignores negative time steps", () => {
    expect(advanceClock(100, -50, 2)).toEqual({ tick: false, elapsed: 100 });
  });
});

describe("initialPlayer / load", () => {
  it("starts on frame 0, playing when there are at least 2 frames", () => {
    expect(initialPlayer(3)).toEqual({
      index: 0,
      count: 3,
      playing: true,
      fps: FPS_DEFAULT,
    });
    expect(initialPlayer(1).playing).toBe(false);
    expect(initialPlayer().playing).toBe(false);
  });

  it("load resets the frame and keeps the speed", () => {
    const state = run(
      playing3(),
      { type: "setFps", fps: 5 },
      { type: "seek", index: 2 },
    );
    expect(run(state, { type: "load", count: 4 })).toEqual({
      index: 0,
      count: 4,
      playing: true,
      fps: 5,
    });
    expect(run(state, { type: "load", count: 1 }).playing).toBe(false);
  });
});

describe("play / pause / toggle", () => {
  it("toggles", () => {
    const paused = run(playing3(), { type: "toggle" });
    expect(paused.playing).toBe(false);
    expect(run(paused, { type: "toggle" }).playing).toBe(true);
    expect(run(paused, { type: "play" }).playing).toBe(true);
    expect(run(playing3(), { type: "pause" }).playing).toBe(false);
  });

  it("cannot play a single frame", () => {
    expect(run(initialPlayer(1), { type: "play" }).playing).toBe(false);
    expect(run(initialPlayer(1), { type: "toggle" }).playing).toBe(false);
  });
});

describe("tick", () => {
  it("loops 0 -> 1 -> 2 -> 0 and keeps playing", () => {
    const tick = { type: "tick" };
    expect(
      [1, 2, 3].map((n) => run(playing3(), ...Array(n).fill(tick)).index),
    ).toEqual([1, 2, 0]);
    expect(run(playing3(), tick).playing).toBe(true);
  });

  it("does nothing without frames", () => {
    expect(run(initialPlayer(0), { type: "tick" }).index).toBe(0);
  });
});

describe("next / prev / seek", () => {
  it("next and prev wrap around and pause", () => {
    expect(run(playing3(), { type: "next" })).toMatchObject({
      index: 1,
      playing: false,
    });
    expect(run(playing3(), { type: "prev" })).toMatchObject({
      index: 2,
      playing: false,
    });
    expect(
      run(playing3(), { type: "seek", index: 2 }, { type: "next" }).index,
    ).toBe(0);
  });

  it("seek clamps, rounds and pauses", () => {
    expect(run(playing3(), { type: "seek", index: 1 })).toMatchObject({
      index: 1,
      playing: false,
    });
    expect(run(playing3(), { type: "seek", index: 99 }).index).toBe(2);
    expect(run(playing3(), { type: "seek", index: -5 }).index).toBe(0);
    expect(run(playing3(), { type: "seek", index: 1.6 }).index).toBe(2);
  });

  it("ignores stepping without frames", () => {
    const empty = initialPlayer(0);
    expect(
      run(
        empty,
        { type: "next" },
        { type: "prev" },
        { type: "seek", index: 3 },
      ),
    ).toEqual(empty);
  });
});

describe("setFps", () => {
  it.each([
    [4, 4],
    ["2.5", 2.5], // value straight from <input type="range">
    [0, FPS_MIN],
    [100, FPS_MAX],
  ])("%j -> %j", (fps, expected) => {
    expect(run(playing3(), { type: "setFps", fps }).fps).toBe(expected);
  });

  it("ignores values that are not numbers", () => {
    expect(run(playing3(), { type: "setFps", fps: "fast" }).fps).toBe(
      FPS_DEFAULT,
    );
  });
});

it("rejects unknown actions", () => {
  expect(() => playerReducer(playing3(), { type: "rewind" })).toThrow(
    /Unknown/,
  );
});
