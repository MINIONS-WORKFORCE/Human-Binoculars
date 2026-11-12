// MSW handlers that mirror members/dong/app/fixture_api.py: same validation,
// same error codes, same echo of the request. Paths start with "*" so they
// match whatever origin VITE_API_BASE_URL points at.
import { http, HttpResponse } from "msw";
import { samplePng, samples } from "./samples";

const TARGETS: Record<string, string> = {
  barnard: "Barnard's Star",
  wise0855: "WISE 0855-0714",
  epsindib: "Epsilon Indi B",
  rwaur: "RW Aurigae",
  rdra: "R Draconis",
};
const RESOLVER_NAMES = new Set(["barnard", "barnards star", "barnard's star"]);

/** frame id -> sample index, filled by /api/frames like the backend's image registry. */
const published = new Map<string, number>();

function fail(
  status: number,
  code: string,
  message: string,
  details: Record<string, unknown> = {},
) {
  return HttpResponse.json(
    { api_version: "0.1", error: { code, message, details } },
    { status },
  );
}

class BadQuery extends Error {
  readonly fields: string[];
  constructor(fields: string[]) {
    super("Invalid request parameters.");
    this.fields = fields;
  }
}

type Rule = {
  required?: boolean;
  integer?: boolean;
  min?: number;
  max?: number;
  maxExclusive?: number;
};

/** Reads numeric query parameters with the backend's rules and collects every invalid field. */
function readQuery(
  url: URL,
  rules: Record<string, Rule>,
): Record<string, number | undefined> {
  const values: Record<string, number | undefined> = {};
  const bad: string[] = [];
  for (const [name, rule] of Object.entries(rules)) {
    const raw = url.searchParams.get(name);
    if (raw === null || raw === "") {
      if (rule.required) bad.push(name);
      continue;
    }
    const value = Number(raw);
    const invalid =
      !Number.isFinite(value) ||
      (rule.integer && !Number.isInteger(value)) ||
      (rule.min !== undefined && value < rule.min) ||
      (rule.max !== undefined && value > rule.max) ||
      (rule.maxExclusive !== undefined && value >= rule.maxExclusive);
    if (invalid) bad.push(name);
    else values[name] = value;
  }
  const targetKey = url.searchParams.get("target_key");
  if (targetKey !== null && targetKey.length > 80) bad.push("target_key");
  if (bad.length) throw new BadQuery(bad.sort());
  return values;
}

const SKY: Record<string, Rule> = {
  ra: { required: true, min: 0, maxExclusive: 360 },
  dec: { required: true, min: -90, max: 90 },
  detector: { integer: true, min: 1, max: 6 },
};

/** Wraps a resolver so a BadQuery becomes the backend's 400 BAD_COORDS / BAD_PARAM. */
function validated(resolver: (url: URL) => Response) {
  return ({ request }: { request: Request }) => {
    try {
      return resolver(new URL(request.url));
    } catch (error) {
      if (!(error instanceof BadQuery)) throw error;
      const code = error.fields.some((f) => f === "ra" || f === "dec")
        ? "BAD_COORDS"
        : "BAD_PARAM";
      return fail(400, code, "Invalid request parameters.", {
        fields: error.fields,
      });
    }
  };
}

/** The echoed target block, or a 404 response for an unknown key. */
function target(url: URL, ra: number, dec: number) {
  const key = url.searchParams.get("target_key");
  if (key !== null && !(key in TARGETS)) {
    return fail(404, "UNKNOWN_TARGET", "Unknown fixture target.", {
      target_key: key,
    });
  }
  return { ra, dec, target_key: key, name: key === null ? null : TARGETS[key] };
}

function shortHash(text: string): string {
  let hash = 2166136261;
  for (let i = 0; i < text.length; i++)
    hash = Math.imul(hash ^ text.charCodeAt(i), 16777619);
  return (hash >>> 0).toString(16).padStart(8, "0");
}

