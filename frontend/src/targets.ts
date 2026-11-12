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
  conclusion: string;
}

export const TARGET_PRESETS: TargetPreset[] = [
  {
    key: "barnard",
    name: "Barnard's Star",
    ra: 269.4521,
    dec: 4.6934,
    aliases: ["Barnards Star", "Barnard Star", "Barnard", "GJ 699"],
    objectType: "Red dwarf, largest proper motion in the sky",
    conclusion:
      "Barnard's Star exhibits rapid proper motion across observation epochs, producing a pronounced bright–dark dipole signature in difference imaging that directly confirms its transverse motion relative to the background sky.",
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
    conclusion:
      "WISE 0855 is an ultra-cold sub-stellar brown dwarf whose thermal emission peaks predominantly in SPHEREx mid-infrared Detector 6 (4.5–5.0 µm) with noticeable proper motion displacement across survey visits.",
  },
  {
    key: "epsindib",
    name: "Epsilon Indi B",
    ra: 331.0441,
    dec: -56.7828,
    aliases: ["eps Ind B", "eps Indi B", "GJ 845 B", "Gl 845 B"],
    objectType: "Brown dwarf pair (Ba + Bb)",
    conclusion:
      "Epsilon Indi B is a nearby benchmark T-dwarf binary companion displaying shared proper motion with the host star and strong atmospheric methane absorption features in SPHEREx channels.",
  },
  {
    key: "rwaur",
    name: "RW Aurigae",
    ra: 76.9565,
    dec: 30.4014,
    aliases: ["RW Aur"],
    objectType: "Young variable star (T Tauri)",
    conclusion:
      "RW Aurigae is a young T Tauri binary system exhibiting prominent infrared excess and irregular multi-magnitude dimming episodes caused by circumstellar dust occultation.",
  },
  {
    key: "rdra",
    name: "R Draconis",
    ra: 248.1676,
    dec: 66.755,
    aliases: ["R Dra"],
    objectType: "Mira variable",
    conclusion:
      "R Draconis is a high-amplitude pulsating Mira variable demonstrating substantial seasonal brightness modulation and saturated core pixels during peak infrared emission.",
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

/** Matches a target from frames response by key, name, or approximate coordinates. */
export function findPresetForTarget(target: {
  target_key?: string | null;
  name?: string | null;
  ra: number;
  dec: number;
}): TargetPreset | null {
  if (target.target_key) {
    const byKey = TARGET_PRESETS.find((t) => t.key === target.target_key);
    if (byKey) return byKey;
  }
  if (target.name) {
    const byName = findTarget(target.name);
    if (byName) return byName;
  }
  return (
    TARGET_PRESETS.find(
      (t) =>
        Math.abs(t.ra - target.ra) < 0.05 && Math.abs(t.dec - target.dec) < 0.05,
    ) ?? null
  );
}
