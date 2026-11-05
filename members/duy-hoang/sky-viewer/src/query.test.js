import { describe, expect, it } from "vitest";
import { DEFAULTS, readQuery, writeQuery } from "./query.js";

describe("readQuery", () => {
  it("uses defaults for an empty URL", () => {
    expect(readQuery("")).toEqual(DEFAULTS);
  });

  it("reads all three values", () => {
    expect(readQuery("?q=RW%20Aur&fov=10&src=sample")).toEqual({
      q: "RW Aur",
      fov: 10,
      src: "sample",
    });
  });

  it("accepts + for spaces and an apostrophe", () => {
    expect(readQuery("?q=Barnard's+Star").q).toBe("Barnard's Star");
  });

  it.each([
    ["?fov=7", 5],
    ["?fov=abc", 5],
    ["?fov=-2", 5],
    ["?fov=20", 20],
  ])("fov in %s -> %s", (search, fov) => {
    expect(readQuery(search).fov).toBe(fov);
  });

  it("falls back for an unknown source", () => {
    expect(readQuery("?src=spherex").src).toBe("unwise");
  });
});

describe("writeQuery", () => {
  it("encodes spaces as %20 and keeps the order q, fov, src", () => {
    expect(writeQuery({ q: "Barnard's Star", fov: 5, src: "unwise" })).toBe(
      "?q=Barnard's%20Star&fov=5&src=unwise",
    );
  });

  it.each([
    [{ q: "08h55m10.831s-7d14m42.53s", fov: 2, src: "unwise" }],
    [{ q: "133.795, -7.245", fov: 20, src: "sample" }],
    [{ q: "Barnard's Star & friends", fov: 10, src: "unwise" }],
  ])("round trips %j", (query) => {
    expect(readQuery(writeQuery(query))).toEqual(query);
  });
});
