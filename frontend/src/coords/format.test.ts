import { describe, expect, it } from "vitest";
import { formatDec, formatDegrees, formatRa } from "./format";
import { parseCoordinates } from "./parse";

// Degrees are the astropy values used in parse.test.js.
describe("formatRa", () => {
  it.each([
    [133.79512916666664, "08h55m10.83s"],
    [269.4520833333333, "17h57m48.50s"],
    [76.95641666666666, "05h07m49.54s"],
    [0, "00h00m00.00s"],
    [359.99999583333334, "00h00m00.00s"], // 23h59m59.999s rounds up and wraps
    [360, "00h00m00.00s"],
  ])("%s -> %s", (deg, text) => {
    expect(formatRa(deg)).toBe(text);
  });

  it("carries rounded seconds into the minute", () => {
    // 00h00m59.996s
    expect(formatRa((59.996 / 3600) * 15)).toBe("00h01m00.00s");
  });

  it("takes the number of decimals", () => {
    expect(formatRa(133.79512916666664, 3)).toBe("08h55m10.831s");
    expect(formatRa(133.79512916666664, 0)).toBe("08h55m11s");
  });
});

describe("formatDec", () => {
  it.each([
    [-7.245147222222222, "−07°14′42.5″"],
    [4.693388888888889, "+04°41′36.2″"],
    [66.75497222222222, "+66°45′17.9″"],
    [-0.5, "−00°30′00.0″"],
    [90, "+90°00′00.0″"],
    [-90, "−90°00′00.0″"],
    [0, "+00°00′00.0″"],
    [-0.000001, "+00°00′00.0″"], // rounds to zero: no minus sign
  ])("%s -> %s", (deg, text) => {
    expect(formatDec(deg)).toBe(text);
  });

  it("carries rounded seconds into the minute", () => {
    expect(formatDec(-(59.96 / 3600))).toBe("−00°01′00.0″");
  });

  it("writes letters that parseCoordinates reads", () => {
    expect(
      formatDec(-7.245147222222222, { style: "letters", decimals: 2 }),
    ).toBe("-07d14m42.53s");
  });
});

describe("round trip through parseCoordinates", () => {
  it.each([
    [133.79512916666664, -7.245147222222222],
    [269.4520833333333, 4.693388888888889],
    [331.0441666666666, -56.782777777777774],
    [0, -0.5],
    [187.70591666666664, 90],
  ])("%s %s", (raDeg, decDeg) => {
    const text = `${formatRa(raDeg, 4)} ${formatDec(decDeg, { style: "letters", decimals: 3 })}`;
    const parsed = parseCoordinates(text);
    expect(parsed.raDeg).toBeCloseTo(raDeg, 6);
    expect(parsed.decDeg).toBeCloseTo(decDeg, 6);
  });
});

describe("formatDegrees", () => {
  it.each([
    [269.45208, {}, "269.4521°"],
    [-7.245147, { signed: true }, "−7.2451°"],
    [4.6934, { signed: true }, "+4.6934°"],
    [-0.00001, { signed: true }, "+0.0000°"], // rounds to zero: no minus sign
    [133.795129, { decimals: 2 }, "133.80°"],
  ])("%s %j -> %s", (deg, options, text) => {
    expect(formatDegrees(deg, options)).toBe(text);
  });
});
