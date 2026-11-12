import { describe, expect, it } from "vitest";
import { buildSearch, fovToSize, parseUrlState } from "./urlState";

describe("parseUrlState", () => {
  it("reads q, fov and det", () => {
    expect(parseUrlState("?q=R+Draconis&fov=5&det=D3")).toEqual({
      q: "R Draconis",
      fov: 5,
      detector: 3,
    });
  });

  it("reads coordinates typed with spaces and a sign", () => {
    expect(parseUrlState("?q=133.7951%20-7.2451").q).toBe("133.7951 -7.2451");
  });

  it("accepts det as a bare number or lowercase", () => {
    expect(parseUrlState("?det=6").detector).toBe(6);
    expect(parseUrlState("?det=d2").detector).toBe(2);
  });

  it("ignores values that are not offered", () => {
    const none = { q: null, fov: null, detector: null };
    expect(parseUrlState("?fov=7&det=D9&q=")).toEqual(none);
    expect(parseUrlState("?fov=abc&det=D0")).toEqual(none);
  });

  it("gives all nulls for an empty query", () => {
    expect(parseUrlState("")).toEqual({ q: null, fov: null, detector: null });
  });
});

describe("buildSearch", () => {
  it("writes only what is set", () => {
    expect(buildSearch({ q: null, fov: null, detector: null })).toBe("");
    expect(buildSearch({ q: "Barnard's Star", fov: null, detector: 6 })).toBe(
      "?q=Barnard%27s+Star&det=D6",
    );
  });

  it("round-trips", () => {
    const state = { q: "269.4521 4.6934", fov: 10 as const, detector: 1 };
    expect(parseUrlState(buildSearch(state))).toEqual(state);
  });
});

describe("fovToSize", () => {
  it("matches the SRS table", () => {
    expect(fovToSize(2)).toBe(0.0333);
    expect(fovToSize(5)).toBe(0.0833);
    expect(fovToSize(10)).toBe(0.1667);
  });
});
