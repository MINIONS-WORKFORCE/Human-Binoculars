"""Training aperture photometry and centroid astrometry on original FITS.

No network or synthetic measurements are inserted by these functions.
Cutouts: list of dicts with path, mjd, detector, release, survey,
wavelength_um and comparison_band (a verified common passband identifier).
positions: one ICRS (ra_deg, dec_deg) per cutout, at its observation epoch.
"""

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import sigma_clip
from astropy.time import Time
from astropy.wcs import WCS
from astropy.wcs.utils import proj_plane_pixel_area
from photutils.aperture import SkyCircularAnnulus, SkyCircularAperture
from scipy.optimize import least_squares

from shared.spherex_calibration import (
    assign_comparison_bands,
    bad_masks,
    measurement_metadata,
    solid_angles,
)

APERTURE_ARCSEC = 12.3  # RADIUS; 2 nominal pixels; explicit wiki draft default
ANNULUS_ARCSEC = (49.2, 86.1)  # 8-14 nominal pixels, beyond bright-source masks


def propagate(target, mjds):
    """Angular-only ICRS prediction; pmra already includes cos(dec)."""
    coord = SkyCoord(
        ra=target["ra_deg"] * u.deg,
        dec=target["dec_deg"] * u.deg,
        pm_ra_cosdec=target["pmra"] * u.mas / u.yr,
        pm_dec=target["pmdec"] * u.mas / u.yr,
        obstime=Time(target["epoch_jyear"], format="jyear"),
    )
    moved = coord.apply_space_motion(new_obstime=Time(mjds, format="mjd"))
    return list(zip(np.atleast_1d(moved.ra.deg), np.atleast_1d(moved.dec.deg)))


def _load(item):
    with fits.open(item["path"]) as hdus:
        image = np.array(hdus["IMAGE"].data, dtype=float)
        variance = np.array(hdus["VARIANCE"].data, dtype=float)
        flags = np.array(hdus["FLAGS"].data)
        source_bad, background_bad = bad_masks(flags, hdus["FLAGS"].header)
        if "ZODI" in hdus:
            zodi = np.asarray(hdus["ZODI"].data, dtype=float)
            if zodi.shape != image.shape:
                raise ValueError("ZODI shape mismatch")
            image = image - zodi
        map_area = solid_angles(item, hdus["IMAGE"].header, image.shape)
        header = hdus["IMAGE"].header
        if header.get("DETECTOR") is not None and item.get("detector") is not None:
            supplied_detector = int(str(item["detector"]).split("D")[-1])
            if supplied_detector != int(header["DETECTOR"]):
                raise ValueError("DETECTOR_METADATA_MISMATCH")
        if u.Unit(header.get("BUNIT", "")) != u.MJy / u.sr:
            raise ValueError("IMAGE BUNIT must be MJy/sr")
        if image.ndim != 2 or image.shape != variance.shape or image.shape != flags.shape:
            raise ValueError("IMAGE/VARIANCE/FLAGS must have equal 2D shapes")
        wcs = WCS(header, fobj=hdus).celestial
    if not np.isfinite(item["mjd"]):
        raise ValueError("mjd must be finite")
    # Conservative default: reject any nonzero flag, not a guessed bit definition.
    bad = ~np.isfinite(image) | ~np.isfinite(variance) | (variance <= 0) | source_bad
    background_bad = background_bad | bad
    area = float(proj_plane_pixel_area(wcs)) * (np.pi / 180) ** 2
    if not np.isfinite(area) or area <= 0:
        raise ValueError("Invalid celestial WCS pixel area")
    if map_area is not None:
        area = map_area
        bad |= ~np.isfinite(area) | (area <= 0)
        background_bad |= bad
    return image, variance, bad, background_bad, wcs, area


def _weights(aperture, shape):
    mask = aperture.to_mask(method="exact")
    array = mask.to_image(shape)
    if array is None or not np.isclose(array.sum(), aperture.area, rtol=1e-6):
        raise ValueError("APERTURE_OR_ANNULUS_OUTSIDE_IMAGE")
    return array


def _geometry(position, wcs, shape, radius):
    if not np.isfinite(radius) or radius <= 0 or radius >= ANNULUS_ARCSEC[0]:
        raise ValueError("Invalid aperture radius")
    coord = SkyCoord(*position, unit="deg", frame="icrs")
    ap = SkyCircularAperture(coord, radius * u.arcsec).to_pixel(wcs)
    ann = SkyCircularAnnulus(coord, *[r * u.arcsec for r in ANNULUS_ARCSEC]).to_pixel(wcs)
    return ap, _weights(ap, shape), _weights(ann, shape)


