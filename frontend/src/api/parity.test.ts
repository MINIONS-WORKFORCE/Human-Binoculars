// Checks that the MSW mock answers exactly like the real backend, so a page that
// works on mocks also works on the API. Skipped unless a backend is running:
//   LIVE_API_URL=http://127.0.0.1:8000 npx vitest run src/api/parity.test.ts
import { bypass, getResponse } from "msw";
import { describe, expect, it } from "vitest";
import { handlers } from "../mocks/handlers";

const live = process.env.LIVE_API_URL;

// Every frames / photometry / astrometry rule the UI relies on, plus each error code
// the fixture backend can produce.
const CASES = [
  "/api/health",
  "/api/resolve?name=Barnard%27s%20Star",
  "/api/resolve?name=Vega",
  "/api/resolve",
  "/api/frames?ra=269.4521&dec=4.6934&detector=6&target_key=barnard",
  "/api/frames?ra=269.4521&dec=4.6934",
  "/api/frames?ra=10&dec=-20&detector=2&size=0.3&max_frames=1",
  "/api/frames?ra=10&dec=-20&max_frames=2&target_key=rdra",
  "/api/frames?ra=360&dec=0",
  "/api/frames?ra=abc&dec=0",
  "/api/frames?dec=0",
  "/api/frames?ra=1&dec=91&detector=7",
  "/api/frames?ra=1&dec=1&detector=7",
  "/api/frames?ra=1&dec=1&detector=2.5",
  "/api/frames?ra=1&dec=1&size=0.01",
  "/api/frames?ra=1&dec=1&max_frames=0",
  "/api/frames?ra=1&dec=1&target_key=nope",
  "/api/frames/not-published.png",
  "/api/frames/not-published/diff.png",
  "/api/photometry?ra=248.1676&dec=66.755&target_key=rdra",
  "/api/photometry?ra=248.1676&dec=66.755&detector=3",
  "/api/photometry?ra=1&dec=1&aperture_arcsec=0",
  "/api/astrometry?ra=269.4521&dec=4.6934&target_key=barnard",
  "/api/astrometry?ra=269.4521&dec=4.6934&detector=2",
];

/** Frame ids hash the query differently on each side; git_sha is environment data. */
function normalize(body: unknown): unknown {
  const text = JSON.stringify(body)
    .replace(/fixture-[0-9a-f]+-/g, "fixture-ID-")
    .replace(/"git_sha":"[^"]*"/, '"git_sha":"SHA"');
  return JSON.parse(text);
}

async function snapshot(response: Response) {
  const type = response.headers.get("content-type") ?? "";
  const body = type.includes("json") ? normalize(await response.json()) : type;
  return { status: response.status, body };
}

describe.skipIf(!live)("MSW mock matches the live backend", () => {
  it.each(CASES)("%s", async (path) => {
    const url = new URL(path, live).href;
    const real = await fetch(bypass(url));
    const mocked = await getResponse(handlers, new Request(url));
    expect(mocked, "no MSW handler").toBeDefined();
    expect(await snapshot(mocked!)).toEqual(await snapshot(real));
  });
});
