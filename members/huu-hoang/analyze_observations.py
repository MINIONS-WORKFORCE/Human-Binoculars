"""Inspect image changes and measure exploratory spectrum samples from sky observations."""

import argparse
import hashlib
import json
import warnings

import astropy.units as u
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from align_sky_images import ROOT, load_cutout
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.stats import mad_std
from astropy.table import Table
from astropy.time import Time
from astropy.wcs.utils import proj_plane_pixel_area
from build_image_series import build_image_series
from photutils.aperture import CircularAnnulus, CircularAperture
from photutils.detection import find_peaks
from process_target_observations import BASE, acquire_target, resolve
from scipy.ndimage import binary_dilation

OUT = ROOT / "data" / "observation_products"


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding="utf-8")


def dipoles(image, sigma=5.0, max_distance=8.0):
    """Pair signed peaks greedily, excluding NaN neighborhoods and image edges."""
    image = np.asarray(image, dtype=float)
    valid = np.isfinite(image)
    if valid.sum() < 30:
        return {"status": "insufficient_pixels", "pairs": []}
    noise = float(mad_std(image[valid]))
    if not np.isfinite(noise) or noise <= 0:
        return {"status": "no_noise_estimate", "pairs": []}
    mask = binary_dilation(~valid, iterations=2)
    mask[:2] = mask[-2:] = True
    mask[:, :2] = mask[:, -2:] = True
    residual = np.where(valid, image - np.median(image[valid]), 0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        positive = find_peaks(residual, sigma * noise, box_size=5, mask=mask)
        negative = find_peaks(-residual, sigma * noise, box_size=5, mask=mask)
    edges = []
    if positive is not None and negative is not None:
        for i, p in enumerate(positive):
            for j, n in enumerate(negative):
                distance = float(np.hypot(p["x_peak"] - n["x_peak"], p["y_peak"] - n["y_peak"]))
                if 0 < distance <= max_distance:
                    edges.append((distance, i, j))
    pairs, used_p, used_n = [], set(), set()
    for distance, i, j in sorted(edges):
        if i in used_p or j in used_n:
            continue
        used_p.add(i)
        used_n.add(j)
        p, n = positive[i], negative[j]
        pairs.append(
            {
                "positive_xy": [int(p["x_peak"]), int(p["y_peak"])],
                "negative_xy": [int(n["x_peak"]), int(n["y_peak"])],
                "separation_pixels": distance,
            }
        )
    return {
        "status": "ok",
        "noise_mad": noise,
        "threshold_sigma": sigma,
        "max_distance_pixels": max_distance,
        "pairs": pairs,
    }


def find_image_changes():
    results = []
    paths = sorted((OUT / "image_series").glob("*/detector_*_minus_*.fits"))
    for path in paths:
        with fits.open(path) as h:
            data = h[0].data.copy()
        report = dipoles(data)
        report["input"] = str(path.relative_to(ROOT))
        results.append(report)
    # Positive control on synthetic data, with a known 5-pixel displacement.
    yy, xx = np.indices((59, 59))
    rng = np.random.default_rng(20261108)
    synthetic = rng.normal(0, 1, (59, 59))
    for x, amplitude in ((31, 40), (26, -40)):
        synthetic += amplitude * np.exp(-((xx - x) ** 2 + (yy - 29) ** 2) / (2 * 0.9**2))
    control = dipoles(synthetic)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, data, result, title in (
        (axes[0], synthetic, control, "Synthetic control (not sky data)"),
        (axes[1], fits.getdata(paths[0]), results[0], "Real visual difference: candidates only"),
    ):
        limit = max(float(np.nanpercentile(np.abs(data), 99)), 1e-9)
        ax.imshow(
            data,
            origin="lower",
            cmap=plt.get_cmap("RdBu_r").with_extremes(bad="#703090"),
            vmin=-limit,
            vmax=limit,
        )
        for pair in result["pairs"]:
            ax.plot(*zip(pair["negative_xy"], pair["positive_xy"]), "g.-")
        ax.set_title(title, fontsize=9)
    (OUT / "change_candidates").mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / "change_candidates" / "signed_change_candidates.png", dpi=140)
    plt.close(fig)
    data = fits.getdata(paths[0])
    limit = max(float(np.nanpercentile(np.abs(data), 99)), 1e-9)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    for ax, cmap, title in (
        (axes[0], "RdBu_r", "Before: missing pixels transparent/white"),
        (
            axes[1],
            plt.get_cmap("RdBu_r").with_extremes(bad="#703090"),
            "After: missing pixels purple",
        ),
    ):
        ax.imshow(data, origin="lower", cmap=cmap, vmin=-limit, vmax=limit)
        ax.set_title(title, fontsize=9)
    fig.savefig(OUT / "change_candidates" / "missing_data_display_comparison.png", dpi=140)
    plt.close(fig)
    save(
        OUT / "change_candidates" / "change_candidates_report.json",
        {
            "real_differences": results,
            "synthetic_control": control,
            "science_status": "unvalidated_candidates; PSF, wavelengths, background and alignment can mimic motion",
            "integration_issues": "none returned by GitHub query; no app integration acceptance claimed",
        },
    )


