import { useEffect, useReducer, useRef } from "react";
import { drawCrosshair, drawFrame } from "./canvas.js";
import {
  FPS_MAX,
  FPS_MIN,
  advanceClock,
  initialPlayer,
  playerReducer,
} from "./player.js";

// Keys typed into a form control belong to that control, not to the player.
const isFormControl = (target) =>
  /^(INPUT|TEXTAREA|SELECT|BUTTON)$/.test(target?.tagName);

function usePlaybackTimer(playing, fps, dispatch) {
  useEffect(() => {
    if (!playing) return undefined;
    let frameId;
    let last = performance.now();
    let elapsed = 0;
    const step = (now) => {
      const clock = advanceClock(elapsed, now - last, fps);
      elapsed = clock.elapsed;
      last = now;
      if (clock.tick) dispatch({ type: "tick" });
      frameId = requestAnimationFrame(step);
    };
    frameId = requestAnimationFrame(step);
    return () => cancelAnimationFrame(frameId);
  }, [playing, fps, dispatch]);
}

function useCanvas(canvasRef, frame, overlay) {
  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return undefined;

    // Size the backing store to the displayed size times devicePixelRatio, so it stays sharp.
    const draw = () => {
      const ratio = window.devicePixelRatio || 1;
      const width = Math.round(canvas.clientWidth * ratio);
      const height = Math.round(canvas.clientHeight * ratio);
      if (canvas.width !== width || canvas.height !== height) {
        canvas.width = width;
        canvas.height = height;
      }
      const ctx = canvas.getContext("2d");
      drawFrame(ctx, frame, width, height);
      if (frame && overlay)
        drawCrosshair(ctx, width, height, ratio, overlay.label);
    };

    draw();
    const observer = new ResizeObserver(draw);
    observer.observe(canvas);
    return () => observer.disconnect();
  }, [canvasRef, frame, overlay]);
}

/**
 * frames: [{ name, bitmap, width, height }].
 * overlay (optional, keep it memoised): { label } draws a centre crosshair and the label.
 */
export function BlinkViewer({ frames, overlay = null }) {
  const [player, dispatch] = useReducer(
    playerReducer,
    frames.length,
    initialPlayer,
  );
  const canvasRef = useRef(null);
  const { index, count, playing, fps } = player;
  const frame = frames[index];

  useEffect(() => {
    dispatch({ type: "load", count: frames.length });
  }, [frames]);

  usePlaybackTimer(playing, fps, dispatch);
  useCanvas(canvasRef, frame, overlay);

  useEffect(() => {
    const onKey = (event) => {
      if (isFormControl(event.target)) return;
      const action = { " ": "toggle", ArrowRight: "next", ArrowLeft: "prev" }[
        event.key
      ];
      if (!action) return;
      event.preventDefault();
      dispatch({ type: action });
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const sizes = new Set(frames.map((f) => `${f.width}x${f.height}`));

  return (
    <section style={{ display: "grid", gap: 12, maxWidth: 512 }}>
      <canvas
        ref={canvasRef}
        aria-label={
          frame ? `Frame ${index + 1} of ${count}: ${frame.name}` : "No frames"
        }
        style={{
          width: "100%",
          aspectRatio: "1",
          background: "#000",
          borderRadius: 4,
          display: "block",
        }}
      />

      <div
        style={{
          display: "flex",
          gap: 8,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <button
          type="button"
          onClick={() => dispatch({ type: "prev" })}
          disabled={count < 2}
        >
          ◀ Prev
        </button>
        <button
          type="button"
          onClick={() => dispatch({ type: "toggle" })}
          disabled={count < 2}
          style={{ minWidth: 80 }}
        >
          {playing ? "❚❚ Pause" : "▶ Play"}
        </button>
        <button
          type="button"
          onClick={() => dispatch({ type: "next" })}
          disabled={count < 2}
        >
          Next ▶
        </button>
        <span style={{ fontVariantNumeric: "tabular-nums" }}>
          Frame {count ? index + 1 : 0} / {count}
          {frame ? ` · ${frame.name}` : ""}
        </span>
      </div>

      <label style={{ display: "grid", gap: 4 }}>
        <span>Frame</span>
        <input
          type="range"
          min={0}
          max={Math.max(0, count - 1)}
          step={1}
          value={index}
          disabled={count < 2}
          onChange={(event) =>
            dispatch({ type: "seek", index: Number(event.target.value) })
          }
          aria-label="Frame"
        />
      </label>

      <label style={{ display: "grid", gap: 4 }}>
        <span>
          Speed: <strong>{fps} fps</strong>
        </span>
        <input
          type="range"
          min={FPS_MIN}
          max={FPS_MAX}
          step={0.5}
          value={fps}
          onChange={(event) =>
            dispatch({ type: "setFps", fps: event.target.value })
          }
          aria-label="Speed in frames per second"
        />
      </label>

      {sizes.size > 1 && (
        <p style={{ color: "#b9770e", margin: 0 }}>
          Frames have different sizes ({[...sizes].join(", ")}); the blink will
          not line up.
        </p>
      )}
      <p style={{ margin: 0, opacity: 0.7, fontSize: 14 }}>
        Keys: Space play/pause, ← → previous/next frame.
      </p>
    </section>
  );
}