function png(id: string, difference: boolean) {
  const index = published.get(id);
  const bytes = index === undefined ? undefined : samplePng(index, difference);
  if (!bytes)
    return fail(
      404,
      "FRAME_NOT_FOUND",
      "Call /api/frames first or reload the list.",
      { id },
    );
  return new HttpResponse(bytes, {
    headers: {
      "Content-Type": "image/png",
      "Cache-Control": "public, max-age=86400",
    },
  });
}

export const handlers = [
  http.get("*/api/health", () =>
    HttpResponse.json({ ...samples.health, git_sha: "msw-mock" }),
  ),

  http.get("*/api/resolve", ({ request }) => {
    const name = new URL(request.url).searchParams.get("name");
    if (!name)
      return fail(400, "BAD_PARAM", "Invalid request parameters.", {
        fields: ["name"],
      });
    if (!RESOLVER_NAMES.has(name.trim().toLowerCase())) {
      return fail(404, "UNKNOWN_TARGET", "Name absent from fixture resolver.", {
        name,
      });
    }
    return HttpResponse.json({ ...samples.resolve, query: name });
  }),

  http.get(
    "*/api/frames",
    validated((url) => {
      const q = readQuery(url, {
        ...SKY,
        size: { min: 0.02, max: 0.3 },
        max_frames: { integer: true, min: 1, max: 200 },
      });
      const ra = q.ra!;
      const dec = q.dec!;
      const echoed = target(url, ra, dec);
      if (echoed instanceof Response) return echoed;

      const sample = structuredClone(samples.frames);
      const identity = shortHash(url.search);
      const warnings = [...sample.warnings];
      const frames = sample.frames
        .slice(0, q.max_frames ?? 60)
        .map((frame, index) => {
          const id = `fixture-${identity}-${index}`;
          published.set(id, index);
          return {
            ...frame,
            id,
            predicted_px: echoed.target_key ? frame.predicted_px : null,
            png: `/api/frames/${id}.png`,
            diff_png: `/api/frames/${id}/diff.png`,
          };
        });
      if (frames.length < sample.frames.length) warnings.push("TRUNCATED");
      if (frames.length < 3) warnings.push("FEW_FRAMES");

      return HttpResponse.json({
        ...sample,
        target: echoed,
        detector: q.detector ?? 6,
        grid: { ...sample.grid, center_ra: ra, center_dec: dec },
        reference_frame_id: frames[0]?.id ?? null,
        frames,
        warnings,
      });
    }),
  ),

  http.get("*/api/frames/:id/diff.png", ({ params }) =>
    png(String(params.id), true),
  ),

  http.get("*/api/frames/:file", ({ params }) => {
    const file = String(params.file);
    if (!file.endsWith(".png")) return fail(404, "INTERNAL", "Request failed.");
    return png(file.slice(0, -".png".length), false);
  }),

  http.get(
    "*/api/photometry",
    validated((url) => {
      const q = readQuery(url, {
        ...SKY,
        aperture_arcsec: { min: Number.MIN_VALUE },
      });
      const echoed = target(url, q.ra!, q.dec!);
      if (echoed instanceof Response) return echoed;
      // Like the backend, only the sample's own target (R Draconis) has measurements.
      const hasSample =
        echoed.target_key === samples.photometry.target.target_key;
      const points = hasSample
        ? samples.photometry.points.filter(
            (p) => q.detector === undefined || p.detector === q.detector,
          )
        : [];
      return HttpResponse.json({
        ...samples.photometry,
        target: echoed,
        reference_star: hasSample ? samples.photometry.reference_star : null,
        points,
        variability: null,
      });
    }),
  ),

  http.get(
    "*/api/astrometry",
    validated((url) => {
      const q = readQuery(url, SKY);
      const echoed = target(url, q.ra!, q.dec!);
      if (echoed instanceof Response) return echoed;
      // The astrometry sample only has detector 6 measurements, as in the backend.
      const onlyD6 = q.detector !== undefined && q.detector !== 6;
      return HttpResponse.json({
        ...samples.astrometry,
        target: echoed,
        points: onlyD6 ? [] : samples.astrometry.points,
        fit: onlyD6 ? null : samples.astrometry.fit,
      });
    }),
  ),
];
