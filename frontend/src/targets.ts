// The five challenge targets, looked up before any online resolver.
// Positions come from shared/targets.json (SIMBAD ICRS, epoch J2000), the same
// table the backend resolves from, so the page and the API never disagree.
// key is the API's target_key; names, aliases and descriptions are the page's own.
import targetTable from "../../shared/targets.json";

export interface TargetPreset {
  key: string;
  name: string;
  ra: number;
  dec: number;
  aliases: string[];
  objectType: string;
  /** Background science for the target (Hữu Hoàng, PR #50). */
  conclusion: string;
}

/** targets.json ids that differ from the API's target_key (as in catalog.py). */
const TABLE_ID: Record<string, string> = {
  epsindib: "epsilon-indi-b",
  rwaur: "rw-aur",
  rdra: "r-dra",
};

function position(key: string) {
  const id = TABLE_ID[key] ?? key;
  const row = targetTable.targets.find((t) => t.id === id);
  if (!row) throw new Error(`shared/targets.json has no target "${id}"`);
  return {
    ra: row.astrometry.ra_deg,
    dec: row.astrometry.dec_deg,
    simbadId: row.simbad_id,
  };
}

function preset(
  key: string,
  name: string,
  aliases: string[],
  objectType: string,
  conclusion: string,
): TargetPreset {
  const { ra, dec, simbadId } = position(key);
  return {
    key,
    name,
    ra,
    dec,
    aliases: [...aliases, simbadId],
    objectType,
    conclusion,
  };
}

export const TARGET_PRESETS: TargetPreset[] = [
  preset(
    "barnard",
    "Barnard's Star",
    ["Barnards Star", "Barnard Star", "Barnard", "GJ 699"],
    "Red dwarf, largest proper motion in the sky",
    "Barnard's Star exhibits rapid proper motion across observation epochs, producing a pronounced bright–dark dipole signature in difference imaging that directly confirms its transverse motion relative to the background sky.",
  ),
  preset(
    "wise0855",
    "WISE 0855-0714",
    ["WISE 0855", "WISE J085510.83-071442.5", "WISEA J085510.74-071442.5"],
    "Coldest known brown dwarf",
    "WISE 0855 is an ultra-cold sub-stellar brown dwarf whose thermal emission peaks predominantly in SPHEREx mid-infrared Detector 6 (4.5–5.0 µm) with noticeable proper motion displacement across survey visits.",
  ),
  preset(
    "epsindib",
    "Epsilon Indi B",
    ["eps Ind B", "eps Indi B", "GJ 845 B", "Gl 845 B"],
    "Brown dwarf pair (Ba + Bb)",
    "Epsilon Indi B is a nearby benchmark T-dwarf binary companion displaying shared proper motion with the host star and strong atmospheric methane absorption features in SPHEREx channels.",
  ),
  preset(
    "rwaur",
    "RW Aurigae",
    ["RW Aur"],
    "Young variable star (T Tauri)",
    "RW Aurigae is a young T Tauri binary system exhibiting prominent infrared excess and irregular multi-magnitude dimming episodes caused by circumstellar dust occultation.",
  ),
  preset(
    "rdra",
    "R Draconis",
    ["R Dra"],
    "Mira variable",
    "R Draconis is a high-amplitude pulsating Mira variable demonstrating substantial seasonal brightness modulation and saturated core pixels during peak infrared emission.",
  ),
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
        Math.abs(t.ra - target.ra) < 0.05 &&
        Math.abs(t.dec - target.dec) < 0.05,
    ) ?? null
  );
}
