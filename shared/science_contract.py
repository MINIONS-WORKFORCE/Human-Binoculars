"""Typed adapters for the wiki E6/E7 payloads; no HTTP route or network I/O."""

from pathlib import Path
from typing import Literal

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from pydantic import BaseModel, ConfigDict, Field

from shared.science import (
    APERTURE_ARCSEC,
    astrometry_measurements,
    photometry_measurements,
    propagate,
)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Target(Model):
    ra: float = Field(ge=0, lt=360)
    dec: float = Field(ge=-90, le=90)
    name: str
    target_key: str


class ReferenceStar(Model):
    gaia_source_id: str | None = None
    ra: float
    dec: float


class PhotometryPoint(Model):
    frame_id: str
    mjd: float
    iso: str
    wavelength_um: float | None = Field(default=None, gt=0)
    bandwidth_um: float | None = Field(default=None, gt=0)
    detector: int = Field(ge=1, le=6)
    release: str
    survey: int | str | None = None
    flux_mjy: float | None
    err_mjy: float | None = Field(ge=0)
    snr: float | None
    detected: bool
    flagged: bool
    is_reference_star: bool
    gaia_source_id: str | None = None
    reference_id: str | None = None
    upper_limit_mjy: float | None = Field(default=None, ge=0)
    wavelength_source: str | None = None
    source_obs_publisher_did: str | None = None
    warnings: list[str] = []


class Variability(Model):
    chi2_reduced: float = Field(ge=0)
    dof: int = Field(gt=0)
    is_variable: bool
    method: str
    reference_validated: bool
    comparison_band: str
    wavelength_min_um: float
    wavelength_max_um: float
    reference_checks: list[dict] = []


class PhotometryResponse(Model):
    data_kind: Literal["mock", "observational"]
    api_version: Literal["0.1"] = "0.1"
    target: Target
    reference_star: ReferenceStar | None
    points: list[PhotometryPoint]
    variability: Variability | None
    aperture_arcsec: float = Field(gt=0)
    aperture_is: Literal["radius"] = "radius"
    measurement_method: str = "aperture_zodi_local_clipped_background"
    groups: list[dict] = []
    warnings: list[str] = []


class Measured(Model):
    ra: float = Field(ge=0, lt=360)
    dec: float = Field(ge=-90, le=90)
    err_arcsec: float = Field(ge=0)


class Predicted(Model):
    ra: float = Field(ge=0, lt=360)
    dec: float = Field(ge=-90, le=90)


class AstrometryPoint(Model):
    frame_id: str
    mjd: float
    measured: Measured | None
    predicted: Predicted
    offset_arcsec: float | None = Field(ge=0)
    measured_px: list[float] | None
    warnings: list[str] = []


class CatalogPM(Model):
    pmra: float
    pmdec: float
    source: str
    epoch: str


class MotionFit(Model):
    pmra: float
    pmdec: float
    pmra_err: float = Field(gt=0)
    pmdec_err: float = Field(gt=0)
    n_points: int = Field(ge=3)
    baseline_days: float = Field(ge=30)
    pmdec_sign_matches_catalog: bool


class AstrometryResponse(Model):
    data_kind: Literal["mock", "observational"]
    api_version: Literal["0.1"] = "0.1"
    target: Target
    catalog_pm: CatalogPM
    points: list[AstrometryPoint]
    fit: MotionFit | None
    warnings: list[str] = []


def _data_kind(cutouts):
    return (
        "observational"
        if cutouts
        and all(
            e.get("data_kind") == "observational"
            or str(e.get("access_url", "")).startswith("https://irsa.ipac.caltech.edu/")
            for e in cutouts
        )
        else "mock"
    )


def normalized_target(t):
    t = dict(t)
    if "astrometry" in t:
        a = t["astrometry"]
        t.update(
            ra_deg=a["ra_deg"],
            dec_deg=a["dec_deg"],
            epoch_jyear=a["reference_epoch_jyear"],
            pmra=a["pm_ra_cosdec_mas_per_yr"],
            pmdec=a["pm_dec_mas_per_yr"],
        )
    epoch = t.get("epoch_jyear", t.get("ref_epoch", t.get("epoch")))
    if isinstance(epoch, str):
        epoch = float(epoch.lstrip("Jj"))
    return {
        **t,
        "ra_deg": float(t.get("ra_deg", t.get("ra"))),
        "dec_deg": float(t.get("dec_deg", t.get("dec"))),
        "epoch_jyear": float(epoch),
        "pmra": float(t["pmra"]),
        "pmdec": float(t["pmdec"]),
    }


