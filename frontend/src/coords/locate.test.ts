import { describe, expect, it } from "vitest";
import { createApiClient } from "../api/client";
import { CoordError } from "./parse";
import { locate, previewInput } from "./locate";
import { TARGET_PRESETS } from "../targets";

const api = createApiClient("http://api.test");

describe("previewInput (no network, runs on every keystroke)", () => {
  it("is empty for blank input", () => {
    expect(previewInput("   ")).toEqual({ status: "empty" });
  });

  it("parses decimal degrees", () => {
    expect(previewInput("269.4521 4.6934")).toEqual({
      status: "ready",
      location: {
        kind: "coordinates",
        format: "decimal",
        raDeg: 269.4521,
        decDeg: 4.6934,
      },
    });
  });

  it("parses hours/degrees", () => {
    const preview = previewInput("08h55m10.831s -7d14m42.53s");
    expect(preview).toMatchObject({
      status: "ready",
      location: { kind: "coordinates", format: "sexagesimal" },
    });
    if (preview.status !== "ready") throw new Error("not ready");
    expect(preview.location.raDeg).toBeCloseTo(133.795129, 6);
    expect(preview.location.decDeg).toBeCloseTo(-7.245147, 6);
  });

  it.each(["Barnard's Star", "barnards star", "GJ 699", "R Dra", "wise0855"])(
    "finds the preset %j offline",
    (input) => {
      expect(previewInput(input)).toMatchObject({
        status: "ready",
        location: { kind: "name", source: "local" },
      });
    },
  );

  it("returns the preset's name, key and both coordinates", () => {
    expect(previewInput("eps Ind B")).toEqual({
      status: "ready",
      location: {
        kind: "name",
        source: "local",
        name: "Epsilon Indi B",
        targetKey: "epsindib",
        objectType: "Brown dwarf pair (Ba + Bb)",
        // shared/targets.json, SIMBAD ICRS at epoch J2000.
        raDeg: 331.04414658852124,
        decDeg: -56.78284419511611,
      },
    });
  });

  it("finds every preset by its SIMBAD id from shared/targets.json", () => {
    for (const id of ["NAME Barnard's star", "R Dra", "RW Aur"]) {
      expect(previewInput(id)).toMatchObject({ status: "ready" });
    }
  });

  it("agrees with the API resolver on every preset position", async () => {
    // The mock mirrors the backend's /api/resolve, which reads the same table.
    for (const t of TARGET_PRESETS) {
      const resolved = await api.resolve(t.key);
      expect([resolved.ra, resolved.dec]).toEqual([t.ra, t.dec]);
    }
  });

  it("explains invalid coordinates", () => {
    const preview = previewInput("400 10");
    expect(preview.status).toBe("invalid");
    if (preview.status !== "invalid") throw new Error("not invalid");
    expect(preview.error.code).toBe("RA_OUT_OF_RANGE");
  });

  it("leaves other names for the lookup on submit", () => {
    expect(previewInput("M31")).toEqual({
      status: "needs-lookup",
      name: "M31",
    });
  });
});

describe("locate (resolves names through /api/resolve)", () => {
  it("passes coordinates and presets through without a request", async () => {
    const noNetwork = () => Promise.reject(new Error("should not be called"));
    await expect(locate("10 20", noNetwork)).resolves.toMatchObject({
      kind: "coordinates",
    });
    await expect(locate("RW Aur", noNetwork)).resolves.toMatchObject({
      name: "RW Aurigae",
    });
  });

  it("asks the API for names the presets do not know and keeps its target key", async () => {
    // The typed text is unknown to the presets, so the request goes to the API
    // (pointed at a name the fixture resolver knows).
    const asked: string[] = [];
    const location = await locate("Some Alias", (name) => {
      asked.push(name);
      return api.resolve("Barnard's Star");
    });
    expect(asked).toEqual(["Some Alias"]);
    expect(location).toEqual({
      kind: "name",
      source: "api",
      name: "Barnard's Star",
      targetKey: "barnard",
      objectType: null,
      // shared/targets.json, SIMBAD ICRS at epoch J2000.
      raDeg: 269.45207695861876,
      decDeg: 4.693364966576667,
    });
  });

  it("turns 404 UNKNOWN_TARGET into NAME_NOT_FOUND", async () => {
    const error = await locate("Planet X", (name) => api.resolve(name)).catch(
      (e: unknown) => e,
    );
    expect(error).toBeInstanceOf(CoordError);
    expect((error as CoordError).code).toBe("NAME_NOT_FOUND");
    expect((error as CoordError).message).toMatch(/Planet X/);
  });

  it("turns other failures into RESOLVER_UNAVAILABLE", async () => {
    const error = await locate("M31", () =>
      Promise.reject(new TypeError("Failed to fetch")),
    ).catch((e: unknown) => e);
    expect((error as CoordError).code).toBe("RESOLVER_UNAVAILABLE");
  });

  it("rejects empty and invalid input with its code", async () => {
    const resolve = (name: string) => api.resolve(name);
    await expect(locate("", resolve)).rejects.toMatchObject({ code: "EMPTY" });
    await expect(locate("10 95", resolve)).rejects.toMatchObject({
      code: "DEC_OUT_OF_RANGE",
    });
  });
});