def aperture_measure(image, variance, xy, background_mask, annulus_radii=(4.0, 7.0)):
    """Strict full native aperture; incomplete apertures are rejected, never filled."""
    aperture = CircularAperture(xy, r=2.0).to_mask(method="exact").to_image(image.shape)
    if aperture is None:
        return {"status": "outside_image"}
    annulus = (
        CircularAnnulus(xy, r_in=annulus_radii[0], r_out=annulus_radii[1])
        .to_mask(method="center")
        .to_image(image.shape)
    )
    good = np.isfinite(image) & np.isfinite(variance) & (variance >= 0)
    footprint = aperture > 0
    fraction = float(aperture[good].sum() / (np.pi * 4))
    if fraction < 1 - 1e-6:
        return {"status": "masked_or_edge_aperture", "valid_aperture_fraction": fraction}
    bg = (annulus > 0) & good & ~background_mask if annulus is not None else np.zeros_like(good)
    if bg.sum() < 20:
        return {"status": "insufficient_background", "background_pixels": int(bg.sum())}
    background = float(np.median(image[bg]))
    bg_error = float(1.2533 * mad_std(image[bg]) / np.sqrt(bg.sum()))
    weights = aperture[footprint]
    value = float(np.sum(weights * (image[footprint] - background)))
    error = float(
        np.sqrt(np.sum(weights**2 * variance[footprint]) + (weights.sum() * bg_error) ** 2)
    )
    return {
        "status": "ok",
        "sum_mjy_sr": value,
        "error_mjy_sr": error,
        "background_mjy_sr": background,
        "background_pixels": int(bg.sum()),
        "valid_aperture_fraction": fraction,
    }