def _target(t):
    return {
        "ra": t["ra_deg"],
        "dec": t["dec_deg"],
        "name": t.get("name", "target"),
        "target_key": t.get("target_key", t.get("id", "target")),
    }


def _detector(value):
    return int(str(value).split("D")[-1])


def _best_group(stats):
    valid = [s for s in stats if s["chi2_reduced"] is not None]
    # Select by coverage, never by largest chi-square or by the measured flux.
    return max(valid, key=lambda s: (s["n"], s["baseline_days"]), default=None)


def _points(rows, reference=False, gaia_id=None, reference_id=None):
    result = []
    for row in rows:
        detected = row["detected"]
        result.append(
            {
                "frame_id": row.get("frame_id", "unknown"),
                "mjd": row["mjd"],
                "iso": Time(row["mjd"], format="mjd", scale="utc").isot + "Z",
                "wavelength_um": row.get("wavelength_um"),
                "bandwidth_um": row.get("bandwidth_um"),
                "detector": _detector(row["detector"]),
                "release": str(row["release"]).removeprefix("spherex_"),
                "survey": row.get("survey"),
                "flux_mjy": row["flux_mjy"],
                "err_mjy": row["err_mjy"],
                "snr": row["snr"],
                "detected": detected,
                "flagged": row["flux_mjy"] is None,
                "is_reference_star": reference,
                "gaia_source_id": gaia_id,
                "reference_id": reference_id,
                "upper_limit_mjy": 3 * row["err_mjy"] if not detected and row["err_mjy"] else None,
                "wavelength_source": row.get("wavelength_source"),
                "source_obs_publisher_did": row.get("source_obs_publisher_did"),
                "warnings": row["warnings"],
            }
        )
    return result


def photometry_response(cutouts, target, aperture_arcsec=APERTURE_ARCSEC, reference_stars=()):
    target = normalized_target(target)
    positions = propagate(target, [e["mjd"] for e in cutouts])
    measured = photometry_measurements(cutouts, positions, aperture_arcsec)
    points = _points(measured["rows"])
    chosen = _best_group(measured["statistics"])
    reference_info, checks = None, []
    for star in reference_stars:
        star = normalized_target(star)
        positions = propagate(star, [e["mjd"] for e in cutouts])
        ref = photometry_measurements(cutouts, positions, aperture_arcsec)
        points += _points(ref["rows"], True, star.get("gaia_source_id"), star.get("id"))
        if reference_info is None:
            reference_info = {
                "gaia_source_id": star.get("gaia_source_id"),
                "ra": star["ra_deg"],
                "dec": star["dec_deg"],
            }
        compatible = []
        if chosen:
            for group in ref["statistics"]:
                if group["detector"] != chosen["detector"] or group["release"] != chosen["release"]:
                    continue
                span = max(group["wavelength_max_um"], chosen["wavelength_max_um"]) - min(
                    group["wavelength_min_um"], chosen["wavelength_min_um"]
                )
                width = min(group["bandwidth_min_um"], chosen["bandwidth_min_um"])
                if width > 0 and span < width and group["n"] >= 3:
                    compatible.append(group)
        check = _best_group(compatible)
        checks.append(
            {
                "reference_id": star.get("id"),
                "gaia_source_id": star.get("gaia_source_id"),
                "chi2_reduced": check["chi2_reduced"] if check else None,
                "n": check["n"] if check else 0,
                "stable_within_errors": bool(check and check["chi2_reduced"] <= 5),
            }
        )
    variability = None
    warnings = ["NO_ABSOLUTE_APERTURE_CORRECTION", "CALIBRATION_SYSTEMATICS_NOT_INCLUDED"]
    if chosen:
        validated = bool(checks and all(c["stable_within_errors"] for c in checks))
        variability = {
            "chi2_reduced": chosen["chi2_reduced"],
            "dof": chosen["dof"],
            "is_variable": bool(validated and chosen["chi2_reduced"] > 5),
            "method": "chi2_vs_reference" if validated else "chi2_constant_flux_unvalidated",
            "reference_validated": validated,
            "comparison_band": chosen["comparison_band"],
            "wavelength_min_um": chosen["wavelength_min_um"],
            "wavelength_max_um": chosen["wavelength_max_um"],
            "reference_checks": checks,
        }
        if not validated:
            warnings.append("VARIABILITY_NOT_CONFIRMED_BY_REFERENCE_STARS")
    else:
        warnings.append("INSUFFICIENT_COMPARABLE_MEASUREMENTS")
    return PhotometryResponse.model_validate(
        {
            "data_kind": _data_kind(cutouts),
            "target": _target(target),
            "reference_star": reference_info,
            "points": sorted(points, key=lambda p: p["mjd"]),
            "variability": variability,
            "aperture_arcsec": aperture_arcsec,
            "measurement_method": measured["measurement_method"],
            "groups": measured["statistics"],
            "warnings": warnings,
        }
    ).model_dump()


