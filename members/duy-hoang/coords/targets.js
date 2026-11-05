// The 5 challenge targets, looked up before any online resolver.
// Positions: SIMBAD (via MAST Name Lookup, 5/11), ICRS at epoch J2000. They do NOT
// include proper motion; Barnard's Star has moved about 4.5' since 2000.
// Replace with shared/targets.json once Nguyên publishes it.

export const TARGETS = [
  {
    id: "barnard",
    name: "Barnard's Star",
    aliases: [
      "Barnard's Star",
      "Barnards Star",
      "Barnard Star",
      "Barnard",
      "GJ 699",
    ],
    raDeg: 269.4520769586187,
    decDeg: 4.6933649665767,
    epoch: 2000,
    objectType: "Red dwarf, largest proper motion in the sky",
    // "Barnard" alone resolves to NGC 6822 (Barnard's Galaxy) online.
  },
  {
    id: "eps-ind-b",
    name: "Epsilon Indi B",
    aliases: [
      "Epsilon Indi B",
      "eps Ind B",
      "eps Indi B",
      "GJ 845 B",
      "Gl 845 B",
    ],
    raDeg: 331.0441465885213,
    decDeg: -56.7828441951161,
    epoch: 2000,
    objectType: "Brown dwarf pair (Ba + Bb)",
    // Online, "eps Ind B" resolves to the planet "eps Ind b" at the host star.
  },
  {
    id: "wise-0855",
    name: "WISE 0855-0714",
    aliases: [
      "WISE 0855-0714",
      "WISE 0855",
      "WISE J085510.83-071442.5",
      "WISEA J085510.74-071442.5",
    ],
    raDeg: 133.81890825,
    decDeg: -7.247048,
    epoch: 2000,
    objectType: "Coldest known brown dwarf",
    // The challenge text gives 08h55m10.831s -7d14m42.53s, a later epoch (~85" away).
  },
  {
    id: "rw-aur",
    name: "RW Aurigae",
    aliases: ["RW Aurigae", "RW Aur"],
    raDeg: 76.9565260346,
    decDeg: 30.4014381739,
    epoch: 2000,
    objectType: "Young variable star (T Tauri)",
  },
  {
    id: "r-dra",
    name: "R Draconis",
    aliases: ["R Draconis", "R Dra"],
    raDeg: 248.16761083295,
    decDeg: 66.75497941722,
    epoch: 2000,
    objectType: "Mira variable",
  },
];

// "Barnard's  star" and "barnards star" both become "barnards star".
export function normalizeName(name) {
  return String(name ?? "")
    .toLowerCase()
    .replace(/['’]/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

const BY_ALIAS = new Map(
  TARGETS.flatMap((target) =>
    target.aliases.map((alias) => [normalizeName(alias), target]),
  ),
);

export function findTarget(name) {
  return BY_ALIAS.get(normalizeName(name)) ?? null;
}
