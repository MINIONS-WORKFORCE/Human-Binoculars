import { useEffect, useState } from "react";
import type { Frame } from "../api/client";
import { PreloadError, preloadImages } from "./preload";

export type PreloadState =
  | { status: "loading"; loaded: number; total: number }
  | { status: "error"; url: string }
  | {
      status: "ready";
      original: HTMLImageElement[];
      diff: HTMLImageElement[];
    };

/**
 * Fetches and decodes every original and difference PNG of `frames` before any of
 * them is shown. A newer `frames` list cancels the progress updates of an older one.
 */
export function usePreloadedFrames(
  frames: readonly Frame[],
  imageUrl: (path: string) => string,
): PreloadState {
  const total = frames.length * 2;
  const [state, setState] = useState<PreloadState>({
    status: "loading",
    loaded: 0,
    total,
  });
  const [prevFrames, setPrevFrames] = useState(frames);

  // New frames: show progress from zero right away (state reset during render,
  // the pattern React recommends over a synchronous setState in an effect).
  if (frames !== prevFrames) {
    setPrevFrames(frames);
    setState({ status: "loading", loaded: 0, total });
  }

  useEffect(() => {
    let current = true;
    const urls = frames.flatMap((f) => [imageUrl(f.png), imageUrl(f.diff_png)]);
    preloadImages(urls, (loaded) => {
      if (current) setState({ status: "loading", loaded, total: urls.length });
    }).then(
      (images) => {
        if (!current) return;
        setState({
          status: "ready",
          original: images.filter((_, i) => i % 2 === 0),
          diff: images.filter((_, i) => i % 2 === 1),
        });
      },
      (error: unknown) => {
        if (!current) return;
        setState({
          status: "error",
          url: error instanceof PreloadError ? error.url : "unknown",
        });
      },
    );
    return () => {
      current = false;
    };
  }, [frames, imageUrl]);

  return state;
}