def astrometry_response(cutouts, target, systematic_floor_mas=100.0):
    target = normalized_target(target)
    positions = propagate(target, [e["mjd"] for e in cutouts])
    result = astrometry_measurements(cutouts, positions, target, systematic_floor_mas)
    points = []
    for row, item in zip(result["rows"], sorted(cutouts, key=lambda e: e["mjd"])):
        predicted = propagate(target, [row["mjd"]])[0]
        measured, offset, pixels = None, None, None
        if row["ra_deg"] is not None:
            measured = {
                "ra": row["ra_deg"],
                "dec": row["dec_deg"],
                "err_arcsec": float(
                    np.hypot(row["ra_cosdec_error_mas"], row["dec_error_mas"]) / 1000
                ),
            }
            sky = SkyCoord(row["ra_deg"], row["dec_deg"], unit="deg")
            offset = float(sky.separation(SkyCoord(*predicted, unit="deg")).arcsec)
            if item.get("png_wcs_header") is not None:
                x, y = WCS(item["png_wcs_header"]).celestial.world_to_pixel(sky)
                pixels = [float(x), float(item["png_shape"][0] - 1 - y)]
        with fits.open(item["path"]) as h:
            frame = str(h["IMAGE"].header.get("OBSID", Path(item["path"]).stem))
        points.append(
            {
                "frame_id": frame,
                "mjd": row["mjd"],
                "measured": measured,
                "predicted": {"ra": float(predicted[0]), "dec": float(predicted[1])},
                "offset_arcsec": offset,
                "measured_px": pixels,
                "warnings": row["warnings"],
            }
        )
    fit = result["fit"]
    if fit:
        fit = {
            "pmra": fit["pmra"],
            "pmdec": fit["pmdec"],
            "pmra_err": fit["pmra_error"],
            "pmdec_err": fit["pmdec_error"],
            "n_points": fit["n"],
            "baseline_days": fit["baseline_days"],
            "pmdec_sign_matches_catalog": fit["pmdec_sign_matches_reference"],
        }
    if fit and abs(fit["pmra"] - target["pmra"]) > 3 * fit["pmra_err"]:
        result["warnings"].append("PMRA_DISAGREES_WITH_CATALOG_BEYOND_3SIGMA")
    source = (
        "gaia_dr3"
        if target.get("crosscheck", {}).get("gaia_dr3")
        else target.get("source", "catalogue")
    )
    return AstrometryResponse.model_validate(
        {
            "data_kind": _data_kind(cutouts),
            "target": _target(target),
            "catalog_pm": {
                "pmra": target["pmra"],
                "pmdec": target["pmdec"],
                "source": source,
                "epoch": f"J{target['epoch_jyear']:.1f}",
            },
            "points": points,
            "fit": fit,
            "warnings": result["warnings"]
            + [
                "PIXELS_REQUIRE_MATCHING_PNG_GRID",
                "ERRORS_INFLATED_BY_RESIDUAL_SCATTER;SYSTEMATIC_FLOOR_IS_ASSUMED",
            ],
        }
    ).model_dump()
