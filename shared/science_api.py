"""Explicit projection onto the team's existing API 0.1; no HTTP or network.

Keep the diagnostic response beside this payload: API 0.1 has no place for
provenance, saturation reasons or wavelength-calibration warnings.
"""

import math

import astropy.units as u
from astropy.coordinates import SkyCoord

TARGET_KEYS = {
    "r-dra": "rdra",
    "eps-ind-b": "epsindib",
    "epsilon-indi-b": "epsindib",
    "rw-aur": "rwaur",
    "wise-0855": "wise0855",
}
PHOTO_FIELDS = (
    "frame_id",
    "mjd",
    "wavelength_um",
    "detector",
    "release",
    "survey",
    "flux_mjy",
    "err_mjy",
    "snr",
    "detected",
    "flagged",
    "is_reference_star",
)
ASTRO_FIELDS = (
    "frame_id", "mjd", "measured", "predicted", "offset_arcsec",
    "residual_ra_mas", "residual_dec_mas", "measured_px",
)
FIT_FIELDS = ("pmra", "pmdec", "pmra_err", "pmdec_err", "n_points", "baseline_days")


def _target(target):
    result = dict(target)
    result["target_key"] = TARGET_KEYS.get(result["target_key"], result["target_key"])
    return result


def photometry_payload(diagnostic):
    """Return E6 fields only; reject missing metadata instead of guessing it."""
    points = []
    for point in diagnostic["points"]:
        wave, survey = point["wavelength_um"], point["survey"]
        if wave is None or not math.isfinite(wave) or wave <= 0:
            raise ValueError("API 0.1 requires wavelength_um; keep diagnostics until calibrated")
        if isinstance(survey, bool) or not isinstance(survey, int):
            raise TypeError("API 0.1 requires integer survey; supply the team's visit index")
        points.append({key: point[key] for key in PHOTO_FIELDS})
    reference = diagnostic["reference_star"]
    # A synthetic or unidentified control must not receive a fabricated Gaia ID.
    if reference is not None and not reference.get("gaia_source_id"):
        reference = None
    variability = diagnostic["variability"]
    if variability is not None:
        variability = {
            key: variability[key] for key in ("chi2_reduced", "dof", "is_variable", "method")
        }
    return {
        "api_version": "0.1",
        "target": _target(diagnostic["target"]),
        "reference_star": reference,
        "points": points,
        "variability": variability,
        "warnings": diagnostic.get("warnings", []),
    }


def astrometry_payload(diagnostic):
    """Return E7 fields only. measured_px stays null without matching PNG WCS."""
    points = []
    for point in diagnostic["points"]:
        payload = {key: point[key] for key in ASTRO_FIELDS if key in point}
        measured = point.get("measured")
        predicted = point.get("predicted")
        if measured is not None and predicted is not None:
            reference = SkyCoord(predicted["ra"], predicted["dec"], unit="deg")
            observed = SkyCoord(measured["ra"], measured["dec"], unit="deg")
            east, north = reference.spherical_offsets_to(observed)
            payload["residual_ra_mas"] = east.to_value(u.mas)
            payload["residual_dec_mas"] = north.to_value(u.mas)
        else:
            payload["residual_ra_mas"] = None
            payload["residual_dec_mas"] = None
        points.append(payload)
    return {
        "api_version": "0.1",
        "target": _target(diagnostic["target"]),
        "catalog_pm": diagnostic["catalog_pm"],
        "points": points,
        "fit": None
        if diagnostic["fit"] is None
        else {key: diagnostic["fit"][key] for key in FIT_FIELDS},
        "warnings": diagnostic.get("warnings", []),
    }
