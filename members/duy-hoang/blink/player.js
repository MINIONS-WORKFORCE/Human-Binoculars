// Playback state for the blink viewer. Pure reducer, no React or timers,
// so every rule here is covered by player.test.js.

export const FPS_MIN = 0.5;
export const FPS_MAX = 10;
export const FPS_DEFAULT = 2; // astronomy blinks usually run at 1-4 frames per second

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

/**
 * One animation-frame step of the playback clock. Adds deltaMs to the time since the
 * last frame change and says whether to advance. The leftover is kept, so 3 fps on a
 * 60 Hz screen averages exactly 3 changes per second. At most one change per step and
 * at most one interval carried over, so a tab that was in the background does not
 * fast-forward through a burst of frames when it comes back.
 */
export function advanceClock(elapsedMs, deltaMs, fps) {
  const interval = 1000 / fps;
  const elapsed = elapsedMs + Math.max(0, deltaMs);
  if (elapsed < interval) return { tick: false, elapsed };
  return { tick: true, elapsed: Math.min(elapsed - interval, interval) };
}

export function initialPlayer(count = 0) {
  return { index: 0, count, playing: count >= 2, fps: FPS_DEFAULT };
}

export function playerReducer(state, action) {
  const { count } = state;
  switch (action.type) {
    case "load":
      return {
        ...state,
        index: 0,
        count: action.count,
        playing: action.count >= 2,
      };
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
    default:
      throw new Error(`Unknown player action: ${action.type}`);
  }
}
