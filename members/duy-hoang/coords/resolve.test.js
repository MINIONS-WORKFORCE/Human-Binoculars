import { describe, expect, it, vi } from "vitest";
import { CoordError } from "./parse.js";
import { locate, resolveName } from "./resolve.js";
import { TARGETS } from "./targets.js";

// A fake fetch that answers like MAST Name Lookup.
function mastReturning(resolvedCoordinate) {
  return vi.fn(async () => ({
    ok: true,
    status: 200,
    json: async () => ({ resolvedCoordinate, status: "" }),
  }));
}

const M31 = {
  canonicalName: "MESSIER 031",
  ra: 10.684708333333,
  decl: 41.26875,
  objectType: "G",
  resolver: "NED",
};

async function expectError(promise, code) {
  const error = await promise.catch((e) => e);
  expect(error).toBeInstanceOf(CoordError);
  expect(error.code).toBe(code);
}

describe("resolveName: local targets", () => {
  it.each([
    ["Barnard's Star", "barnard"],
    ["barnards star", "barnard"],
    ["Barnard", "barnard"], // online this is NGC 6822, a galaxy
    ["eps Ind B", "eps-ind-b"], // online this is the planet eps Ind b
    ["Epsilon Indi B", "eps-ind-b"],
    ["WISE 0855", "wise-0855"],
    ["wise 0855-0714", "wise-0855"],
    ["RW Aur", "rw-aur"],
    ["  R   Draconis ", "r-dra"],
  ])("%j -> %s without calling MAST", async (input, id) => {
    const fetch = mastReturning([]);
    const target = TARGETS.find((t) => t.id === id);

    const result = await resolveName(input, { fetch });

    expect(result).toMatchObject({
      raDeg: target.raDeg,
      decDeg: target.decDeg,
      name: target.name,
      source: "local",
      epoch: 2000,
    });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("gives the brown dwarf pair for eps Ind B, not the planet at the host star", async () => {
    const result = await resolveName("eps Ind B", { fetch: mastReturning([]) });
    expect(result.raDeg).toBeCloseTo(331.0441, 3);
    expect(result.objectType).toMatch(/brown dwarf/i);
  });
});

describe("resolveName: MAST", () => {
  it("asks MAST for other names and reads the answer", async () => {
    const fetch = mastReturning([M31]);

    const result = await resolveName("M31", {
      fetch,
      endpoint: "https://example.test/invoke",
    });

    expect(result).toEqual({
      raDeg: M31.ra,
      decDeg: M31.decl,
      name: "MESSIER 031",
      objectType: "G",
      source: "mast",
      epoch: 2000,
    });
    const [url, init] = fetch.mock.calls[0];
    expect(url).toBe("https://example.test/invoke");
    expect(init.method).toBe("POST");
    const request = JSON.parse(
      decodeURIComponent(init.body.replace(/^request=/, "")),
    );
    expect(request).toEqual({
      service: "Mast.Name.Lookup",
      params: { input: "M31", format: "json" },
    });
  });

  it("uses the Vite proxy path by default", async () => {
    const fetch = mastReturning([M31]);
    await resolveName("M31", { fetch });
    expect(fetch.mock.calls[0][0]).toBe("/mast/api/v0/invoke");
  });

  it("reports an unknown name", async () => {
    await expectError(
      resolveName("nonexistent zzz", { fetch: mastReturning([]) }),
      "NAME_NOT_FOUND",
    );
  });

  it("reports a network failure", async () => {
    const fetch = vi.fn(async () => {
      throw new TypeError("fetch failed");
    });
    await expectError(resolveName("M31", { fetch }), "RESOLVER_UNAVAILABLE");
  });

  it("reports an HTTP error", async () => {
    const fetch = vi.fn(async () => ({
      ok: false,
      status: 503,
      json: async () => ({}),
    }));
    await expectError(resolveName("M31", { fetch }), "RESOLVER_UNAVAILABLE");
  });

  it("rejects an empty name", async () => {
    await expectError(
      resolveName("  ", { fetch: mastReturning([M31]) }),
      "EMPTY",
    );
  });
});

describe("locate: WISE 0855 in every supported form", () => {
  // The challenge position (astropy) for the three coordinate formats.
  it.each([
    ["133.79512916666664 -7.245147222222222"],
    ["08h55m10.831s -07d14m42.53s"],
    ["08:55:10.831 -07:14:42.53"],
    ["08 55 10.831 -07 14 42.53"],
  ])("%j is read as coordinates, not looked up", async (input) => {
    const fetch = mastReturning([M31]);

    const result = await locate(input, { fetch });

    expect(result.raDeg).toBeCloseTo(133.79512917, 6);
    expect(result.decDeg).toBeCloseTo(-7.24514722, 6);
    expect(result).toMatchObject({ source: "input", name: null });
    expect(fetch).not.toHaveBeenCalled();
  });

  // The name gives the catalog J2000 position from targets.js, about 85" from the
  // challenge position, which is for a later epoch.
  it("the name gives the local target without calling MAST", async () => {
    const fetch = mastReturning([M31]);
    const target = TARGETS.find((t) => t.id === "wise-0855");

    const result = await locate("WISE 0855", { fetch });

    expect(result).toMatchObject({
      raDeg: target.raDeg,
      decDeg: target.decDeg,
      name: "WISE 0855-0714",
      source: "local",
      epoch: 2000,
    });
    expect(fetch).not.toHaveBeenCalled();
  });
});

describe("locate", () => {
  it("parses coordinates without calling MAST", async () => {
    const fetch = mastReturning([M31]);

    const result = await locate("08h55m10.831s-7d14m42.53s", { fetch });

    expect(result.raDeg).toBeCloseTo(133.79512917, 6);
    expect(result.decDeg).toBeCloseTo(-7.24514722, 6);
    expect(result).toMatchObject({ source: "input", name: null, epoch: null });
    expect(fetch).not.toHaveBeenCalled();
  });

  it("reports bad coordinates instead of looking them up as a name", async () => {
    const fetch = mastReturning([M31]);
    await expectError(
      locate("25h00m00s +10d00m00s", { fetch }),
      "RA_OUT_OF_RANGE",
    );
    expect(fetch).not.toHaveBeenCalled();
  });

  it("resolves names", async () => {
    const result = await locate("M31", { fetch: mastReturning([M31]) });
    expect(result.source).toBe("mast");
  });
});
