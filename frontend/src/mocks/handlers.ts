// MSW handlers that mirror members/dong/app/fixture_api.py: same validation,
// same error codes, same echo of the request. Paths start with "*" so they
// match whatever origin VITE_API_BASE_URL points at.
import { http, HttpResponse } from "msw";
import targetTable from "../../../shared/targets.json";
import type { Resolve } from "../api/client";
import { samplePng, samples } from "./samples";

/** Names the API echoes in `target` (members/dong/app/services/fixtures.py). */
const TARGETS: Record<string, string> = {
  barnard: "Barnard's Star",
  wise0855: "WISE 0855-0714",
  epsindib: "Epsilon Indi B",
  rwaur: "RW Aurigae",
  rdra: "R Draconis",
};

// /api/resolve reads shared/targets.json like members/dong/app/services/catalog.py:
// same id -> target_key mapping, same extra aliases, same epoch-tagged record.
const TABLE_KEYS: Record<string, string> = {
  "epsilon-indi-b": "epsindib",
  "rw-aur": "rwaur",
  "r-dra": "rdra",
};
const RESOLVER_ALIASES: Record<string, string[]> = {
  barnard: ["Barnards Star", "GJ 699"],
  wise0855: ["WISE 0855-0714", "WISE J085510.83-071442.5"],
  epsindib: ["eps Ind B"],
  rwaur: ["RW Aur"],
  rdra: ["R Dra"],
};
const CATALOG = targetTable.targets.map((row) => {
  const key = TABLE_KEYS[row.id] ?? row.id;
  const a = row.astrometry;
  const record = {
    target_key: key,
    name: row.name,
    ra: a.ra_deg,
    dec: a.dec_deg,
    epoch: `J${a.reference_epoch_jyear.toFixed(1)}`,
    pmra: a.pm_ra_cosdec_mas_per_yr,
    pmdec: a.pm_dec_mas_per_yr,
    parallax_mas: null,
    kind: key === "rwaur" || key === "rdra" ? "variable" : "high_pm",
    source: "targets_table",
  } satisfies Omit<Resolve, "api_version" | "query">;
  const names = [key, row.name, row.simbad_id, ...RESOLVER_ALIASES[key]];
  return { record, names: new Set(names.map((n) => n.toLowerCase())) };
});
const catalogRecord = (key: string | null) =>
  CATALOG.find((entry) => entry.record.target_key === key)?.record;

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
    const wanted = name.trim().toLowerCase();
    const match = CATALOG.find((entry) => entry.names.has(wanted));
    if (!match) {
      return fail(404, "UNKNOWN_TARGET", "Name absent from fixture resolver.", {
        name,
      });
    }
    return HttpResponse.json({
      api_version: "0.1",
      query: name,
      ...match.record,
    });
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
      // The sample is R Draconis; any other target gets no measurements.
      const own = echoed.target_key === samples.photometry.target.target_key;
      const points = (own ? samples.photometry.points : []).filter(
        (p) => q.detector === undefined || p.detector === q.detector,
      );
      return HttpResponse.json({
        ...samples.photometry,
        reference_star: own ? samples.photometry.reference_star : null,
        target: echoed,
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
      // The sample is Barnard's Star. Other targets get no measurements and the
      // catalog proper motion from shared/targets.json (unknown without a key).
      const own = echoed.target_key === samples.astrometry.target.target_key;
      const record = catalogRecord(echoed.target_key);
      const catalogPm = own
        ? samples.astrometry.catalog_pm
        : {
            pmra: record?.pmra ?? null,
            pmdec: record?.pmdec ?? null,
            epoch: record?.epoch ?? "unknown",
            source: record?.source ?? "unknown",
          };
      // The astrometry sample only has detector 6 measurements, as in the backend.
      const onlyD6 = q.detector !== undefined && q.detector !== 6;
      const measured = own && !onlyD6;
      return HttpResponse.json({
        ...samples.astrometry,
        target: echoed,
        catalog_pm: catalogPm,
        points: measured ? samples.astrometry.points : [],
        fit: measured ? samples.astrometry.fit : null,
      });
    }),
  ),
];
