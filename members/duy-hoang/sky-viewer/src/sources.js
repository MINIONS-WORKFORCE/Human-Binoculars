// Where the frames come from. Every source has the same shape, so the SPHEREx source
// can be added later (Đông's /api/frames) without touching the page:
//   { id, label, note, enabled, load({ raDeg, decDeg, fovArcmin }, { signal }) -> frames }
// and a frame is { name, bitmap, width, height }, as BlinkViewer expects.

import { makeSampleFrames } from "../../blink/sampleFrames.js";

const LEGACY_SURVEY = "https://www.legacysurvey.org/viewer/jpeg-cutout";
// unWISE coadds by NEOWISE data release, oldest first. Each one stacks all data up to
// that release, so a fast mover shifts between them. Checked on 5/11: all four answer
// with CORS, so the browser can call them directly.
export const UNWISE_LAYERS = [
  "unwise-neo4",
  "unwise-neo6",
  "unwise-neo7",
  "unwise-neo11",
];
export const UNWISE_PIXSCALE = 2.75; // arcsec per pixel, WISE native

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export function unwiseCutoutUrl({ raDeg, decDeg, fovArcmin, layer }) {
  const size = clamp(Math.round((fovArcmin * 60) / UNWISE_PIXSCALE), 16, 512);
  const params = new URLSearchParams({
    ra: raDeg.toFixed(6),
    dec: decDeg.toFixed(6),
    layer,
    pixscale: String(UNWISE_PIXSCALE),
    size: String(size),
  });
  return `${LEGACY_SURVEY}?${params}`;
}

// Legacy Survey answers HTTP 429 when asked too fast, so cutouts are fetched one at a
// time, a 429 is retried after a pause, and fetched images are kept for the session.
const RETRY_DELAYS_MS = [1500, 4000];
const MAX_CACHED = 64;
const cache = new Map(); // url -> Blob

const wait = (ms, signal) =>
  new Promise((resolve, reject) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener("abort", () => {
      clearTimeout(timer);
      reject(signal.reason);
    });
  });

async function fetchCutout(url, label, { signal, fetch, sleep }) {
  if (cache.has(url)) return cache.get(url);
  for (let attempt = 0; ; attempt++) {
    const response = await fetch(url, { signal });
    if (response.ok) {
      const blob = await response.blob();
      if (cache.size >= MAX_CACHED) cache.delete(cache.keys().next().value);
      cache.set(url, blob);
      return blob;
    }
    if (response.status !== 429 || attempt >= RETRY_DELAYS_MS.length) {
      throw new Error(`${label}: HTTP ${response.status}`);
    }
    await sleep(RETRY_DELAYS_MS[attempt], signal);
  }
}

export function clearCutoutCache() {
  cache.clear();
}

async function loadUnwise(
  position,
  {
    signal,
    fetch = globalThis.fetch,
    decode = createImageBitmap,
    sleep = wait,
  } = {},
) {
  const frames = [];
  for (const layer of UNWISE_LAYERS) {
    const url = unwiseCutoutUrl({ ...position, layer });
    const bitmap = await decode(
      await fetchCutout(url, layer, { signal, fetch, sleep }),
    );
    frames.push({
      name: layer,
      bitmap,
      width: bitmap.width,
      height: bitmap.height,
    });
  }
  return frames;
}

export const SOURCES = [
  {
    id: "unwise",
    label: "unWISE (real images)",
    note: "Real WISE infrared images, stacked by data release (oldest first). Not SPHEREx.",
    enabled: true,
    load: loadUnwise,
  },
  {
    id: "sample",
    label: "Sample frames",
    note: "Synthetic frames for testing the player; they do not show this position.",
    enabled: true,
    load: () => makeSampleFrames(),
  },
  {
    id: "spherex",
    label: "SPHEREx (coming)",
    note: "Waiting for the /api/frames contract.",
    enabled: false,
    load: async () => {
      throw new Error("SPHEREx source is not available yet");
    },
  },
];

export const sourceById = (id) => SOURCES.find((source) => source.id === id);