def _background(image, variance, bad, ann):
    valid = (ann > 0) & ~bad
    if np.sum(ann[valid]) < 0.2 * ann.sum() or valid.sum() < 20:
        raise ValueError("INSUFFICIENT_BACKGROUND")
    noise_floor = float(np.sqrt(np.median(variance[valid])))
    clipped = sigma_clip(
        image[valid] - np.median(image[valid]),
        sigma=3.0,
        maxiters=5,
        stdfunc=lambda a, axis=None: np.maximum(np.nanstd(a, axis=axis), noise_floor),
    )
    indices = np.flatnonzero(valid)
    valid.flat[indices[np.ma.getmaskarray(clipped)]] = False
    if valid.sum() < 20:
        raise ValueError("INSUFFICIENT_BACKGROUND_AFTER_CLIPPING")
    # Linear estimator conditional on the selected uncontaminated pixels.
    weights = np.where(valid, ann, 0)
    weights /= weights.sum()
    level = float(np.sum(weights[valid] * image[valid]))
    var = float(np.sum(weights[valid] ** 2 * variance[valid]))
    return level, var


def _pairs(cutouts, positions):
    if len(cutouts) != len(positions):
        raise ValueError("Exactly one observation-epoch position per cutout required")
    return zip(cutouts, positions)


def photometry_measurements(cutouts, positions, aperture_arcsec=APERTURE_ARCSEC):
    """Return rows plus per-common-passband constant-flux chi2_reduced.

    Comparison bands must be supplied by calibrated wavelength selection upstream;
    a detector label alone is not a common passband. No aperture correction.
    """
    rows = []
    for item, position in _pairs(cutouts, positions):
        row = {
            k: item.get(k)
            for k in (
                "mjd",
                "wavelength_um",
                "detector",
                "release",
                "survey",
                "comparison_band",
                "source_obs_publisher_did",
            )
        }
        row.update(flux_mjy=None, err_mjy=None, snr=None, detected=False, warnings=[])
        try:
            image, variance, bad, background_bad, wcs, area = _load(item)
            row.update(measurement_metadata(item, position))
            if row["wavelength_source"] not in {"synthetic", "CWAVE/CBAND"}:
                row["comparison_band"] = None
            _, ap, ann = _geometry(position, wcs, image.shape, aperture_arcsec)
            if np.any(bad & (ap > 0)):
                with fits.open(item["path"]) as hdus:
                    flag_header = hdus["FLAGS"].header
                    overflow = 1 << int(flag_header.get("MP_OVERFLOW", 1))
                    if np.any((hdus["FLAGS"].data.astype(np.uint64) & overflow) != 0, where=ap > 0):
                        raise ValueError("SATURATED")
                raise ValueError("BAD_SOURCE_PIXELS")
            background, background_var = _background(image, variance, background_bad, ann)
            select = ap > 0
            # Coefficients of independent full pixel random variables are ap weights.
            # Hence squared fractional weights, unlike area-based Poisson splitting.
            factor = np.broadcast_to(area, image.shape) * 1e9
            flux_weights = ap * factor
            value = np.sum(flux_weights[select] * (image[select] - background))
            noise = (
                np.sum(flux_weights[select] ** 2 * variance[select])
                + flux_weights[select].sum() ** 2 * background_var
            )
            row.update(flux_mjy=float(value), err_mjy=float(np.sqrt(noise)))
            row["snr"] = row["flux_mjy"] / row["err_mjy"]
            row["detected"] = row["snr"] >= 3
            row["warnings"] = [
                "NO_APERTURE_CORRECTION",
                "SAPM_USED" if item.get("sapm_path") else "WCS_AREA_APPROXIMATION",
                "INDEPENDENT_PIXEL_NOISE",
                "ANNULUS_CONTAMINATION_NOT_MODELLED",
            ]
        except ValueError as exc:
            row["warnings"] = [str(exc)]
        rows.append(row)
    rows.sort(key=lambda row: row["mjd"])
    assign_comparison_bands(rows)
    return summarize_photometry(rows, aperture_arcsec, "aperture")


