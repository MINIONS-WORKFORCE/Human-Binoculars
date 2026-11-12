"""Median frames by detector and time cluster, on a fixed target-centered TAN grid."""

import itertools
import json
import warnings
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits
from astropy.time import Time
from astropy.visualization import AsinhStretch, ImageNormalize
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from shared.image_processing import reproject_compatible as reproject_interp
from tan_pipeline import DEC, FOV, OUT, RA, ROOT, load_cutout, tan_grid

# Official build_frames per section 6 of the API contract
from build_frames import build_frames


def make_frames(ra, dec, fov, det, *, manifest=None, output=None, gap_days=30):
    """FOV in degrees, detector 1..6. Median values stay in original MJy/sr units.

    Clusters split at gaps >30 days across all manifest observations, before filtering
    by detector. These are empirical visit groups, not official mission survey IDs.
    """
    if det not in range(1, 7) or gap_days <= 0:
        raise ValueError("det must be 1..6; gap_days must be positive")
    manifest = Path(manifest or OUT / "inputs.json")
    output = Path(output or OUT / "frames")
    output.mkdir(parents=True, exist_ok=True)
    entries = sorted(json.loads(manifest.read_text(encoding="utf-8")), key=lambda e: e["mjd"])
    ids = [(e["obs_id"], e["detector"]) for e in entries]
    if len(set(ids)) != len(ids):
        raise ValueError("Duplicate observation/detector in manifest")
    groups = []
    explicit = ["cluster_id" in e for e in entries]
    if any(explicit) and not all(explicit):
        raise ValueError("Mixed explicit and inferred cluster membership")
    if all(explicit) and entries:
        for cluster_id in sorted({e["cluster_id"] for e in entries}):
            group = [e for e in entries if e["cluster_id"] == cluster_id]
            groups.append((cluster_id, group))
    else:
        inferred = []
        for entry in entries:
            if not inferred or entry["mjd"] - inferred[-1][-1]["mjd"] > gap_days:
                inferred.append([])
            inferred[-1].append(entry)
        groups = list(enumerate(inferred))
    wcs, shape = tan_grid(ra, dec, fov)
    products, arrays = [], []
    unit = None
    for group_id, group in groups:
        selected = [e for e in group if e["detector"] == f"D{det}"]
        if not selected:
            continue
        images, metadata = [], []
        for entry in selected:
            import hashlib

            path = ROOT / entry["path"]
            if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
                raise ValueError(f"Checksum mismatch: {path}")
            image, native, info = load_cutout(path, ra, dec)
            if info["detector"] != det or info["obs_id"] != entry["obs_id"]:
                raise ValueError("FITS identity differs from manifest")
            if unit is None:
                unit = info["bunit"]
            if not unit or unit != info["bunit"]:
                raise ValueError("Missing or inconsistent brightness units")
            aligned, footprint = reproject_interp((image, native), wcs, shape_out=shape)
            images.append(np.where(footprint > 0, aligned, np.nan))
            metadata.append(info)
        cube = np.asarray(images)
        count = np.isfinite(cube).sum(axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            median = np.nanmedian(cube, axis=0)
        if not np.isfinite(median).any():
            raise ValueError("No valid output pixels")
        label = f"D{det}_visit{group_id:02}"
        hdr = wcs.to_header()
        hdr["BUNIT"] = unit
        hdr["HISTORY"] = "Masked native bad bits; bilinear TAN; unweighted pixelwise median"
        fits.HDUList(
            [
                fits.PrimaryHDU(),
                fits.ImageHDU(median.astype("float32"), hdr, name="MEDIAN"),
                fits.ImageHDU(count.astype("int16"), wcs.to_header(), name="NVALID"),
            ]
        ).writeto(output / f"{label}.fits", overwrite=True)
        products.append(
            {
                "label": label,
                "cluster_id": group_id,
                "n_inputs": len(selected),
                "cluster_mjd": [
                    group[0].get("cluster_start_mjd", group[0]["mjd"]),
                    group[0].get("cluster_end_mjd", group[-1]["mjd"]),
                ],
                "selected_mjd": [min(e["mjd"] for e in selected), max(e["mjd"] for e in selected)],
                "wave_range_um": [
                    min(m["wave_um"] for m in metadata),
                    max(m["wave_um"] for m in metadata),
                ],
                "valid_fraction": float((count > 0).mean()),
                "min_max_nvalid": [int(count.min()), int(count.max())],
                "inputs": metadata,
            }
        )
        arrays.append(median)
    if not arrays:
        raise ValueError(f"No D{det} observations in manifest")
    values = np.concatenate([a[np.isfinite(a)] for a in arrays])
    lo, hi = map(float, np.percentile(values, [2, 99.5]))
    norm = ImageNormalize(vmin=lo, vmax=hi, stretch=AsinhStretch())
    differences = [b - a for a, b in itertools.pairwise(arrays)]
    valid_diff = [d[np.isfinite(d)] for d in differences if np.isfinite(d).any()]
    limit = float(np.percentile(np.abs(np.concatenate(valid_diff)), 99)) if valid_diff else None
    if limit == 0:
        limit = float(np.finfo(float).eps)
    for index, (product, image) in enumerate(zip(products, arrays)):
        fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
        cmap = plt.get_cmap("gray").with_extremes(bad="#703090")
        im = ax.imshow(image, origin="lower", cmap=cmap, norm=norm)
        start, end = Time(product["selected_mjd"], format="mjd").iso
        ax.set_title(
            f"{product['label']} / median of {product['n_inputs']}\n{start[:10]} to {end[:10]}"
        )
        fig.colorbar(im, ax=ax, label=unit)
        fig.savefig(output / f"{product['label']}.png", dpi=140)
        plt.close(fig)
        if index == 0:
            continue
        diff = differences[index - 1]
        name = f"{product['label']}_minus_{products[index - 1]['label']}"
        fits.PrimaryHDU(diff.astype("float32"), hdr).writeto(
            output / f"{name}.fits", overwrite=True
        )
        fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
        difference_cmap = plt.get_cmap("RdBu_r").with_extremes(bad="#703090")
        im = ax.imshow(diff, origin="lower", cmap=difference_cmap, vmin=-limit, vmax=limit)
        ax.set_title(name + "\nVisual difference; wavelengths/PSF/background unmatched", fontsize=9)
        fig.colorbar(im, ax=ax, label=unit)
        fig.savefig(output / f"{name}.png", dpi=140)
        plt.close(fig)
    report = {
        "ra_deg": ra,
        "dec_deg": dec,
        "fov_deg": fov,
        "detector": det,
        "grouping": {
            "gap_days": gap_days,
            "kind": "empirical time clusters",
            "reason": "Separate observing visits while keeping adjacent-day exposures together; not official survey IDs.",
            "scope": "boundaries from full local SIA query, not complete mission history"
            if any(explicit)
            else "boundaries from selected manifest, not complete mission history",
            "membership_source": "full catalog clusters in manifest"
            if any(explicit)
            else "selected manifest time gaps",
        },
        "frames": products,
        "display": {"stretch": "asinh", "vmin": lo, "vmax": hi, "difference_abs_limit": limit},
        "limits": [
            "Same detector mixes wavelengths: not a monochromatic or photometric coadd.",
            "No PSF matching, background subtraction, or propagated covariance; difference is visual only.",
            "Median uses valid pixels only; NVALID records spatially varying exposure counts.",
            "One-input groups remain single images; masked saturation is not recovered.",
        ],
    }
    (output / f"D{det}_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    for detector in (3, 6):
        result = make_frames(RA, DEC, FOV, detector)
        print(f"D{detector}: {len(result['frames'])} frames")
