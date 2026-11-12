"""Build aligned, normalized median frames and difference products for SPHEREx cutouts.

Implements the official build_frames() pipeline:
  - Reprojects native cutouts onto a common TAN grid.
  - Places the grid center at the temporal midpoint of the cutout sequence,
    allowing high-proper-motion targets (e.g. Barnard's Star) to pass through the center.
  - Clusters observations by time (e.g. 30-day visit separation).
  - Computes robust pixelwise medians for each visit.
  - Applies a shared AsinhStretch normalization across all frames of the detector.
  - Computes predicted_px for each frame with flipped vertical axis (PNG top-left origin):
      x_png = x_fits,  y_png = (height - 1) - y_fits
  - Generates standard frame PNGs, difference PNGs (with RdBu_r colormap and #703090 missing mask).
  - Produces verification PNGs with crosshairs overlaid at predicted_px to verify target motion.
"""

from __future__ import annotations

import hashlib
import json
import warnings
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.visualization import AsinhStretch, ImageNormalize
from astropy.wcs import WCS
import astropy.units as u
from PIL import Image
from reproject import reproject_interp

from tan_pipeline import ROOT, load_cutout, tan_grid

# Missing/masked data color convention across the project
COLOR_MISSING = "#703090"  # Purple


def compute_predicted_pixel(
    coord_ref: SkyCoord,
    mjd: float,
    wcs: WCS,
    height: int,
) -> tuple[float, float]:
    """Compute (x_png, y_png) using PNG top-left origin convention.
    
    x_png = x_fits
    y_png = (height - 1) - y_fits
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if "s" in coord_ref.frame.data.differentials:
            star_pos = coord_ref.apply_space_motion(new_obstime=Time(mjd, format="mjd"))
        else:
            star_pos = coord_ref
        x_fits, y_fits = map(float, wcs.world_to_pixel(star_pos))
    x_png = x_fits
    y_png = (height - 1) - y_fits
    return x_png, y_png


def draw_crosshair_on_ax(
    ax: plt.Axes,
    cx: float,
    cy: float,
    gap: float = 1.5,
    arm: float = 3.0,
    color: str = "red",
    outline_color: str = "black",
    lw: float = 1.6,
) -> None:
    """Draw a 4-tick crosshair with a central gap and dark outline so the target star core remains visible."""
    segments = [
        ((cx - gap - arm, cx - gap), (cy, cy)),
        ((cx + gap, cx + gap + arm), (cy, cy)),
        ((cx, cx), (cy - gap - arm, cy - gap)),
        ((cx, cx), (cy + gap, cy + gap + arm)),
    ]
    # Outline
    for (x0, x1), (y0, y1) in segments:
        ax.plot([x0, x1], [y0, y1], color=outline_color, lw=lw + 1.2, solid_capstyle="butt")
    # Foreground color
    for (x0, x1), (y0, y1) in segments:
        ax.plot([x0, x1], [y0, y1], color=color, lw=lw, solid_capstyle="butt")


def build_frames(
    cutouts: list[dict[str, Any]] | list[Path | str] | Path | str,
    target: dict[str, Any] | str | None = None,
    size: float = 0.1,
    detector: int = 6,
    pixscale_arcsec: float = 6.2,
    gap_days: float = 30.0,
    output_dir: Path | str | None = None,
    generate_verification: bool = True,
    verification_dir: Path | str | None = None,
    fov_deg: float | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Execute end-to-end frame building and alignment on SPHEREx cutouts.

    Conforms to Section 6 of the team API contract:
      build_frames(cutouts, target, size)

    Args:
        cutouts: List of cutout metadata dicts, file paths, or path to inputs.json.
        target: Target name/key string (e.g. "barnard") or target metadata dict:
            {
                "name": str,
                "target_key": str,
                "ra": float,         # J2000 deg
                "dec": float,        # J2000 deg
                "pmra": float,       # mas/yr (optional)
                "pmdec": float,      # mas/yr (optional)
                "epoch": str,        # default "J2000"
            }
        size: Field of view / cutout size in degrees (default 0.1 deg).
        detector: SPHEREx detector number (1..6). Default is 6.
        pixscale_arcsec: Pixel scale in arcsec/pixel. Default is 6.2.
        gap_days: Maximum day gap within an observing cluster. Default is 30.0.
        output_dir: Folder to save FITS, standard PNGs, and report.json.
        generate_verification: Whether to render PNGs with crosshair and comparison GIF.
        verification_dir: Folder for verification artifacts.

    Returns:
        Dictionary conforming to API 0.1 Frames specification.
    """
    if fov_deg is not None:
        size = fov_deg
    elif "fov" in kwargs:
        size = kwargs["fov"]
    fov_deg = size

    # Allow string target key e.g. "barnard"
    if isinstance(target, str):
        target_file = ROOT / "data" / "five_targets" / target / "target.json"
        if target_file.exists():
            target = json.loads(target_file.read_text(encoding="utf-8"))
        else:
            target = {"name": target, "target_key": target}
    if detector not in range(1, 7):
        raise ValueError(f"Detector must be between 1 and 6, got {detector}")

    # 1. Parse and standardize cutouts list
    entries: list[dict[str, Any]] = []
    if isinstance(cutouts, (str, Path)):
        cpath = Path(cutouts)
        if cpath.is_file() and cpath.suffix == ".json":
            entries = json.loads(cpath.read_text(encoding="utf-8"))
        elif cpath.is_dir():
            fits_files = sorted(cpath.glob("*.fits"))
            for p in fits_files:
                entries.append({"path": str(p)})
        elif cpath.is_file() and cpath.suffix == ".fits":
            entries.append({"path": str(cpath)})
        else:
            raise ValueError(f"Unsupported cutouts path: {cutouts}")
    elif isinstance(cutouts, list):
        for item in cutouts:
            if isinstance(item, dict):
                entries.append(item)
            elif isinstance(item, (str, Path)):
                entries.append({"path": str(item)})
            else:
                raise TypeError(f"Unsupported item in cutouts: {type(item)}")
    else:
        raise TypeError(f"Unsupported cutouts type: {type(cutouts)}")

    if not entries:
        raise ValueError("No cutouts provided to build_frames")

    # Read minimal header metadata if missing
    parsed_entries: list[dict[str, Any]] = []
    for item in entries:
        entry = dict(item)
        fpath = Path(entry["path"])
        if not fpath.is_absolute():
            fpath = ROOT / fpath
        if not fpath.exists():
            raise FileNotFoundError(f"Cutout file not found: {fpath}")

        # If metadata is missing, read from FITS header
        if "mjd" not in entry or "detector" not in entry:
            with fits.open(fpath) as h:
                hdr = h["IMAGE"].header
                entry.setdefault("obs_id", hdr.get("OBSID", fpath.stem))
                det_num = int(hdr.get("DETECTOR", detector))
                entry.setdefault("detector", f"D{det_num}")
                entry.setdefault("mjd", float(hdr.get("MJD-OBS", hdr.get("MJD", 60000.0))))
                entry.setdefault("date_obs", hdr.get("DATE-OBS", "2025-01-01T00:00:00"))
        
        # Standardize detector representation
        det_val = entry["detector"]
        det_int = int(det_val[1:]) if isinstance(det_val, str) and det_val.startswith("D") else int(det_val)
        if det_int == detector:
            entry["detector_int"] = det_int
            entry["resolved_path"] = fpath
            parsed_entries.append(entry)

    if not parsed_entries:
        raise ValueError(f"No cutouts matched detector D{detector}")

    parsed_entries.sort(key=lambda e: float(e["mjd"]))

    # 2. Check proper motion & determine grid center at temporal midpoint
    has_pm = False
    coord_ref: SkyCoord | None = None
    target_name = None
    target_key = None
    center_ra: float
    center_dec: float

    all_mjds = [float(e["mjd"]) for e in parsed_entries]
    mjd_mid = (min(all_mjds) + max(all_mjds)) / 2.0

    if target:
        target_key = target.get("target_key") or target.get("id")
        target_name = target.get("name") or target.get("identifier") or (target_key.title() if target_key else "Target")

        if "j2000_deg" in target:
            t_ra, t_dec = float(target["j2000_deg"][0]), float(target["j2000_deg"][1])
            epoch_str = "J2000"
        else:
            t_ra = float(target.get("ra", target.get("ra_deg", 0.0)))
            t_dec = float(target.get("dec", target.get("dec_deg", 0.0)))
            epoch_str = target.get("epoch", "J2000")

        pmra = target.get("pmra", target.get("pm_mas_yr", [0, 0])[0] if "pm_mas_yr" in target else 0.0)
        pmdec = target.get("pmdec", target.get("pm_mas_yr", [0, 0])[1] if "pm_mas_yr" in target else 0.0)
        
        if pmra is not None and pmdec is not None and (abs(pmra) > 0 or abs(pmdec) > 0):
            has_pm = True
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                coord_ref = SkyCoord(
                    t_ra * u.deg,
                    t_dec * u.deg,
                    pm_ra_cosdec=float(pmra) * u.mas / u.yr,
                    pm_dec=float(pmdec) * u.mas / u.yr,
                    obstime=Time(epoch_str),
                )
                # Compute position at midpoint epoch
                star_at_mid = coord_ref.apply_space_motion(new_obstime=Time(mjd_mid, format="mjd"))
                center_ra = float(star_at_mid.ra.deg)
                center_dec = float(star_at_mid.dec.deg)
        else:
            center_ra = t_ra
            center_dec = t_dec
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                coord_ref = SkyCoord(center_ra * u.deg, center_dec * u.deg)
    else:
        # Fallback to cutout coordinates
        with fits.open(parsed_entries[0]["resolved_path"]) as h:
            native_wcs = WCS(h["IMAGE"].header, fobj=h).celestial
            center_ra = float(native_wcs.wcs.crval[0])
            center_dec = float(native_wcs.wcs.crval[1])

    # 3. Create TAN grid WCS with odd dimensions (centered on pixel)
    wcs, shape = tan_grid(center_ra, center_dec, fov_deg, scale=pixscale_arcsec)
    grid_height, grid_width = shape

    # 4. Group cutouts by time clusters (gap > gap_days)
    clusters: list[tuple[int, list[dict[str, Any]]]] = []
    # Check if cluster_id is pre-assigned in metadata
    if all("cluster_id" in e for e in parsed_entries):
        for cid in sorted({e["cluster_id"] for e in parsed_entries}):
            clusters.append((cid, [e for e in parsed_entries if e["cluster_id"] == cid]))
    else:
        current_cluster: list[dict[str, Any]] = []
        cluster_idx = 0
        for entry in parsed_entries:
            if current_cluster and (float(entry["mjd"]) - float(current_cluster[-1]["mjd"]) > gap_days):
                clusters.append((cluster_idx, current_cluster))
                cluster_idx += 1
                current_cluster = []
            current_cluster.append(entry)
        if current_cluster:
            clusters.append((cluster_idx, current_cluster))

    # Output paths setup
    if output_dir is not None:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
    else:
        out_path = ROOT / "data" / "five_targets" / (target_key or "unknown") / "frames"
        out_path.mkdir(parents=True, exist_ok=True)

    if generate_verification:
        verif_path = Path(verification_dir) if verification_dir else (out_path.parent / "verification_crosshairs")
        verif_path.mkdir(parents=True, exist_ok=True)
    else:
        verif_path = None

    # 5. Reproject cutouts and compute median frames
    visit_products = []
    visit_arrays = []
    common_bunit: str | None = None

    for cluster_id, cluster_entries in clusters:
        aligned_images = []
        cluster_mjds = []
        metadata_list = []

        for entry in cluster_entries:
            fpath = entry["resolved_path"]
            img, native, info = load_cutout(fpath, center_ra, center_dec)
            if common_bunit is None:
                common_bunit = info["bunit"]
            aligned, footprint = reproject_interp((img, native), wcs, shape_out=shape)
            aligned_clean = np.where(footprint > 0, aligned, np.nan)
            aligned_images.append(aligned_clean)
            cluster_mjds.append(float(entry["mjd"]))
            metadata_list.append(info)

        cube = np.asarray(aligned_images)
        count_valid = np.isfinite(cube).sum(axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            visit_median = np.nanmedian(cube, axis=0)

        mean_mjd = float(np.mean(cluster_mjds))
        mean_wave = float(np.mean([m["wave_um"] for m in metadata_list]))
        mean_width = float(np.mean([m["bandwidth_um"] for m in metadata_list]))
        bad_frac = float((count_valid == 0).mean())

        # Compute predicted_px if target coordinate available
        pred_px: list[float] | None = None
        pred_fits: tuple[float, float] | None = None
        if coord_ref is not None:
            x_png, y_png = compute_predicted_pixel(coord_ref, mean_mjd, wcs, grid_height)
            pred_px = [round(float(x_png), 2), round(float(y_png), 2)]
            pred_fits = (float(x_png), float(grid_height - 1 - y_png))

        frame_id = f"D{detector}_visit{cluster_id:02}"
        visit_arrays.append(visit_median)
        visit_products.append({
            "id": frame_id,
            "cluster_id": cluster_id,
            "mjd": mean_mjd,
            "iso": Time(mean_mjd, format="mjd").isot + "Z",
            "wavelength_um": round(mean_wave, 4),
            "bandwidth_um": round(mean_width, 4),
            "release": "qr2",
            "survey": cluster_id + 1,
            "bad_pixel_frac": round(bad_frac, 4),
            "predicted_px": pred_px,
            "predicted_fits": pred_fits,
            "n_inputs": len(cluster_entries),
            "inputs": metadata_list,
        })

        # Save FITS product
        hdr = wcs.to_header()
        hdr["BUNIT"] = common_bunit or "MJy / sr"
        hdr["MJD-OBS"] = mean_mjd
        hdr["DETECTOR"] = detector
        fits.HDUList([
            fits.PrimaryHDU(),
            fits.ImageHDU(visit_median.astype("float32"), hdr, name="MEDIAN"),
            fits.ImageHDU(count_valid.astype("int16"), wcs.to_header(), name="NVALID"),
        ]).writeto(out_path / f"{frame_id}.fits", overwrite=True)

    # 6. Compute shared normalization scale across all visit frames
    all_finite = np.concatenate([arr[np.isfinite(arr)] for arr in visit_arrays if np.isfinite(arr).any()])
    if len(all_finite) == 0:
        raise ValueError("No valid finite pixels across any frames")

    vmin = float(np.percentile(all_finite, 2.0))
    vmax = float(np.percentile(all_finite, 99.5))
    if vmin >= vmax:
        vmax = vmin + 1.0

    norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=AsinhStretch())

    # Differences between consecutive visit frames
    diff_arrays = []
    diff_limits = []
    for i in range(1, len(visit_arrays)):
        diff = visit_arrays[i] - visit_arrays[i - 1]
        diff_arrays.append(diff)
        finite_diff = diff[np.isfinite(diff)]
        if len(finite_diff) > 0:
            lim = float(np.percentile(np.abs(finite_diff), 99.0))
            if lim == 0:
                lim = float(np.finfo(float).eps)
        else:
            lim = 1.0
        diff_limits.append(lim)

    # 7. Render standard Frame PNGs and Difference PNGs
    cmap_frame = plt.get_cmap("gray").with_extremes(bad=COLOR_MISSING)
    cmap_diff = plt.get_cmap("RdBu_r").with_extremes(bad=COLOR_MISSING)

    for idx, (prod, arr) in enumerate(zip(visit_products, visit_arrays)):
        frame_id = prod["id"]
        png_path = out_path / f"{frame_id}.png"
        fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
        im = ax.imshow(arr, origin="lower", cmap=cmap_frame, norm=norm)
        ax.set_title(f"{frame_id} / median of {prod['n_inputs']}\nMJD {prod['mjd']:.2f} ({prod['iso'][:10]})")
        fig.colorbar(im, ax=ax, label=common_bunit or "MJy / sr")
        fig.savefig(png_path, dpi=140)
        plt.close(fig)
        prod["png"] = str(png_path.relative_to(ROOT)).replace("\\", "/")

        # Difference PNG
        if idx > 0:
            diff = diff_arrays[idx - 1]
            lim = diff_limits[idx - 1]
            diff_name = f"{frame_id}_minus_{visit_products[idx - 1]['id']}"
            diff_png_path = out_path / f"{diff_name}.png"
            diff_fits_path = out_path / f"{diff_name}.fits"

            fits.PrimaryHDU(diff.astype("float32"), wcs.to_header()).writeto(diff_fits_path, overwrite=True)

            fig, ax = plt.subplots(figsize=(6, 5), constrained_layout=True)
            im_diff = ax.imshow(diff, origin="lower", cmap=cmap_diff, vmin=-lim, vmax=lim)
            ax.set_title(f"{diff_name}\nDipole difference: +red (current) vs -blue (previous)", fontsize=9)
            fig.colorbar(im_diff, ax=ax, label=common_bunit or "MJy / sr")
            fig.savefig(diff_png_path, dpi=140)
            plt.close(fig)
            prod["diff_png"] = str(diff_png_path.relative_to(ROOT)).replace("\\", "/")
        else:
            prod["diff_png"] = ""

    # 8. Render Verification PNGs with Crosshairs (Nghiệm thu dấu thập trên sao)
    verification_images = []
    if generate_verification and verif_path is not None:
        for prod, arr in zip(visit_products, visit_arrays):
            frame_id = prod["id"]
            fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
            ax.imshow(arr, origin="lower", cmap=cmap_frame, norm=norm)

            if prod["predicted_fits"] is not None:
                xf, yf = prod["predicted_fits"]
                px_png = prod["predicted_px"]
                draw_crosshair_on_ax(ax, xf, yf, gap=1.5, arm=3.5, color="red")
                ax.plot(xf, yf, "+", color="yellow", markersize=4, markeredgewidth=0.8)
                ax.set_title(
                    f"Verification: {frame_id} (D{detector})\n"
                    f"Crosshair at predicted_px={px_png} (FITS=[{xf:.2f}, {yf:.2f}])\n"
                    f"MJD={prod['mjd']:.2f} | Obs date: {prod['iso'][:10]}",
                    fontsize=10,
                )
            else:
                ax.set_title(f"Verification: {frame_id} (no prediction)")

            verif_png = verif_path / f"{frame_id}_crosshair.png"
            fig.savefig(verif_png, dpi=150)
            plt.close(fig)
            verification_images.append(verif_png)

        # Generate side-by-side comparison image if >= 2 visits
        if len(visit_arrays) >= 2:
            fig, axes = plt.subplots(1, 2, figsize=(13, 6), constrained_layout=True)
            for i, ax in enumerate(axes[:2]):
                prod = visit_products[i]
                arr = visit_arrays[i]
                ax.imshow(arr, origin="lower", cmap=cmap_frame, norm=norm)
                if prod["predicted_fits"] is not None:
                    xf, yf = prod["predicted_fits"]
                    draw_crosshair_on_ax(ax, xf, yf, gap=1.5, arm=3.5, color="red")
                    # Zoom in on central region to see proper motion clearly
                    ax.set_xlim(xf - 12, xf + 12)
                    ax.set_ylim(yf - 12, yf + 12)
                ax.set_title(
                    f"{prod['id']} ({prod['iso'][:10]})\n"
                    f"predicted_px: {prod['predicted_px']}",
                    fontsize=11,
                )
            fig.suptitle(
                f"Barnard Proper Motion Verification (Detector D{detector})\n"
                f"Star moves northward as crosshair tracks predicted_px across epochs",
                fontsize=13,
                fontweight="bold",
            )
            comparison_path = verif_path / f"barnard_d{detector}_movement_comparison.png"
            fig.savefig(comparison_path, dpi=160)
            plt.close(fig)

            # Generate animated GIF
            try:
                pil_frames = [Image.open(p) for p in verification_images]
                gif_path = verif_path / f"barnard_d{detector}_movement_blink.gif"
                pil_frames[0].save(
                    gif_path,
                    save_all=True,
                    append_images=pil_frames[1:],
                    duration=800,
                    loop=0,
                )
            except Exception as e:
                warnings.warn(f"Could not write verification GIF: {e}")

    # 9. Format response matching API 0.1 Models
    warnings_list: list[str] = []
    if len(visit_products) < 3:
        warnings_list.append("FEW_FRAMES")

    result = {
        "api_version": "0.1",
        "target": {
            "ra": round(center_ra, 6),
            "dec": round(center_dec, 6),
            "name": target_name or (target_key.title() if target_key else "Target"),
            "target_key": target_key,
        },
        "detector": detector,
        "grid": {
            "width": grid_width,
            "height": grid_height,
            "pixscale_arcsec": pixscale_arcsec,
            "projection": "TAN",
            "center_ra": round(center_ra, 6),
            "center_dec": round(center_dec, 6),
        },
        "norm": {
            "vmin": round(vmin, 4),
            "vmax": round(vmax, 4),
            "stretch": "asinh",
        },
        "reference_frame_id": visit_products[0]["id"] if visit_products else None,
        "frames": [
            {
                "id": p["id"],
                "mjd": round(p["mjd"], 4),
                "iso": p["iso"],
                "wavelength_um": p["wavelength_um"],
                "bandwidth_um": p["bandwidth_um"],
                "release": p["release"],
                "survey": p["survey"],
                "bad_pixel_frac": p["bad_pixel_frac"],
                "predicted_px": p["predicted_px"],
                "png": p.get("png", ""),
                "diff_png": p.get("diff_png", ""),
            }
            for p in visit_products
        ],
        "warnings": warnings_list,
    }

    report_path = out_path / f"D{detector}_frames_report.json"
    report_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    return result


if __name__ == "__main__":
    barnard_dir = ROOT / "data" / "five_targets" / "barnard"
    target_info = json.loads((barnard_dir / "target.json").read_text(encoding="utf-8"))
    res = build_frames(
        barnard_dir / "inputs.json",
        target=target_info,
        detector=6,
        output_dir=barnard_dir / "frames",
        generate_verification=True,
    )
    print("Done build_frames() for Barnard D6!")
    print(f"Norm: {res['norm']}")
    for f in res["frames"]:
        print(f"  Frame {f['id']}: MJD={f['mjd']}, predicted_px={f['predicted_px']}")