def summarize_photometry(rows, aperture_arcsec, method):
    groups = {}
    for row in rows:
        if (
            row["flux_mjy"] is None
            or not row["comparison_band"]
            or row.get("wavelength_um") is None
        ):
            continue
        # Never mix releases/detectors just because the caller reused a band name.
        key = (row["release"], row["detector"], row["comparison_band"])
        groups.setdefault(key, []).append(row)
    statistics = []
    for key, group in groups.items():
        f = np.array([r["flux_mjy"] for r in group])
        e = np.array([r["err_mjy"] for r in group])
        mean = float(np.average(f, weights=1 / e**2))
        chi = float(np.sum(((f - mean) / e) ** 2))
        statistics.append(
            {
                "release": key[0],
                "detector": key[1],
                "comparison_band": key[2],
                "n": len(group),
                "weighted_mean_mjy": mean,
                "dof": len(group) - 1,
                "wavelength_min_um": min(r["wavelength_um"] for r in group),
                "wavelength_max_um": max(r["wavelength_um"] for r in group),
                "bandwidth_min_um": min((r.get("bandwidth_um") or 0.0) for r in group),
                "baseline_days": max(r["mjd"] for r in group) - min(r["mjd"] for r in group),
                "chi2_reduced": chi / (len(group) - 1) if len(group) > 1 else None,
            }
        )
    return {
        "aperture_arcsec": aperture_arcsec,
        "aperture_is": "radius",
        "flux_unit": "mJy",
        "measurement_method": method,
        "rows": rows,
        "statistics": statistics,
        "chi2_reduced": statistics[0]["chi2_reduced"] if len(statistics) == 1 else None,
    }


def _centroid(image, variance, bad, position, wcs, background_bad=None):
    if background_bad is None:
        background_bad = bad
    ap, _, ann = _geometry(position, wcs, image.shape, APERTURE_ARCSEC)
    try:
        background, _ = _background(image, variance, background_bad, ann)
    except ValueError:
        # Background remains a free parameter in the Gaussian centroid fit.
        if (~bad).sum() < 25:
            raise ValueError("INSUFFICIENT_CENTROID_PIXELS")
        background = float(np.median(image[~bad]))
    x0, y0 = ap.positions
    yy, xx = np.indices(image.shape)
    selected = (abs(xx - x0) <= 5) & (abs(yy - y0) <= 5)
    selected &= ~bad
    if selected.sum() < 25:
        raise ValueError("BAD_CENTROID_WINDOW")
    x, y = xx[selected], yy[selected]
    values, errors = image[selected], np.sqrt(variance[selected])
    amplitude = float(values.max() - background)
    if amplitude <= 0:
        raise ValueError("NO_POSITIVE_SOURCE")

    def residual(p):
        a, xc, yc, sigma, bg = p
        model = bg + a * np.exp(-((x - xc) ** 2 + (y - yc) ** 2) / (2 * sigma**2))
        return (model - values) / errors

    fit = least_squares(
        residual,
        [amplitude, x0, y0, 1, background],
        bounds=(
            [0, x0 - 2, y0 - 2, 0.4, -np.inf],
            [np.inf, x0 + 2, y0 + 2, 2.5, np.inf],
        ),
    )
    if not fit.success or np.any(fit.active_mask) or np.linalg.matrix_rank(fit.jac) < 5:
        raise ValueError("CENTROID_FIT_FAILED_OR_AT_BOUND")
    covariance = np.linalg.inv(fit.jac.T @ fit.jac)
    if fit.x[0] / np.sqrt(covariance[0, 0]) < 5:
        raise ValueError("CENTROID_LOW_SNR")
    xc, yc = fit.x[1:3]
    sky = wcs.pixel_to_world(xc, yc)
    # Numerical Jacobian includes rotation, RA wrap and cos(dec).
    derivatives = []
    for dx, dy in [(0.001, 0), (0, 0.001)]:
        shifted = wcs.pixel_to_world(xc + dx, yc + dy)
        east, north = sky.spherical_offsets_to(shifted)
        derivatives.append([east.to_value(u.mas) / 0.001, north.to_value(u.mas) / 0.001])
    jac = np.array(derivatives).T
    sky_cov = jac @ covariance[1:3, 1:3] @ jac.T
    return sky, np.sqrt(np.diag(sky_cov)), float(np.sum(fit.fun**2) / (len(values) - 5))


def _slope(times, values, errors):
    design = np.column_stack([np.ones(len(times)), times])
    normal = design.T @ (design / errors[:, None] ** 2)
    covariance = np.linalg.inv(normal)
    coeff = covariance @ (design.T @ (values / errors**2))
    residual = values - design @ coeff
    scale = max(1.0, float(np.sum((residual / errors) ** 2) / (len(values) - 2)))
    return float(coeff[1]), float(np.sqrt(covariance[1, 1] * scale))


