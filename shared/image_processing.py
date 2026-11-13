"""Shared fixed-sky-grid products; PNG coordinates have a top-left origin.

Motion predictions use catalog proper motion only. Difference/RGB products are
visual previews, without wavelength, PSF or background matching.
"""

import hashlib
import io
import itertools
import json
import warnings
from pathlib import Path

import astropy.units as u
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
from PIL import Image, ImageDraw


def mask_flags(pixels, flags, header):
    """Reject quality bits, including saturation, retaining SOURCE/FULLSAMPLE."""
    bits = {
        int(header[k])
        for k in header
        if k.startswith("MP_") and k not in {"MP_SOURCE", "MP_FULLSAMPLE"}
    }
    if not bits:
        raise ValueError("Missing flag definitions")
    mask = sum(1 << bit for bit in bits)
    return np.where(np.isfinite(pixels) & ((flags & mask) == 0), pixels, np.nan)


def png_bytes(rgb):
    buffer = io.BytesIO()
    Image.fromarray(np.flipud(rgb).astype(np.uint8)).save(buffer, format="PNG")
    return buffer.getvalue()


def stretch(pixels, low, high):
    values = np.nan_to_num((pixels - low) / max(high - low, 1e-12), nan=0.0)
    return np.rint(255 * np.arcsinh(10 * np.clip(values, 0, 1)) / np.arcsinh(10))


def frame_png(pixels, low, high):
    gray = stretch(pixels, low, high)
    rgb = np.repeat(gray[..., None], 3, axis=-1)
    rgb[~np.isfinite(pixels)] = [112, 48, 144]
    return png_bytes(rgb)


def diff_png(pixels, limit):
    """Red positive, blue negative, purple missing, one symmetric series scale."""
    value = np.clip(np.nan_to_num(pixels, nan=0.0) / max(limit, 1e-12), -1, 1)
    rgb = np.stack(
        [
            255 * (1 + np.minimum(value, 0)),
            255 * (1 - np.abs(value)),
            255 * (1 - np.maximum(value, 0)),
        ],
        axis=-1,
    )
    rgb[~np.isfinite(pixels)] = [112, 48, 144]
    return png_bytes(np.rint(rgb))


def rgb_png(d6, d3, d1):
    """D6/D3/D1 -> R/G/B, same aligned grid required; missing -> purple."""
    planes = [np.asarray(p, dtype=float) for p in (d6, d3, d1)]
    if len({p.shape for p in planes}) != 1 or planes[0].ndim != 2:
        raise ValueError("RGB planes must share a 2-D sky grid")
    channels = []
    for plane in planes:
        finite = plane[np.isfinite(plane)]
        if not finite.size:
            raise ValueError("RGB channel has no usable pixels")
        channels.append(stretch(plane, *np.percentile(finite, [2, 99.5])))
    rgb = np.stack(channels, axis=-1)
    rgb[~np.all(np.isfinite(planes), axis=0)] = [112, 48, 144]
    return png_bytes(rgb)


def target_at(target, mjd):
    coord = SkyCoord(
        *target["j2000_deg"],
        unit="deg",
        obstime=Time("J2000"),
        pm_ra_cosdec=target["pm_mas_yr"][0] * u.mas / u.yr,
        pm_dec=target["pm_mas_yr"][1] * u.mas / u.yr,
    )
    return coord.apply_space_motion(new_obstime=Time(mjd, format="mjd"))


