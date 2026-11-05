import { describe, expect, it } from "vitest";
import { CoordError, looksLikeCoordinates, parseCoordinates } from "./parse.js";

// Expected values come from astropy: Angle("08h55m10.831s").to(u.deg), etc.
const WISE_0855 = { raDeg: 133.79512916666664, decDeg: -7.245147222222222 };

function expectCoords(input, raDeg, decDeg) {
  const result = parseCoordinates(input);
  expect(result.raDeg).toBeCloseTo(raDeg, 6);
  expect(result.decDeg).toBeCloseTo(decDeg, 6);
}

function expectError(input, code) {
  let error;
  try {
    parseCoordinates(input);
  } catch (e) {
    error = e;
  }
  expect(error).toBeInstanceOf(CoordError);
  expect(error.code).toBe(code);
}

describe("parseCoordinates: h/m/s d/m/s", () => {
  it.each([
    ["08h55m10.831s-7d14m42.53s"], // as written in the challenge, no space
    ["08h55m10.831s -7d14m42.53s"],
    ["08h55m10.831s, -7d14m42.53s"],
    ["8h 55m 10.831s  -7d 14m 42.53s"],
    ["  08H55M10.831S -7D14M42.53S  "],
    ["08h55m10.831s −7d14m42.53s"], // Unicode minus sign
  ])("reads WISE 0855 from %j", (input) => {
    expectCoords(input, WISE_0855.raDeg, WISE_0855.decDeg);
  });

  it.each([
    ["17h57m48.5s +4d41m36.2s", 269.4520833333333, 4.693388888888889],
    ["05h07m49.54s +30d24m05.2s", 76.95641666666666, 30.401444444444444],
    ["16h32m40.23s +66d45m17.9s", 248.16762500000002, 66.75497222222222],
    ["22h04m10.6s -56d46m58s", 331.0441666666666, -56.782777777777774],
    ["12h30m49.42s 12d23m28.0s", 187.70591666666664, 12.39111111111111], // no sign = positive
    ["00h00m00s +00d00m00s", 0, 0],
    ["23h59m59.999s +90d00m00s", 359.99999583333334, 90],
    ["00h00m00s -90d00m00s", 0, -90],
  ])("%s", (input, raDeg, decDeg) => {
    expectCoords(input, raDeg, decDeg);
  });

  it("keeps the sign when degrees are zero", () => {
    expectCoords("00h00m00s -0d30m00s", 0, -0.5);
  });
});

describe("parseCoordinates: decimal degrees", () => {
  it.each([
    ["133.795 -7.245", 133.795, -7.245],
    ["133.795, -7.245", 133.795, -7.245],
    ["133.795,-7.245", 133.795, -7.245],
    ["269.452 +4.693", 269.452, 4.693],
    ["0 0", 0, 0],
    ["359.9999 -90", 359.9999, -90],
    [".5 -.25", 0.5, -0.25],
    ["10 −45", 10, -45], // Unicode minus sign
  ])("%j", (input, raDeg, decDeg) => {
    expectCoords(input, raDeg, decDeg);
  });

  it("returns 0 rather than -0", () => {
    expect(Object.is(parseCoordinates("10 -0").decDeg, 0)).toBe(true);
  });
});

describe("parseCoordinates: errors", () => {
  it.each([
    ["", "EMPTY"],
    ["   ", "EMPTY"],
    ["24h00m00s +00d00m00s", "RA_OUT_OF_RANGE"],
    ["360 0", "RA_OUT_OF_RANGE"],
    ["-1 0", "RA_OUT_OF_RANGE"],
    ["0 91", "DEC_OUT_OF_RANGE"],
    ["0 -90.5", "DEC_OUT_OF_RANGE"],
    ["00h00m00s +91d00m00s", "DEC_OUT_OF_RANGE"],
    ["00h00m00s +90d00m01s", "DEC_OUT_OF_RANGE"],
    ["00h61m00s +00d00m00s", "MINUTES_OUT_OF_RANGE"],
    ["00h00m00s +00d60m00s", "MINUTES_OUT_OF_RANGE"],
    ["00h00m60s +00d00m00s", "SECONDS_OUT_OF_RANGE"],
    ["00h00m00s +00d00m60.0s", "SECONDS_OUT_OF_RANGE"],
    ["08h55m10.831s -7.245", "UNSUPPORTED_FORMAT"], // mixed forms
    ["08:55:10.831 -07:14:42.53", "UNSUPPORTED_FORMAT"], // colons: not yet
    ["133.795", "UNSUPPORTED_FORMAT"], // Dec missing
    ["133.795 -7.245 1", "UNSUPPORTED_FORMAT"],
    ["Barnard's Star", "UNSUPPORTED_FORMAT"],
  ])("%j -> %s", (input, code) => {
    expectError(input, code);
  });
});

describe("looksLikeCoordinates", () => {
  it.each([
    ["133.795 -7.245", true],
    ["08h55m10.831s-7d14m42.53s", true],
    ["25h00m00s +10d00m00s", true], // invalid, but still coordinates
    ["-7 5", true],
    ["Barnard's Star", false],
    ["M31", false],
    ["R Dra", false],
    ["2MASS J22041052-5646577", false],
    ["", false],
  ])("%j -> %s", (input, expected) => {
    expect(looksLikeCoordinates(input)).toBe(expected);
  });
});
