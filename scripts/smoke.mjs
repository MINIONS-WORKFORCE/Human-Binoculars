#!/usr/bin/env node
// Smoke test before every demo: is the API up, and does each challenge target give
// a blink the viewer can play? No dependencies; Node 18+.
//
//   npm run smoke                                         # http://127.0.0.1:8000
//   npm run smoke -- https://human-binoculars.onrender.com
//   npm run smoke -- <api-url> --origin https://<frontend>.vercel.app
//
// --origin also checks that the API's CORS lets that frontend read the answers.
// Exit code 0 when every check passes, 1 otherwise.
import { readFileSync } from "node:fs";

const args = process.argv.slice(2);
const flag = (name) => {
  const i = args.indexOf(name);
  return i === -1 ? undefined : args.splice(i, 2)[1];
};
const origin = flag("--origin");
const detector = Number(flag("--detector") ?? 6);
const base = (args[0] ?? process.env.SMOKE_API_URL ?? "http://127.0.0.1:8000").replace(/\/$/, "");
// A sleeping free-tier host (Render) needs about a minute to wake up.
const TIMEOUT_MS = Number(process.env.SMOKE_TIMEOUT_MS ?? 120_000);

// The five targets from the shared table, under the API's target_key names.
const TABLE_KEY = { "epsilon-indi-b": "epsindib", "rw-aur": "rwaur", "r-dra": "rdra" };
const table = JSON.parse(readFileSync(new URL("../shared/targets.json", import.meta.url), "utf8"));
const targets = table.targets.map((t) => ({
  key: TABLE_KEY[t.id] ?? t.id,
  name: t.name,
  ra: t.astrometry.ra_deg,
  dec: t.astrometry.dec_deg,
}));

const PNG_MAGIC = [0x89, 0x50, 0x4e, 0x47];
const results = [];

async function get(path) {
  const started = performance.now();
  const response = await fetch(base + path, {
    headers: origin ? { Origin: origin } : {},
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  const ms = Math.round(performance.now() - started);
  if (origin) {
    const allowed = response.headers.get("access-control-allow-origin");
    if (allowed !== "*" && allowed !== origin)
      throw new Error(`CORS: ${origin} is not allowed (got ${allowed ?? "no header"})`);
  }
  return { response, ms };
}

async function json(path) {
  const { response, ms } = await get(path);
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const code = body?.error?.code ?? "not contract JSON";
    throw new Error(`HTTP ${response.status} ${code}`);
  }
  if (body?.api_version !== "0.1") throw new Error("missing api_version 0.1");
  return { body, ms };
}

async function png(path) {
  const { response, ms } = await get(path);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}`);
  if (!PNG_MAGIC.every((b, i) => bytes[i] === b)) throw new Error(`${path}: not a PNG`);
  return ms;
}

async function check(name, run) {
  try {
    const detail = await run();
    results.push({ ok: true, name, detail });
    console.log(`  ok    ${name}  ${detail}`);
  } catch (error) {
    const message = error.name === "TimeoutError" ? `no answer in ${TIMEOUT_MS / 1000} s` : error.message;
    results.push({ ok: false, name, detail: message });
    console.log(`  FAIL  ${name}  ${message}`);
  }
}

console.log(`Smoke test: ${base}${origin ? `  (CORS for ${origin})` : ""}\n`);

await check("health", async () => {
  const { body, ms } = await json("/api/health");
  if (body.status !== "ok") throw new Error(`status ${body.status}`);
  return `${body.status}, mode ${body.mode}, git ${body.git_sha} (${ms} ms)`;
});

for (const t of targets) {
  await check(`resolve ${t.name}`, async () => {
    const { body, ms } = await json(`/api/resolve?name=${encodeURIComponent(t.name)}`);
    if (body.target_key !== t.key) throw new Error(`target_key ${body.target_key}, expected ${t.key}`);
    return `${t.key} (${ms} ms)`;
  });

  await check(`frames ${t.name} D${detector}`, async () => {
    const query = new URLSearchParams({ ra: t.ra, dec: t.dec, target_key: t.key, detector });
    const { body, ms } = await json(`/api/frames?${query}`);
    if (body.frames.length === 0) throw new Error(`no frames (${body.warnings.join(", ")})`);
    const first = body.frames[0];
    const imageMs = (await png(first.png)) + (await png(first.diff_png));
    const marker = first.predicted_px ? "crosshair" : "no crosshair";
    const few = body.frames.length < 3 ? ", FEW_FRAMES" : "";
    return `${body.frames.length} frames${few}, grid ${body.grid.width}x${body.grid.height}, ${marker} (${ms} ms + PNG ${imageMs} ms)`;
  });
}

const failed = results.filter((r) => !r.ok).length;
console.log(`\n${results.length - failed}/${results.length} checks passed.`);
process.exit(failed ? 1 : 0);