def reproject_bilinear(input_data, grid, shape_out):
    """2-D celestial WCS reprojection using SciPy, with conservative NaN edges.

    Only samples whose centers lie inside the native pixel-center bounds are
    retained. This is narrower than reproject's half-pixel edge extension.
    """
    from astropy.wcs.utils import pixel_to_pixel
    from scipy.ndimage import map_coordinates

    data, source_wcs = input_data
    yy, xx = np.indices(shape_out, dtype=float)
    sx, sy = pixel_to_pixel(grid, source_wcs, xx, yy)
    rx, ry = pixel_to_pixel(source_wcs, grid, sx, sy)
    valid = (
        np.isfinite(sx)
        & np.isfinite(sy)
        & (np.abs(rx - xx) < 1e-4)
        & (np.abs(ry - yy) < 1e-4)
        & (sx >= -1e-7)
        & (sx <= data.shape[1] - 1 + 1e-7)
        & (sy >= -1e-7)
        & (sy <= data.shape[0] - 1 + 1e-7)
    )
    sx = np.clip(np.where(valid, sx, 0), 0, data.shape[1] - 1)
    sy = np.clip(np.where(valid, sy, 0), 0, data.shape[0] - 1)
    aligned = map_coordinates(
        np.asarray(data, dtype=float),
        [sy, sx],
        order=1,
        mode="constant",
        cval=np.nan,
        prefilter=False,
    )
    aligned[~valid] = np.nan
    return aligned, np.isfinite(aligned).astype(float)


def reproject_compatible(input_data, grid, shape_out, order="bilinear"):
    """Use reproject when available; fall back to WCS bilinear interpolation."""
    try:
        from reproject import reproject_interp
    except ImportError:
        if order != "bilinear":
            raise ValueError("Fallback supports bilinear interpolation only")
        return reproject_bilinear(input_data, grid, shape_out)
    return reproject_interp(input_data, grid, shape_out=shape_out, order=order)