def astrometry_measurements(cutouts, positions, reference=None, systematic_floor_mas=100.0):
    """Gaussian centroids -> WCS -> tangent offsets -> weighted linear slopes.

    Slopes are apparent linear trends; parallax/registration errors are not fitted.
    The positive systematic floor is a configurable assumption, not a calibration.
    """
    if not np.isfinite(systematic_floor_mas) or systematic_floor_mas <= 0:
        raise ValueError("Positive systematic floor required")
    rows = []
    for item, position in _pairs(cutouts, positions):
        row = {"mjd": item["mjd"], "ra_deg": None, "dec_deg": None, "warnings": []}
        try:
            image, var, bad, background_bad, wcs, _ = _load(item)
            sky, error, chi = _centroid(image, var, bad, position, wcs, background_bad)
            row.update(
                ra_deg=float(sky.ra.deg),
                dec_deg=float(sky.dec.deg),
                ra_cosdec_error_mas=float(np.hypot(error[0], systematic_floor_mas)),
                dec_error_mas=float(np.hypot(error[1], systematic_floor_mas)),
                centroid_chi2_reduced=chi,
            )
        except ValueError as exc:
            row["warnings"] = [str(exc)]
        rows.append(row)
    rows.sort(key=lambda r: r["mjd"])
    good = [r for r in rows if r["ra_deg"] is not None]
    result = {
        "rows": rows,
        "fit": None,
        "warnings": [
            "APPARENT_LINEAR_TREND_NO_PARALLAX_FIT",
            "NO_REFERENCE_STAR_REGISTRATION",
            "GAUSSIAN_PSF_APPROXIMATION",
        ],
        "systematic_floor_mas": systematic_floor_mas,
    }
    if len(good) < 3 or np.ptp([r["mjd"] for r in good]) < 30:
        result["warnings"].append("NEED_THREE_MEASUREMENTS_AND_30_DAY_BASELINE")
        return result
    coords = SkyCoord([r["ra_deg"] for r in good], [r["dec_deg"] for r in good], unit="deg")
    east, north = coords[0].spherical_offsets_to(coords)
    times = (np.array([r["mjd"] for r in good]) - good[0]["mjd"]) / 365.25
    pmra, era = _slope(
        times, east.to_value(u.mas), np.array([r["ra_cosdec_error_mas"] for r in good])
    )
    pmdec, edec = _slope(times, north.to_value(u.mas), np.array([r["dec_error_mas"] for r in good]))
    result["fit"] = {
        "pmra": pmra,
        "pmdec": pmdec,
        "pmra_error": era,
        "pmdec_error": edec,
        "unit": "mas/yr",
        "n": len(good),
        "baseline_days": float(np.ptp(times) * 365.25),
    }
    if reference is not None:
        result["fit"]["pmdec_sign_matches_reference"] = bool(pmdec * reference["pmdec"] > 0)
        result["fit"]["reference_pmdec"] = reference["pmdec"]
    return result


def photometry(
    cutouts, target, aperture_arcsec=APERTURE_ARCSEC, *, reference_stars=None, diagnostics=False
):
    """API 0.1 payload by default; diagnostics=True keeps quality/provenance fields."""
    if not isinstance(target, dict):
        return photometry_measurements(cutouts, target, aperture_arcsec)
    if not diagnostics:
        for item in cutouts:
            survey = item.get("survey")
            if isinstance(survey, bool) or not isinstance(survey, int):
                raise TypeError("API 0.1 requires integer survey; supply the team's visit index")
    from shared.science_contract import photometry_response

    result = photometry_response(cutouts, target, aperture_arcsec, reference_stars or [])
    if diagnostics:
        return result
    from shared.science_api import photometry_payload

    return photometry_payload(result)


def astrometry(cutouts, target, reference=None, systematic_floor_mas=100.0, *, diagnostics=False):
    """API 0.1 payload by default; diagnostics=True keeps quality/provenance fields."""
    if not isinstance(target, dict):
        return astrometry_measurements(cutouts, target, reference, systematic_floor_mas)
    from shared.science_contract import astrometry_response

    result = astrometry_response(cutouts, target, systematic_floor_mas)
    if diagnostics:
        return result
    from shared.science_api import astrometry_payload

    return astrometry_payload(result)
