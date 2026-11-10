import { describe, expect, it } from "vitest";
import {
  FPS_DEFAULT,
  FPS_MAX,
  FPS_MIN,
  advanceClock,
  initialPlayer,
  playerReducer,
  type PlayerAction,
  type PlayerState,
} from "./player";

const run = (state: PlayerState, ...actions: PlayerAction[]) =>
  actions.reduce(playerReducer, state);
/** Three decoded frames, playing: the state after preload finishes. */
const playing3 = () =>
  run(initialPlayer(), { type: "load", count: 3 }, { type: "play" });

// Feed the clock `seconds` of steady animation frames and count the frame changes.
function ticksOver(seconds: number, fps: number, frameMs: number) {
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
    [1, 1000 / 60, 10],
    [2, 1000 / 60, 20],
    [3, 1000 / 60, 30], // 333 ms is not a whole number of 16.7 ms frames
    [10, 1000 / 60, 100],
    [10, 1000 / 144, 100],
    [5, 1000 / 30, 50], // a busy tab dropping to 30 Hz keeps the same speed
  ])(
    "%s fps at %s ms per frame gives %s changes in 10 s",
    (fps, frameMs, expected) => {
      expect(
        Math.abs(ticksOver(10, fps, frameMs) - expected),
      ).toBeLessThanOrEqual(1);
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
  it("starts empty and paused, showing originals with the crosshair", () => {
    expect(initialPlayer()).toEqual({
      index: 0,
      count: 0,
      playing: false,
      fps: FPS_DEFAULT,
      mode: "original",
      showCrosshair: true,
    });
  });

  it("load resets the frame, pauses, and keeps speed and view choices", () => {
    const state = run(
      playing3(),
      { type: "setFps", fps: 5 },
      { type: "seek", index: 2 },
      { type: "setMode", mode: "diff" },
      { type: "toggleCrosshair" },
    );
    expect(run(state, { type: "load", count: 4 })).toEqual({
      index: 0,
      count: 4,
      playing: false,
      fps: 5,
      mode: "diff",
      showCrosshair: false,
    });
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

  it("cannot play while frames are loading or with a single frame", () => {
    expect(run(initialPlayer(), { type: "play" }).playing).toBe(false);
    const one = run(initialPlayer(), { type: "load", count: 1 });
    expect(run(one, { type: "play" }).playing).toBe(false);
    expect(run(one, { type: "toggle" }).playing).toBe(false);
  });
});

describe("tick", () => {
  it("loops 0 -> 1 -> 2 -> 0 (last frame back to first) and keeps playing", () => {
    const tick: PlayerAction = { type: "tick" };
    const after = (n: number) =>
      run(playing3(), ...Array<PlayerAction>(n).fill(tick));
    expect([1, 2, 3, 4].map((n) => after(n).index)).toEqual([1, 2, 0, 1]);
    expect(after(3).playing).toBe(true);
  });

  it("does nothing without frames", () => {
    expect(run(initialPlayer(), { type: "tick" }).index).toBe(0);
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
    const empty = initialPlayer();
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
    ["7", 7], // value straight from <input type="range">
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

describe("view options", () => {
  it("switches between original and difference images without moving frame", () => {
    const state = run(
      playing3(),
      { type: "tick" },
      { type: "setMode", mode: "diff" },
    );
    expect(state).toMatchObject({ mode: "diff", index: 1, playing: true });
    expect(run(state, { type: "setMode", mode: "original" }).mode).toBe(
      "original",
    );
  });

  it("toggles the crosshair", () => {
    expect(run(playing3(), { type: "toggleCrosshair" }).showCrosshair).toBe(
      false,
    );
  });
});

it("rejects unknown actions", () => {
  expect(() =>
    playerReducer(playing3(), { type: "rewind" } as unknown as PlayerAction),
  ).toThrow(/Unknown/);
});
