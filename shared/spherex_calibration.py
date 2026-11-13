"""Read SPHEREx masks and calibrated per-pixel wavelength/solid angle offline."""

from functools import lru_cache

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from scipy.ndimage import map_coordinates

FLAGS_DOCUMENTATION = "https://irsa.ipac.caltech.edu/onlinehelp/spherex/spherex/sp.html"


def bad_masks(flags, header):
    """SOURCE and FULLSAMPLE are informational for source fitting, not failures.

    SOURCE is additionally excluded from the local background. All other set
    bits, including unknown bits, are conservatively rejected. Header MP_* values
    are bit indices; defaults are the published QR2/QR3 definitions.
    """
    flags = np.asarray(flags, dtype=np.uint64)
    source = np.uint64(1 << int(header.get("MP_SOURCE", 21)))
    fullsample = np.uint64(1 << int(header.get("MP_FULLSAMPLE", 12)))
    allowed = source | fullsample
    bad_source = (flags & ~allowed) != 0
    bad_background = bad_source | ((flags & source) != 0)
    return bad_source, bad_background


@lru_cache(maxsize=12)
def _calibration(path, ext):
    with fits.open(path) as h:
        array = np.array(h[ext].data if ext is not None else h[0].data, dtype=float)
        if array.ndim != 2:
            raise ValueError("Calibration must be a 2D image")
        return array


def original_xy(header, x, y):
    """IRSA cutout alternate WCS A -> 0-based original detector coordinates."""
    if "CRPIX1A" not in header or "CRPIX2A" not in header:
        raise ValueError("Original detector coordinates CRPIX1A/2A are required")
    return 1 + np.asarray(x) - header["CRPIX1A"], 1 + np.asarray(y) - header["CRPIX2A"]


def _sample(array, x, y):
    return map_coordinates(
        array,
        [np.asarray(y), np.asarray(x)],
        order=1,
        mode="constant",
        cval=np.nan,
        prefilter=False,
    )


def solid_angles(item, header, shape):
    """Return per-pixel sr, or None for an explicitly warned WCS approximation."""
    if not item.get("sapm_path"):
        return None
    yy, xx = np.indices(shape)
    x, y = original_xy(header, xx, yy)
    # The QR2 SAPM IMAGE extension is in square arcseconds (verified on download).
    with fits.open(item["sapm_path"]) as h:
        if not u.Unit(h["IMAGE"].header.get("BUNIT", "")).is_equivalent(u.arcsec**2):
            raise ValueError("SAPM BUNIT must be an angular area")
        factor = u.Unit(h["IMAGE"].header["BUNIT"]).to(u.sr)
    area = _sample(_calibration(str(item["sapm_path"]), "IMAGE"), x, y) * factor
    return area


def measurement_metadata(item, position):
    with fits.open(item["path"]) as h:
        header = h["IMAGE"].header
        wcs = WCS(header, fobj=h).celestial
        x, y = wcs.world_to_pixel(SkyCoord(*position, unit="deg"))
        result = {
            "frame_id": str(header.get("OBSID", item.get("obs_id", "unknown"))),
            "mjd": float(header.get("MJD-AVG", item["mjd"])),
            "psf_fwhm_arcsec": float(header.get("PSF_FWHM", np.nan)),
            "bandwidth_um": item.get("bandwidth_um"),
            "wavelength_um": item.get("wavelength_um"),
            "wavelength_source": "unverified_input",
            "wavelength_calibrated": False,
        }
        if item.get("spectral_wcs_path"):
            ox, oy = original_xy(header, float(x), float(y))
            path = str(item["spectral_wcs_path"])
            result["wavelength_um"] = float(_sample(_calibration(path, "CWAVE"), [ox], [oy])[0])
            result["bandwidth_um"] = float(_sample(_calibration(path, "CBAND"), [ox], [oy])[0])
            result["wavelength_source"] = "CWAVE/CBAND"
            result["wavelength_calibrated"] = True
        elif item.get("survey") == "synthetic" or item.get("data_kind") == "mock":
            result["wavelength_source"] = "synthetic"
        elif "WCS-WAVE" in h:
            spectral = WCS(header, fobj=h, key="W")
            spectral.sip = None
            wave, width = spectral.pixel_to_world_values(x, y)
            result.update(
                wavelength_um=float(wave),
                bandwidth_um=float(width),
                wavelength_source="WCS-WAVE_APPROXIMATE",
            )
        for key in ["wavelength_um", "bandwidth_um", "psf_fwhm_arcsec"]:
            value = result[key]
            if value is None or not np.isfinite(value) or value <= 0:
                result[key] = None
        return result


def assign_comparison_bands(rows):
    """Only calibrated measurements are auto-grouped; full span < 0.5 min FWHM.

    This guards spectral comparability rather than trusting arbitrary band names.
    A detector and release are never mixed. Mock input bands remain available for
    offline numerical tests, and are explicitly labelled synthetic.
    """
    keys = sorted({(r["release"], str(r["detector"])) for r in rows})
    for key in keys:
        calibrated = sorted(
            [
                r
                for r in rows
                if (r["release"], str(r["detector"])) == key
                and r.get("wavelength_calibrated")
                and r.get("wavelength_um")
                and r.get("bandwidth_um")
            ],
            key=lambda r: r["wavelength_um"],
        )
        groups = []
        for row in calibrated:
            if not groups or row["wavelength_um"] - groups[-1][0]["wavelength_um"] >= 0.5 * min(
                [r["bandwidth_um"] for r in groups[-1]] + [row["bandwidth_um"]]
            ):
                groups.append([])
            groups[-1].append(row)
        for i, group in enumerate(groups):
            for row in group:
                row["comparison_band"] = f"{key[0]}:{key[1]}:calibrated-{i}"
