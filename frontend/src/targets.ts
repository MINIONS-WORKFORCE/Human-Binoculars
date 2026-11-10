// The five challenge targets with the API's target_key values.
// Barnard's position follows shared/api-contract/frontend-guide.md; the others are
// SIMBAD J2000 positions from members/duy-hoang/coords/targets.js.
// Replace with shared/targets.json once it is published.
export interface TargetPreset {
  key: string;
  name: string;
  ra: number;
  dec: number;
}

export const TARGET_PRESETS: TargetPreset[] = [
  { key: "barnard", name: "Barnard's Star", ra: 269.4521, dec: 4.6934 },
  { key: "wise0855", name: "WISE 0855-0714", ra: 133.8189, dec: -7.247 },
  { key: "epsindib", name: "Epsilon Indi B", ra: 331.0441, dec: -56.7828 },
  { key: "rwaur", name: "RW Aurigae", ra: 76.9565, dec: 30.4014 },
  { key: "rdra", name: "R Draconis", ra: 248.1676, dec: 66.755 },
];

export const DETECTORS = [1, 2, 3, 4, 5, 6] as const;
