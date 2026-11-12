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
): TargetPreset {
  const { ra, dec, simbadId } = position(key);
  return { key, name, ra, dec, aliases: [...aliases, simbadId], objectType };
}

export const TARGET_PRESETS: TargetPreset[] = [
  preset(
    "barnard",
    "Barnard's Star",
    ["Barnards Star", "Barnard Star", "Barnard", "GJ 699"],
    "Red dwarf, largest proper motion in the sky",
  ),
  preset(
    "wise0855",
    "WISE 0855-0714",
    ["WISE 0855", "WISE J085510.83-071442.5", "WISEA J085510.74-071442.5"],
    "Coldest known brown dwarf",
  ),
  preset(
    "epsindib",
    "Epsilon Indi B",
    ["eps Ind B", "eps Indi B", "GJ 845 B", "Gl 845 B"],
    "Brown dwarf pair (Ba + Bb)",
  ),
  preset("rwaur", "RW Aurigae", ["RW Aur"], "Young variable star (T Tauri)"),
  preset("rdra", "R Draconis", ["R Dra"], "Mira variable"),
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
