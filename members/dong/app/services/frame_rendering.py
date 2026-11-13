"""Adapt Hữu Hoàng's TAN and FITS helpers to the API's in-memory image contract."""

from importlib import import_module

import numpy as np
from astropy.time import Time
from shared.image_processing import png_bytes, reproject_compatible, stretch
from shared.pipeline.irsa import group_images_into_visits

from .catalog import position_at

# The member directory has a hyphen, so it cannot appear in a from-import.
imaging = import_module("members.huu-hoang.tan_pipeline")
PIXEL_SCALE = 6.15


class NoCoverage(Exception):
    """No indexed image overlaps the requested sky grid."""


def build_frames(cutouts, query, identity):
    """Render one median frame per visit on a common grid and display scale."""
    times = [cutout.mjd for cutout in cutouts if cutout.detector == query.detector]
    center = position_at(query.target_key, (min(times) + max(times)) / 2) if times else None
    ra, dec = (
        (float(center.ra.deg), float(center.dec.deg))
        if center is not None
        else (query.ra, query.dec)
    )
    wcs, shape = imaging.tan_grid(ra, dec, query.size, scale=PIXEL_SCALE)
    grid = {
        "width": shape[1],
        "height": shape[0],
        "pixscale_arcsec": PIXEL_SCALE,
        "projection": "TAN",
        "center_ra": ra,
        "center_dec": dec,
    }
    frames, arrays, wavelengths, frame_warnings = [], [], [], []
    brightness_unit = None
    has_coverage = False
    groups = group_images_into_visits(
        [{"t_min": cutout.mjd, "cutout": cutout} for cutout in cutouts]
    )
    for visit, group in enumerate(groups, start=1):
        aligned, metadata, missing, times, releases = [], [], [], [], set()
        for entry in group:
            cutout = entry["cutout"]
            if has_coverage and cutout.detector != query.detector:
                continue
            image, native_wcs, info = imaging.load_cutout(cutout.path, ra, dec)
            if info["detector"] != cutout.detector or info["obs_id"] != cutout.obs_id:
                raise ValueError("FITS observation or detector differs from fixture metadata")
            pixels, footprint = reproject_compatible(
                (image, native_wcs), wcs, shape_out=shape, order="bilinear"
            )
            valid = (np.isfinite(pixels) & (footprint > 0)).any()
            if valid:
                has_coverage = True
            elif not has_coverage:
                _, geometric = reproject_compatible(
                    (np.ones_like(image), native_wcs), wcs, shape_out=shape
                )
                has_coverage = bool(geometric.any())
            if not valid or cutout.detector != query.detector:
                continue
            # A partial cutout may overlap the grid while missing the target.
            # Test geometry separately from the quality mask: a saturated target
            # can be masked even though the detector actually observed it.
            predicted_input = position_at(query.target_key, cutout.mjd)
            if predicted_input is not None:
                px, py = native_wcs.world_to_pixel(predicted_input)
                height, width = image.shape
                if not (-0.5 <= px < width - 0.5 and -0.5 <= py < height - 0.5):
                    frame_warnings.append("TARGET_OUTSIDE_COVERAGE")
                    continue
            if not info["bunit"]:
                raise ValueError("Fixture image has no brightness unit")
            brightness_unit = brightness_unit or info["bunit"]
            if brightness_unit != info["bunit"]:
                raise ValueError("Fixture images have inconsistent brightness units")
            aligned.append(np.where(footprint > 0, pixels, np.nan))
            metadata.append(info)
            missing.append(info["bad_pixel_frac"])
            times.append(cutout.mjd)
            releases.add(cutout.release)
        if not aligned:
            continue
        if len(frames) == query.max_frames:
            frame_warnings.append("TRUNCATED")
            break

        stack = np.asarray(aligned)
        covered = np.isfinite(stack).any(axis=0)
        median = np.full(shape, np.nan)
        median[covered] = np.nanmedian(stack[:, covered], axis=0)
        arrays.append(median)
        waves = [m["wave_um"] for m in metadata]
        widths = [m["bandwidth_um"] for m in metadata]
        if not np.isfinite(waves + widths).all() or min(waves + widths) <= 0:
            raise ValueError("Fixture spectral WCS returned invalid wavelength metadata")
        wavelengths.extend(zip(waves, widths))
        if any(
            count
            for meta in metadata
            for flag, count in meta["flag_counts"].items()
            if "SATUR" in flag or "OVERFLOW" in flag
        ):
            frame_warnings.append("SATURATION_POSSIBLE")
        mjd = float(np.median(times))
        predicted = position_at(query.target_key, mjd)
        predicted_px = None
        if predicted is not None:
            x, y = wcs.world_to_pixel(predicted)
            predicted_px = (float(x), float(shape[0] - 1 - y))
        frame_id = f"observed-{identity}-{visit}"
        frames.append(
            {
                "id": frame_id,
                "mjd": mjd,
                "iso": Time(mjd, format="mjd", scale="utc").isot + "Z",
                "wavelength_um": float(np.median(waves)),
                "bandwidth_um": float(np.median(widths)),
                "release": "+".join(sorted(releases)),
                "survey": visit,
                "bad_pixel_frac": float(np.mean(missing)),
                "predicted_px": predicted_px,
                "png": f"/api/frames/{frame_id}.png",
                "diff_png": f"/api/frames/{frame_id}/diff.png",
            }
        )

    if not has_coverage:
        raise NoCoverage
    lo, hi, published = 0.0, 1.0, {}
    if arrays:
        values = np.concatenate([image[np.isfinite(image)] for image in arrays])
        lo, hi = map(float, np.percentile(values, [2, 99.5]))
        if hi <= lo:
            hi = float(np.nextafter(lo, np.inf))
        differences = [image - arrays[0] for image in arrays]
        values = np.concatenate([diff[np.isfinite(diff)] for diff in differences])
        limit = float(np.percentile(np.abs(values), 99))
        if limit == 0:
            limit = float(np.max(np.abs(values))) or 1.0
        for frame, image, diff in zip(frames, arrays, differences, strict=True):
            # Separate slopes retain gray 128 at zero and use the full 0–255 range.
            signed = np.clip(np.nan_to_num(diff / limit, nan=0), -1, 1)
            published[frame["id"]] = (
                png_bytes(stretch(image, lo, hi)),
                png_bytes(np.rint(128 + signed * np.where(signed > 0, 127, 128))),
            )
        waves, widths = zip(*wavelengths)
        if max(waves) - min(waves) > min(widths):
            frame_warnings.append("MIXED_WAVELENGTH")
    if len(frames) < 3:
        frame_warnings.append("FEW_FRAMES")

    return {
        "grid": grid,
        "norm": {"vmin": lo, "vmax": hi, "stretch": "asinh"},
        "reference_frame_id": frames[0]["id"] if frames else None,
        "frames": frames,
        "warnings": list(dict.fromkeys(frame_warnings)),
    }, published
