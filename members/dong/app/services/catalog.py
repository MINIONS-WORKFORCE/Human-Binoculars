"""Expose the team's epoch-tagged target table through API 0.1."""

import json
from functools import lru_cache
from pathlib import Path

import astropy.units as u
from astropy.coordinates import SkyCoord
from astropy.time import Time

TABLE = Path(__file__).resolve().parents[4] / "shared" / "targets.json"
KEYS = {"epsilon-indi-b": "epsindib", "rw-aur": "rwaur", "r-dra": "rdra"}
ALIASES = {
    "barnard": ("Barnards Star", "GJ 699"),
    "wise0855": ("WISE 0855-0714", "WISE J085510.83-071442.5"),
    "epsindib": ("eps Ind B",),
    "rwaur": ("RW Aur",),
    "rdra": ("R Dra",),
}


@lru_cache(maxsize=1)
def targets():
    records = {}
    for row in json.loads(TABLE.read_text(encoding="utf-8"))["targets"]:
        key = KEYS.get(row["id"], row["id"])
        data = row["astrometry"]
        records[key] = (
            {
                "target_key": key,
                "name": row["name"],
                "ra": data["ra_deg"],
                "dec": data["dec_deg"],
                "epoch": f"J{data['reference_epoch_jyear']:.1f}",
                "pmra": data["pm_ra_cosdec_mas_per_yr"],
                "pmdec": data["pm_dec_mas_per_yr"],
                "parallax_mas": None,
                "kind": "variable" if key in {"rwaur", "rdra"} else "high_pm",
                "source": "targets_table",
            },
            row["simbad_id"],
        )
    return records


def resolve_name(name):
    normalized = name.strip().casefold()
    for key, (record, simbad_id) in targets().items():
        names = (key, record["name"], simbad_id, *ALIASES[key])
        if normalized in {value.casefold() for value in names}:
            return {**record, "query": name}
    return None


def position_at(key, mjd):
    entry = targets().get(key)
    if entry is None:
        return None
    record, _ = entry
    if record["pmra"] is None or record["pmdec"] is None:
        return None
    coord = SkyCoord(record["ra"], record["dec"], unit="deg")
    elapsed_years = (Time(mjd, format="mjd", scale="utc").tt - Time(record["epoch"])).to_value(u.yr)
    return coord.spherical_offsets_by(
        record["pmra"] * elapsed_years * u.mas, record["pmdec"] * elapsed_years * u.mas
    )
