import { beforeEach, describe, expect, it, vi } from "vitest";
import { SOURCE_IDS } from "./query.js";
import {
  SOURCES,
  UNWISE_LAYERS,
  clearCutoutCache,
  sourceById,
  unwiseCutoutUrl,
} from "./sources.js";

const WISE_0855 = { raDeg: 133.79512916666664, decDeg: -7.245147222222222 };
const BARNARD = { raDeg: 269.4520769586187, decDeg: 4.6933649665767 };

beforeEach(() => clearCutoutCache());

describe("unwiseCutoutUrl", () => {
  it("asks Legacy Survey for a cutout at the position", () => {
    const url = new URL(
      unwiseCutoutUrl({ ...WISE_0855, fovArcmin: 5, layer: "unwise-neo7" }),
    );
    expect(url.origin + url.pathname).toBe(
      "https://www.legacysurvey.org/viewer/jpeg-cutout",
    );
    expect(Object.fromEntries(url.searchParams)).toEqual({
      ra: "133.795129",
      dec: "-7.245147",
      layer: "unwise-neo7",
      pixscale: "2.75",
      size: "109", // 5' = 300" / 2.75" per pixel
    });
  });

  it.each([
    [0.1, "16"],
    [2, "44"],
    [20, "436"],
    [60, "512"],
  ])("fov %s arcmin -> size %s px (clamped to 16..512)", (fovArcmin, size) => {
    const url = new URL(
      unwiseCutoutUrl({ ...WISE_0855, fovArcmin, layer: "x" }),
    );
    expect(url.searchParams.get("size")).toBe(size);
  });
});

describe("unwise source", () => {
  const unwise = sourceById("unwise");
  const okResponse = () => ({
    ok: true,
    status: 200,
    blob: async () => new Blob(["jpeg"]),
  });
  const decode = vi.fn(async () => ({ width: 109, height: 109 }));

  it("loads one frame per layer, oldest release first", async () => {
    const fetch = vi.fn(async () => okResponse());
    const signal = new AbortController().signal;

    const frames = await unwise.load(
      { ...WISE_0855, fovArcmin: 5 },
      { signal, fetch, decode },
    );

    expect(frames.map((f) => f.name)).toEqual(UNWISE_LAYERS);
    expect(frames[0]).toMatchObject({ width: 109, height: 109 });
    expect(fetch).toHaveBeenCalledTimes(4);
    for (const [url, init] of fetch.mock.calls) {
      expect(url).toContain("ra=133.795129");
      expect(init.signal).toBe(signal);
    }
  });

  it("fails when a cutout fails", async () => {
    const fetch = vi.fn(async (url) =>
      url.includes("neo6") ? { ok: false, status: 500 } : okResponse(),
    );
    await expect(
      unwise.load({ ...WISE_0855, fovArcmin: 5 }, { fetch, decode }),
    ).rejects.toThrow("unwise-neo6: HTTP 500");
  });

  it("fetches one cutout at a time", async () => {
    let inFlight = 0;
    let most = 0;
    const fetch = vi.fn(async () => {
      most = Math.max(most, ++inFlight);
      await Promise.resolve();
      inFlight--;
      return okResponse();
    });
    await unwise.load({ ...BARNARD, fovArcmin: 2 }, { fetch, decode });
    expect(most).toBe(1);
  });

  it("retries after HTTP 429, then gives up", async () => {
    const sleep = vi.fn(async () => {});
    let calls = 0;
    const fetch = vi.fn(async () =>
      ++calls <= 2 ? { ok: false, status: 429 } : okResponse(),
    );

    const frames = await unwise.load(
      { ...BARNARD, fovArcmin: 5 },
      { fetch, decode, sleep },
    );
    expect(frames).toHaveLength(4);
    expect(sleep.mock.calls.map(([ms]) => ms)).toEqual([1500, 4000]);

    const alwaysBusy = vi.fn(async () => ({ ok: false, status: 429 }));
    await expect(
      unwise.load(
        { ...BARNARD, fovArcmin: 10 },
        { fetch: alwaysBusy, decode, sleep },
      ),
    ).rejects.toThrow("unwise-neo4: HTTP 429");
    expect(alwaysBusy).toHaveBeenCalledTimes(3);
  });

  it("reuses cutouts it already fetched", async () => {
    const fetch = vi.fn(async () => okResponse());
    const position = { ...BARNARD, fovArcmin: 20 };
    await unwise.load(position, { fetch, decode });
    await unwise.load(position, { fetch, decode });
    expect(fetch).toHaveBeenCalledTimes(4);
  });
});

describe("SOURCES", () => {
  it("every enabled source can be picked in the URL", () => {
    const enabled = SOURCES.filter((s) => s.enabled).map((s) => s.id);
    expect(enabled).toEqual(SOURCE_IDS);
  });

  it("the SPHEREx source is listed but disabled", async () => {
    const spherex = sourceById("spherex");
    expect(spherex.enabled).toBe(false);
    await expect(spherex.load({})).rejects.toThrow(/not available/);
  });
});
