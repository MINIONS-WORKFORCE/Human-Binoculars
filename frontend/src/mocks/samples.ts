// The synthetic API samples Đông committed in <repo>/api_samples (Issue 14).
// The same files feed MSW in the browser, the Vitest suite and the backend's
// own schema validator, so the three never drift apart.
import astrometry from "../../../api_samples/astrometry_barnard.json";
import errorNoFrames from "../../../api_samples/error_no_frames.json";
import frames from "../../../api_samples/frames_barnard_d6.json";
import health from "../../../api_samples/health.json";
import photometry from "../../../api_samples/photometry_rdra.json";
import resolve from "../../../api_samples/resolve_barnard.json";
import type {
  Astrometry,
  ErrorResponse,
  Frames,
  Health,
  Photometry,
  Resolve,
} from "../api/client";

// JSON imports are typed loosely ("0.1" becomes string, tuples become number[]),
// so they are cast here. samples.test.ts proves at runtime that the casts hold.
export const samples = {
  health: health as unknown as Health,
  resolve: resolve as unknown as Resolve,
  frames: frames as unknown as Frames,
  photometry: photometry as unknown as Photometry,
  astrometry: astrometry as unknown as Astrometry,
  errorNoFrames: errorNoFrames as unknown as ErrorResponse,
};

/** Raw JSON keyed by file name and the OpenAPI schema it must satisfy. */
export const sampleFiles: Array<{
  file: string;
  schema: string;
  json: unknown;
}> = [
  { file: "health.json", schema: "Health", json: health },
  { file: "resolve_barnard.json", schema: "Resolve", json: resolve },
  { file: "frames_barnard_d6.json", schema: "Frames", json: frames },
  { file: "photometry_rdra.json", schema: "Photometry", json: photometry },
  { file: "astrometry_barnard.json", schema: "Astrometry", json: astrometry },
  {
    file: "error_no_frames.json",
    schema: "ErrorResponse",
    json: errorNoFrames,
  },
];

// Inlined as data: URLs so the bytes are available both in the browser and in Node.
const pngs = import.meta.glob<string>("../../../api_samples/png/*.png", {
  query: "?inline",
  import: "default",
  eager: true,
});

/** PNG bytes of sample frame `index` (0-based), or of its difference image. */
export function samplePng(
  index: number,
  difference: boolean,
): Uint8Array<ArrayBuffer> | undefined {
  const dataUrl =
    pngs[
      `../../../api_samples/png/frame-${index}${difference ? "_diff" : ""}.png`
    ];
  if (!dataUrl) return undefined;
  const binary = atob(dataUrl.slice(dataUrl.indexOf(",") + 1));
  return Uint8Array.from(binary, (char) => char.charCodeAt(0));
}
