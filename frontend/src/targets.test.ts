import { describe, expect, it } from "vitest";
import { findPresetForTarget, TARGET_PRESETS } from "./targets";

describe("TARGET_PRESETS", () => {
  it("contains exactly the five challenge targets", () => {
    expect(TARGET_PRESETS).toHaveLength(5);
    const keys = TARGET_PRESETS.map((t) => t.key).sort();
    expect(keys).toEqual(["barnard", "epsindib", "rdra", "rwaur", "wise0855"]);
  });

  it("provides a one-sentence English conclusion for each target", () => {
    for (const target of TARGET_PRESETS) {
      expect(target.conclusion).toBeDefined();
      expect(typeof target.conclusion).toBe("string");
      expect(target.conclusion.trim().length).toBeGreaterThan(20);
      expect(target.conclusion.trim().endsWith(".")).toBe(true);
    }
  });

  it("includes dipole signature in Barnard's Star conclusion", () => {
    const barnard = TARGET_PRESETS.find((t) => t.key === "barnard");
    expect(barnard?.conclusion).toContain("dipole");
  });
});

describe("findPresetForTarget", () => {
  it("matches target by target_key", () => {
    const preset = findPresetForTarget({
      target_key: "barnard",
      ra: 269.4521,
      dec: 4.6934,
    });
    expect(preset?.name).toBe("Barnard's Star");
  });

  it("matches target by name", () => {
    const preset = findPresetForTarget({
      name: "WISE 0855",
      ra: 133.8,
      dec: -7.2,
    });
    expect(preset?.key).toBe("wise0855");
  });

  it("matches target by coordinates within 0.05 degrees", () => {
    const preset = findPresetForTarget({
      ra: 269.46,
      dec: 4.70,
    });
    expect(preset?.key).toBe("barnard");
  });

  it("returns null for unknown coordinates", () => {
    const preset = findPresetForTarget({
      ra: 10.0,
      dec: 20.0,
    });
    expect(preset).toBeNull();
  });
});
