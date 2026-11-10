// Playback state for the blink viewer. Pure reducer, no React or timers, so every
// rule is covered by player.test.ts. Ported from members/duy-hoang/blink/player.js.

export const FPS_MIN = 1;
export const FPS_MAX = 10;
export const FPS_DEFAULT = 2; // astronomy blinks usually run at 1-4 frames per second

export type ImageMode = "original" | "diff";

export interface PlayerState {
  index: number;
  count: number;
  playing: boolean;
  fps: number;
  mode: ImageMode;
  showCrosshair: boolean;
}

export type PlayerAction =
  | { type: "load"; count: number }
  | { type: "play" }
  | { type: "pause" }
  | { type: "toggle" }
  | { type: "tick" }
  | { type: "next" }
  | { type: "prev" }
  | { type: "seek"; index: number }
  | { type: "setFps"; fps: number | string }
  | { type: "setMode"; mode: ImageMode }
  | { type: "toggleCrosshair" };

const clamp = (value: number, min: number, max: number) =>
  Math.min(max, Math.max(min, value));

/**
 * One animation-frame step of the playback clock. Adds deltaMs to the time since the
 * last frame change and says whether to advance. The leftover is kept, so 3 fps on a
 * 60 Hz screen averages exactly 3 changes per second. At most one change per step and
 * at most one interval carried over, so a tab that was in the background does not
 * fast-forward through a burst of frames when it comes back.
 */
export function advanceClock(
  elapsedMs: number,
  deltaMs: number,
  fps: number,
): { tick: boolean; elapsed: number } {
  const interval = 1000 / fps;
  const elapsed = elapsedMs + Math.max(0, deltaMs);
  if (elapsed < interval) return { tick: false, elapsed };
  return { tick: true, elapsed: Math.min(elapsed - interval, interval) };
}

/** Starts paused: frames are only playable once every image is decoded. */
export function initialPlayer(count = 0): PlayerState {
  return {
    index: 0,
    count,
    playing: false,
    fps: FPS_DEFAULT,
    mode: "original",
    showCrosshair: true,
  };
}

export function playerReducer(
  state: PlayerState,
  action: PlayerAction,
): PlayerState {
  const { count } = state;
  switch (action.type) {
    case "load":
      // New frames: back to the first one, keep speed, mode and crosshair choice.
      return { ...state, index: 0, count: action.count, playing: false };
    case "play":
      return { ...state, playing: count >= 2 };
    case "pause":
      return { ...state, playing: false };
    case "toggle":
      return { ...state, playing: !state.playing && count >= 2 };
    case "tick":
      if (count === 0) return state;
      return { ...state, index: (state.index + 1) % count };
    // Stepping or scrubbing by hand pauses, so the frame stays where the user put it.
    case "next":
      if (count === 0) return state;
      return { ...state, index: (state.index + 1) % count, playing: false };
    case "prev":
      if (count === 0) return state;
      return {
        ...state,
        index: (state.index - 1 + count) % count,
        playing: false,
      };
    case "seek":
      if (count === 0) return state;
      return {
        ...state,
        index: clamp(Math.round(action.index), 0, count - 1),
        playing: false,
      };
    case "setFps": {
      const fps = Number(action.fps);
      return Number.isFinite(fps)
        ? { ...state, fps: clamp(fps, FPS_MIN, FPS_MAX) }
        : state;
    }
    case "setMode":
      return { ...state, mode: action.mode };
    case "toggleCrosshair":
      return { ...state, showCrosshair: !state.showCrosshair };
    default: {
      const unknown: never = action;
      throw new Error(
        `Unknown player action: ${(unknown as { type: string }).type}`,
      );
    }
  }
}
