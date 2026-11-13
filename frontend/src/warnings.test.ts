import { describe, expect, it } from "vitest";
import { describeWarning } from "./warnings";

describe("describeWarning", () => {
  it("has a sentence for every code in the contract", () => {
    for (const code of [
      "SATURATION_POSSIBLE",
      "FEW_FRAMES",
      "TRUNCATED",
      "MIXED_WAVELENGTH",
      "TARGET_OUTSIDE_COVERAGE",
    ]) {
      const text = describeWarning(code);
      expect(text).not.toContain(code);
      expect(text.endsWith(".")).toBe(true);
    }
  });

  it("shows an unknown code instead of hiding it", () => {
    expect(describeWarning("SOMETHING_NEW")).toContain("SOMETHING_NEW");
  });
});
