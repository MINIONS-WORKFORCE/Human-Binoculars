import { describe, expect, it } from "vitest";
import { http, HttpResponse } from "msw";
import { server } from "../test/setup";
import { ApiError, createApiClient, friendlyMessage } from "./client";

const BASE = "http://api.test";
const api = createApiClient(BASE);
const barnard = {
  ra: 269.4521,
  dec: 4.6934,
  targetKey: "barnard",
  detector: 6,
};

async function failure(promise: Promise<unknown>): Promise<ApiError> {
  const error = await promise.then(
    () => undefined,
    (e: unknown) => e,
  );
  expect(error).toBeInstanceOf(ApiError);
  return error as ApiError;
}

describe("api.frames against the MSW mock", () => {
  it("returns the three sample frames with the request echoed back", async () => {
    const data = await api.frames(barnard);
    expect(data.api_version).toBe("0.1");
    expect(data.frames).toHaveLength(3);
    expect(data.target).toEqual({
      ra: 269.4521,
      dec: 4.6934,
      target_key: "barnard",
      name: "Barnard's Star",
    });
    expect(data.detector).toBe(6);
    expect(data.reference_frame_id).toBe(data.frames[0].id);
    expect(data.frames.map((f) => f.predicted_px)).toEqual([
      [17, 19],
      [19, 19],
      [21, 19],
    ]);
  });

  it("drops predicted_px when no target_key is sent, like the backend", async () => {
    const data = await api.frames({ ra: 10, dec: 20 });
    expect(data.frames.every((f) => f.predicted_px === null)).toBe(true);
    expect(data.target.name).toBeNull();
  });

  it("truncates with max_frames and reports the warnings", async () => {
    const data = await api.frames({ ...barnard, maxFrames: 1 });
    expect(data.frames).toHaveLength(1);
    expect(data.warnings).toEqual(["TRUNCATED", "FEW_FRAMES"]);
  });

  it("serves each frame's PNG and difference PNG after /api/frames", async () => {
    const data = await api.frames(barnard);
    for (const frame of data.frames) {
      for (const path of [frame.png, frame.diff_png]) {
        const response = await fetch(api.imageUrl(path));
        expect(response.status).toBe(200);
        expect(response.headers.get("content-type")).toBe("image/png");
        const bytes = new Uint8Array(await response.arrayBuffer());
        expect(
          [...bytes.slice(1, 4)].map((b) => String.fromCharCode(b)).join(""),
        ).toBe("PNG");
      }
    }
  });

  it("returns FRAME_NOT_FOUND for an image id it never published", async () => {
    const response = await fetch(`${BASE}/api/frames/does-not-exist.png`);
    expect(response.status).toBe(404);
    expect((await response.json()).error.code).toBe("FRAME_NOT_FOUND");
  });
});

describe("errors become ApiError with a readable message", () => {
  it("unknown target -> 404 UNKNOWN_TARGET", async () => {
    const error = await failure(
      api.frames({ ra: 1, dec: 2, targetKey: "planet-x" }),
    );
    expect(error.status).toBe(404);
    expect(error.code).toBe("UNKNOWN_TARGET");
    expect(friendlyMessage(error)).toMatch(/not in our list/);
  });

  it("RA out of range -> 400 BAD_COORDS", async () => {
    const error = await failure(api.frames({ ra: 360, dec: 0 }));
    expect(error.status).toBe(400);
    expect(error.code).toBe("BAD_COORDS");
    expect(error.details).toEqual({ fields: ["ra"] });
  });

  it("detector out of range -> 400 BAD_PARAM", async () => {
    const error = await failure(api.frames({ ra: 10, dec: 10, detector: 7 }));
    expect(error.code).toBe("BAD_PARAM");
  });

  it("server down -> NETWORK", async () => {
    server.use(http.get(`${BASE}/api/frames`, () => HttpResponse.error()));
    const error = await failure(api.frames(barnard));
    expect(error.code).toBe("NETWORK");
    expect(friendlyMessage(error)).toMatch(/not reachable/);
  });

  it("non-JSON failure still gives an ApiError", async () => {
    server.use(
      http.get(
        `${BASE}/api/frames`,
        () => new HttpResponse("Bad Gateway", { status: 502 }),
      ),
    );
    const error = await failure(api.frames(barnard));
    expect(error).toMatchObject({ status: 502, code: "HTTP_ERROR" });
  });
});

describe("other endpoints", () => {
  it("health, resolve, photometry and astrometry answer from api_samples", async () => {
    await expect(api.health()).resolves.toMatchObject({
      status: "ok",
      mode: "fixture",
    });
    await expect(api.resolve("Barnard's Star")).resolves.toMatchObject({
      target_key: "barnard",
    });
    await expect(
      api.photometry({ ra: 248.1676, dec: 66.755, targetKey: "rdra" }),
    ).resolves.toMatchObject({
      variability: null,
    });
    const astrometry = await api.astrometry({ ...barnard, detector: 3 });
    expect(astrometry.points).toEqual([]);
  });
});
