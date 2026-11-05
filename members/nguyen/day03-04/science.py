"""Small training utilities for the 3-4 November science handoff.

No network calls, source-image edits, or guessed observing dates.
Astropy is loaded only for space-motion propagation.
"""

import csv
import json
import math
from pathlib import Path


def ra_to_degrees(hms):
    h, m, s = (float(v) for v in hms.split())
    if not all(math.isfinite(v) for v in (h, m, s)):
        raise ValueError("RA must be finite")
    if not (0 <= h < 24 and 0 <= m < 60 and 0 <= s < 60):
        raise ValueError("Invalid RA hours/minutes/seconds")
    return 15 * (h + m / 60 + s / 3600)


def dec_to_degrees(dms):
    d, m, s = (float(v) for v in dms.split())
    if not all(math.isfinite(v) for v in (d, m, s)):
        raise ValueError("Declination must be finite")
    if not (0 <= abs(d) <= 90 and 0 <= m < 60 and 0 <= s < 60):
        raise ValueError("Invalid declination degrees/minutes/seconds")
    result = abs(d) + m / 60 + s / 3600
    if result > 90:
        raise ValueError("Declination exceeds 90 degrees")
    return (-1 if dms.strip().startswith("-") else 1) * result


def nominal_motion(pm_ra_cosdec, pm_dec, baseline_years, pixel_scale=6.15):
    values = (pm_ra_cosdec, pm_dec, baseline_years, pixel_scale)
    if not all(math.isfinite(v) for v in values):
        raise ValueError("Motion arguments must be finite")
    if baseline_years < 0 or pixel_scale <= 0:
        raise ValueError("Need nonnegative baseline and positive pixel scale")
    arcsec = math.hypot(pm_ra_cosdec, pm_dec) * baseline_years / 1000
    return arcsec, arcsec / pixel_scale


def load_targets(path):
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    targets = payload["targets"]
    ids = [t["id"] for t in targets]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate target ID")
    for t in targets:
        a = t["astrometry"]
        if a["frame"] != "icrs":
            raise ValueError("Only ICRS is supported")
        for field in ("reference_epoch_jyear", "pm_ra_cosdec_mas_per_yr", "pm_dec_mas_per_yr"):
            if not math.isfinite(a[field]):
                raise ValueError(f"Missing/nonfinite {field}: {t['id']}")
        if abs(ra_to_degrees(a["ra_hms"]) - a["ra_deg"]) > 1e-9:
            raise ValueError(f"Inconsistent RA: {t['id']}")
        if abs(dec_to_degrees(a["dec_dms"]) - a["dec_deg"]) > 1e-9:
            raise ValueError(f"Inconsistent Dec: {t['id']}")
    return {t["id"]: t for t in targets}


def read_observations(path, targets):
    required = {"record_id", "target_id", "obs_id", "collection", "detector", "t_min", "t_max"}
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not required.issubset(reader.fieldnames or []):
            raise ValueError(f"Required metadata columns: {sorted(required)}")
        rows = list(reader)
    if not rows:
        raise ValueError("Metadata has no observations; no actual-date result can be produced")
    seen = set()
    for row in rows:
        if any(not str(row[key]).strip() for key in required):
            raise ValueError("Metadata contains an empty required value")
        if row["record_id"] in seen:
            raise ValueError("record_id must be globally unique")
        seen.add(row["record_id"])
        if row["target_id"] not in targets:
            raise ValueError(f"Unknown target: {row['target_id']}")
        if row["detector"] not in {f"D{i}" for i in range(1, 7)}:
            raise ValueError("Normalize detector to D1..D6; do not silently guess")
        start, end = float(row["t_min"]), float(row["t_max"])
        if not (math.isfinite(start) and math.isfinite(end) and 0 < start <= end):
            raise ValueError("Require finite MJD t_min <= t_max")
        row["mjd_mid"] = (start + end) / 2
        row["time_scale"] = row.get("time_scale", "utc").strip().lower() or "utc"
        if row["time_scale"] not in {"utc", "tt", "tai", "tdb"}:
            raise ValueError("Unsupported time_scale")
    return rows


def propagate(target, mjd, time_scale="utc"):
    """ICRS angular proper motion, not spacecraft apparent position.

    No distance or radial velocity is supplied. Astropy may emit its
    expected ERFA distance-override warning. Annual parallax, binary orbit,
    and perspective acceleration are not modeled in this v0 exercise.
    """
    from astropy import units as u
    from astropy.coordinates import SkyCoord
    from astropy.time import Time

    a = target["astrometry"]
    source = SkyCoord(
        ra=a["ra_deg"] * u.deg,
        dec=a["dec_deg"] * u.deg,
        pm_ra_cosdec=a["pm_ra_cosdec_mas_per_yr"] * u.mas / u.yr,
        pm_dec=a["pm_dec_mas_per_yr"] * u.mas / u.yr,
        obstime=Time(a["reference_epoch_jyear"], format="jyear", scale=a["epoch_scale"]),
        frame="icrs",
    )
    return source.apply_space_motion(new_obstime=Time(mjd, format="mjd", scale=time_scale))


def decode_flags(value, definitions):
    """definitions maps symbolic names to BIT INDICES, not mask values."""
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError("Flag value must be a nonnegative integer")
    known_mask = 0
    names = []
    for name, bit in definitions.items():
        if not isinstance(bit, int) or bit < 0:
            raise ValueError("Invalid bit index")
        mask = 1 << bit
        known_mask |= mask
        if value & mask:
            names.append(name)
    return names, value & ~known_mask


def definitions_from_header(header):
    """Astropy exposes HIERARCH MP_X as MP_X; accept either representation."""
    result = {}
    for key in header:
        name = key.removeprefix("HIERARCH ")
        if name.startswith("MP_"):
            bit = header[key]
            if not isinstance(bit, int) or bit < 0:
                raise ValueError(f"Invalid bit index for {key}")
            result[name[3:]] = bit
    if not result:
        raise ValueError("No MP_* definitions in this FLAGS header")
    return result