def extract_spectrum_samples(download=False, wide_background=False):
    output = (
        OUT / "luhman16_spectrum" / ("wide_background" if wide_background else "local_background")
    )
    radii = (12.0, 25.0) if wide_background else (4.0, 7.0)
    folder = BASE / "luhman-16"
    if download:
        info = resolve("luhman-16", "WISE J104915.57-531906.1")
        acquire_target(info)
    info = json.loads((folder / "target_coordinates.json").read_text())
    entries = json.loads((folder / "observation_manifest.json").read_text())
    rows = []
    for entry in entries:
        path = ROOT / entry["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Checksum mismatch: {path}")
        coord = SkyCoord(
            *info["j2000_deg"],
            unit="deg",
            pm_ra_cosdec=info["pm_mas_yr"][0] * u.mas / u.yr,
            pm_dec=info["pm_mas_yr"][1] * u.mas / u.yr,
            obstime=Time("J2000"),
        )
        coord = coord.apply_space_motion(new_obstime=Time(entry["mjd"], format="mjd"))
        image, wcs, meta = load_cutout(path, coord.ra.deg, coord.dec.deg)
        if meta["obs_id"] != entry["obs_id"] or f"D{meta['detector']}" != entry["detector"]:
            raise ValueError("FITS identity differs from manifest")
        if u.Unit(meta["bunit"]) != u.MJy / u.sr:
            raise ValueError("Expected surface brightness MJy/sr")
        with fits.open(path) as h:
            variance = h["VARIANCE"].data.astype(float)
            if u.Unit(h["VARIANCE"].header["BUNIT"]) != (u.MJy / u.sr) ** 2:
                raise ValueError("Unexpected variance units")
            fh = h["FLAGS"].header
            flags = h["FLAGS"].data
            background_mask = (flags & (1 << int(fh["MP_SOURCE"]))) != 0
        xy = tuple(float(v) for v in wcs.world_to_pixel(coord))
        result = aperture_measure(image, variance, xy, background_mask, radii)
        # Native projection-plane area: explicit small-field approximation, no PSF correction.
        factor = abs(float(proj_plane_pixel_area(wcs))) * (np.pi / 180) ** 2 * 1e9
        row = {
            "obs_id": entry["obs_id"],
            "detector": entry["detector"],
            "mjd": entry["mjd"],
            "wave_um": meta["wave_um"],
            "bandwidth_um": meta["bandwidth_um"],
            "x": xy[0],
            "y": xy[1],
            **result,
        }
        if result["status"] == "ok":
            row["aperture_mjy"] = result["sum_mjy_sr"] * factor
            row["error_mjy"] = result["error_mjy_sr"] * factor
        rows.append(row)
    save(
        output / "spectrum_extraction_report.json",
        {
            "target": info,
            "samples": rows,
            "accepted_samples": sum(r["status"] == "ok" for r in rows),
            "science_review": "pending Nguyen; forced-position sparse aperture photometry, not a confirmed detection or calibrated full spectrum",
            "aperture_radius_pixels": 2,
            "background_annulus_pixels": list(radii),
            "background_strategy": "wide annulus sensitivity experiment"
            if wide_background
            else "baseline local annulus",
            "limits": [
                "No aperture/PSF correction; Luhman binary unresolved/blended",
                "Linear proper motion only; no parallax/orbit/RV",
                "Three detector subsets, non-simultaneous samples; no interpolation across gaps",
                "Projection-plane solid angle approximation; independent native variance plus approximate background error",
                "No upper limits or molecular-feature claims; source identity needs review",
            ],
        },
    )
    Table(rows).write(output / "spectrum_samples.ecsv", overwrite=True)
    fig, ax = plt.subplots(figsize=(8, 4), constrained_layout=True)
    for det in ("D1", "D3", "D6"):
        selected = [r for r in rows if r["status"] == "ok" and r["detector"] == det]
        if not selected:
            continue
        ax.errorbar(
            [r["wave_um"] for r in selected],
            [r["aperture_mjy"] for r in selected],
            yerr=[r["error_mjy"] for r in selected],
            fmt="o",
            label=det,
        )
    if not any(r["status"] == "ok" for r in rows):
        ax.text(
            0.5,
            0.5,
            "No accepted real samples\nSee QA reasons in spectrum_extraction_report.json",
            ha="center",
            va="center",
            transform=ax.transAxes,
        )
    ax.set(
        xlabel="Wavelength at predicted position (um)",
        ylabel="Uncorrected aperture flux (mJy)",
        title="Luhman 16 practice samples; pending science review",
    )
    if any(r["status"] == "ok" for r in rows):
        ax.legend()
    fig.savefig(output / "spectrum_samples.png", dpi=140)
    plt.close(fig)
    first = rows[0]
    first_path = ROOT / entries[0]["path"]
    with fits.open(first_path) as h:
        native = h["IMAGE"].data.astype(float)
        source_mask = (h["FLAGS"].data & (1 << int(h["FLAGS"].header["MP_SOURCE"]))) != 0
    fig, axes = plt.subplots(1, 2, figsize=(10, 4), constrained_layout=True)
    low, high = np.nanpercentile(native, [2, 99])
    axes[0].imshow(
        native,
        origin="lower",
        cmap=plt.get_cmap("gray").with_extremes(bad="#703090"),
        vmin=low,
        vmax=high,
    )
    axes[1].imshow(source_mask, origin="lower", cmap="Greys", vmin=0, vmax=1)
    for ax in axes:
        for radius, color in ((2, "lime"), (radii[0], "orange"), (radii[1], "orange")):
            ax.add_patch(plt.Circle((first["x"], first["y"]), radius, fill=False, color=color))
    axes[0].set_title("Native image + aperture/annulus", fontsize=9)
    axes[1].set_title("White: no SOURCE; black: SOURCE (excluded from background)", fontsize=8)
    fig.savefig(output / "background_selection_check.png", dpi=140)
    plt.close(fig)
    # A separate synthetic teaching control; never added to the real sample table.
    yy, xx = np.indices((41, 41))
    toy = 10 + 100 * np.exp(-((xx - 20) ** 2 + (yy - 20) ** 2) / (2 * 0.8**2))
    control = aperture_measure(toy, np.ones_like(toy), (20, 20), np.zeros_like(toy, dtype=bool))
    save(
        output / "synthetic_control.json",
        {
            "kind": "synthetic teaching data, not Luhman 16",
            "description": "Known Gaussian source plus constant background 10; native variance 1",
            "measurement": control,
        },
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["build-images", "find-changes", "extract-spectrum"])
    parser.add_argument("--download", action="store_true")
    parser.add_argument(
        "--wide-background",
        action="store_true",
        help="extract-spectrum only: separate 12-25 pixel background experiment, pending science review",
    )
    args = parser.parse_args()
    if args.command == "build-images":
        build_image_series()
    elif args.command == "find-changes":
        find_image_changes()
    else:
        extract_spectrum_samples(args.download, args.wide_background)
