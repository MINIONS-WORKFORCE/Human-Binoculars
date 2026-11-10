// The five challenge targets, looked up before any online resolver.
// key is the API's target_key. Barnard's position follows
// shared/api-contract/frontend-guide.md; the others are SIMBAD J2000 positions
// from members/duy-hoang/coords/targets.js. Replace with shared/targets.json
// once it is published.
export interface TargetPreset {
  key: string;
  name: string;
  ra: number;
  dec: number;
  aliases: string[];
  objectType: string;
}

export const TARGET_PRESETS: TargetPreset[] = [
  {
    key: "barnard",
    name: "Barnard's Star",
    ra: 269.4521,
    dec: 4.6934,
    aliases: ["Barnards Star", "Barnard Star", "Barnard", "GJ 699"],
    objectType: "Red dwarf, largest proper motion in the sky",
  },
  {
    key: "wise0855",
    name: "WISE 0855-0714",
    ra: 133.8189,
    dec: -7.247,
    aliases: [
      "WISE 0855",
      "WISE J085510.83-071442.5",
      "WISEA J085510.74-071442.5",
    ],
    objectType: "Coldest known brown dwarf",
  },
  {
    key: "epsindib",
    name: "Epsilon Indi B",
    ra: 331.0441,
    dec: -56.7828,
    aliases: ["eps Ind B", "eps Indi B", "GJ 845 B", "Gl 845 B"],
    objectType: "Brown dwarf pair (Ba + Bb)",
  },
  {
    key: "rwaur",
    name: "RW Aurigae",
    ra: 76.9565,
    dec: 30.4014,
    aliases: ["RW Aur"],
    objectType: "Young variable star (T Tauri)",
  },
  {
    key: "rdra",
    name: "R Draconis",
    ra: 248.1676,
    dec: 66.755,
    aliases: ["R Dra"],
    objectType: "Mira variable",
  },
];

export const DETECTORS = [1, 2, 3, 4, 5, 6] as const;

/** "Barnard's  star", "barnards star" and "BARNARD’S STAR" all become "barnards star". */
export function normalizeName(name: string): string {
  return String(name ?? "")
    .toLowerCase()
    .replace(/['’]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

const BY_ALIAS = new Map(
  TARGET_PRESETS.flatMap((target) =>
    [target.name, target.key, ...target.aliases].map(
      (alias) => [normalizeName(alias), target] as const,
    ),
  ),
);

/** A preset by its name, key or any alias (case, spaces and apostrophes ignored). */
export function findTarget(name: string): TargetPreset | null {
  return BY_ALIAS.get(normalizeName(name)) ?? null;
}