def build_frames(
    cutouts,
    target,
    *,
    root=Path("."),
    output=None,
    fov_deg=0.1,
    scale_arcsec=6.2,
    gap_days=30,
    interpolation="wcs-bilinear",
):
    """Build detector x visit medians from manifest entries and target metadata.

    Entries contain path, obs_id, detector (D1..D6), mjd and optional sha256,
    cluster_id. All detectors share one TAN grid at the temporal midpoint of
    the input series. Return JSON metadata and filename -> PNG bytes.
    """
    if interpolation == "reproject":
        from reproject import reproject_interp
    elif interpolation == "wcs-bilinear":
        reproject_interp = reproject_bilinear
    else:
        raise ValueError("Unknown interpolation backend")

    entries = sorted(cutouts, key=lambda row: row["mjd"])
    if not entries or not all(np.isfinite(e["mjd"]) for e in entries):
        raise ValueError("Finite observation times required")
    if not (0 < fov_deg <= 2 and scale_arcsec > 0 and gap_days > 0):
        raise ValueError("Invalid grid or grouping parameters")
    identities = [(e["obs_id"], e["detector"]) for e in entries]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate observation/detector")
    explicit = ["cluster_id" in e for e in entries]
    if any(explicit) and not all(explicit):
        raise ValueError("Mixed cluster membership")
    midpoint = (entries[0]["mjd"] + entries[-1]["mjd"]) / 2
    center = target_at(target, midpoint)
    size = int(np.ceil(fov_deg * 3600 / scale_arcsec))
    size += size % 2 == 0
    grid = WCS(naxis=2)
    grid.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    grid.wcs.crval = [center.ra.deg, center.dec.deg]
    grid.wcs.crpix = [(size + 1) / 2] * 2
    grid.wcs.cdelt = [-scale_arcsec / 3600, scale_arcsec / 3600]
    groups, cluster, unit = {}, 0, None
    for index, entry in enumerate(entries):
        if index and entry["mjd"] - entries[index - 1]["mjd"] > gap_days:
            cluster += 1
        key = (entry["detector"], entry.get("cluster_id", cluster))
        path = Path(root) / entry["path"]
        if "sha256" in entry and hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Checksum mismatch: {path}")
        with fits.open(path, memmap=False) as hdus:
            hdu, flags = hdus["IMAGE"], hdus["FLAGS"]
            if (
                str(hdu.header["OBSID"]) != entry["obs_id"]
                or f"D{hdu.header['DETECTOR']}" != entry["detector"]
            ):
                raise ValueError("Source identity mismatch")
            current_unit = hdu.header.get("BUNIT")
            if not current_unit or (unit is not None and current_unit != unit):
                raise ValueError("Inconsistent image units")
            unit = current_unit
            pixels = mask_flags(hdu.data.astype(float), flags.data, flags.header)
            aligned, footprint = reproject_interp(
                (pixels, WCS(hdu.header, fobj=hdus).celestial), grid, shape_out=(size, size)
            )
            aligned[footprint <= 0] = np.nan
        groups.setdefault(key, []).append((entry, aligned))
    products = []
    for (detector, visit), group in sorted(groups.items()):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            median = np.nanmedian(np.stack([p for _, p in group]), axis=0)
        epoch = float(np.mean([e["mjd"] for e, _ in group]))
        x, y = map(float, grid.world_to_pixel(target_at(target, epoch)))
        products.append(
            (
                {
                    "frame_id": f"{detector}-visit-{visit}",
                    "detector": detector,
                    "visit": visit,
                    "mjd": epoch,
                    "n_images": len(group),
                    "predicted_px": [x, size - 1 - y],
                    "source_obs_ids": [e["obs_id"] for e, _ in group],
                },
                median,
            )
        )
    products.sort(key=lambda item: (item[0]["detector"], item[0]["mjd"]))
    images, frames, norms = {}, [], {}
    for detector in sorted({f["detector"] for f, _ in products}):
        sequence = [(f, a) for f, a in products if f["detector"] == detector]
        values = np.concatenate([a[np.isfinite(a)] for _, a in sequence])
        if not values.size:
            raise ValueError(f"No usable pixels for {detector}")
        low, high = map(float, np.percentile(values, [2, 99.5]))
        differences = [b - a for (_, a), (_, b) in itertools.pairwise(sequence)]
        finite = [np.abs(d[np.isfinite(d)]) for d in differences if np.isfinite(d).any()]
        limit = max(float(np.percentile(np.concatenate(finite), 99)), 1e-12) if finite else 1
        norms[detector] = {"vmin": low, "vmax": high, "difference_abs_limit": limit}
        for index, (frame, pixels) in enumerate(sequence):
            name = frame["frame_id"]
            frame["image_url"] = name + ".png"
            images[name + ".png"] = frame_png(pixels, low, high)
            annotated = Image.open(io.BytesIO(images[name + ".png"])).convert("RGB")
            draw = ImageDraw.Draw(annotated)
            x, y = frame["predicted_px"]
            if 0 <= x < size and 0 <= y < size:
                draw.line([(x - 3, y), (x + 3, y)], fill="red")
                draw.line([(x, y - 3), (x, y + 3)], fill="red")
            buffer = io.BytesIO()
            annotated.save(buffer, format="PNG")
            frame["crosshair_url"] = name + "-crosshair.png"
            images[frame["crosshair_url"]] = buffer.getvalue()
            if index:
                frame["diff_png"] = name + "-diff.png"
                images[frame["diff_png"]] = diff_png(differences[index - 1], limit)
            frames.append(frame)
    for visit in sorted({f["visit"] for f, _ in products}):
        planes = {f["detector"]: a for f, a in products if f["visit"] == visit}
        if all(d in planes and np.isfinite(planes[d]).any() for d in ("D6", "D3", "D1")):
            images[f"rgb-visit-{visit}.png"] = rgb_png(*(planes[d] for d in ("D6", "D3", "D1")))
    report = {
        "interpolation": interpolation,
        "target": target,
        "center_mjd": midpoint,
        "center_deg": [float(center.ra.deg), float(center.dec.deg)],
        "shape": [size, size],
        "wcs": dict(grid.to_header()),
        "display": norms,
        "frames": frames,
        "limits": "Proper-motion prediction only; no annual parallax/RV/orbit. "
        "See separate validation.json for measured-source diagnostics. "
        "Differences/RGB are visual previews; wcs-bilinear uses conservative edges.",
    }
    if output is not None:
        folder = Path(output)
        folder.mkdir(parents=True, exist_ok=True)
        for frame, pixels in products:
            header = grid.to_header()
            header["BUNIT"] = unit
            header["MJD-OBS"] = frame["mjd"]
            fits.PrimaryHDU(pixels.astype("float32"), header).writeto(
                folder / (frame["frame_id"] + ".fits"), overwrite=True
            )
        for name, content in images.items():
            (folder / name).write_bytes(content)
        (folder / "frames.json").write_text(
            json.dumps(report, indent=2, allow_nan=False), encoding="utf-8"
        )
    return report, images
