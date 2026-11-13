"""Reproject two real SPHEREx cutouts around WISE 0855 onto the 2025 grid.

Run from any directory: python members/huu-hoang/reproject_demo.py --download
Subsequent offline runs omit --download. Products stay in gitignored data/.
"""

import argparse
import contextlib
import hashlib
import importlib.metadata
import io
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import requests
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
from astropy.visualization import AsinhStretch, ImageNormalize
from astropy.wcs import WCS
from PIL import Image
import sys

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[2]))
from shared.image_processing import reproject_compatible as reproject_interp

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "reproject_wise0855"
# Search/cutout center from scripts/check_env.py, not an epoch-corrected star position.
RA, DEC, SIZE = 133.7951, -7.2451, 0.1
OBS_IDS = {2025: "2025W19_1B_0116_1", 2026: "2026W17_1B_0634_1"}


def validate_inputs():
    """Fail clearly when fixtures are missing, mixed up, or changed."""
    required = [OUT / "inputs.json"] + [OUT / f"wise0855_{year}.fits" for year in OBS_IDS]
    missing = [path.name for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            f"Missing {', '.join(missing)}. Run reproject_demo.py --download first."
        )
    manifest = json.loads((OUT / "inputs.json").read_text(encoding="utf-8"))
    for year, obs_id in OBS_IDS.items():
        entries = [entry for entry in manifest if entry["year"] == year]
        if len(entries) != 1:
            raise ValueError(f"Expected one manifest entry for {year}")
        path = OUT / f"wise0855_{year}.fits"
        if hashlib.sha256(path.read_bytes()).hexdigest() != entries[0]["sha256"]:
            raise ValueError(f"Input checksum mismatch: {path.name}")
        with fits.open(path) as hdul:
            header = hdul["IMAGE"].header
            if header["OBSID"] != obs_id or int(header["DETECTOR"]) != 6:
                raise ValueError(f"Unexpected OBSID or detector: {path.name}")
            if Time(header["DATE-OBS"]).to_datetime().year != year:
                raise ValueError(f"Wrong observation year: {path.name}")
    print("Input SHA-256, OBSID, detector and FITS observation years: PASS")


def export_result_previews(reference, aligned, footprint, valid, norm, unit):
    for filename, data, title in [
        ("wise0855_2025_reference.png", reference, "2025 reference / masked"),
        ("wise0855_2026_aligned.png", aligned, "2026 reprojected onto 2025 WCS"),
        ("footprint_2026.png", footprint, "2026 valid footprint / yellow = valid"),
        ("common_valid.png", valid.astype(float), "Both years valid / yellow = valid"),
    ]:
        is_mask = filename in {"footprint_2026.png", "common_valid.png"}
        fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
        if is_mask:
            im = ax.imshow(
                data, origin="lower", cmap="viridis", vmin=0, vmax=1, interpolation="nearest"
            )
        else:
            cmap = plt.get_cmap("gray").copy()
            cmap.set_bad("#703090")
            im = ax.imshow(data, origin="lower", cmap=cmap, norm=norm, interpolation="nearest")
        ax.set_title(title)
        ax.set_xlabel("x pixel (zero based)")
        ax.set_ylabel("y pixel")
        fig.colorbar(im, ax=ax, label="valid = 1 / invalid = 0" if is_mask else unit)
        fig.savefig(OUT / filename, dpi=160)
        plt.close(fig)


def download():
    response = requests.get(
        "https://irsa.ipac.caltech.edu/SIA",
        params={"POS": f"CIRCLE {RA} {DEC} 0.03", "COLLECTION": "spherex_qr2"},
        timeout=180,
    )
    response.raise_for_status()
    catalog = OUT / "sia_qr2.xml"
    catalog.write_bytes(response.content)
    table = Table.read(catalog, use_names_over_ids=True)
    table.write(OUT / "catalog.ecsv", overwrite=True)
    manifest = []
    for year, obs_id in OBS_IDS.items():
        rows = table[(table["obs_id"] == obs_id) & (table["energy_bandpassname"] == "SPHEREx-D6")]
        if len(rows) != 1:
            raise ValueError(f"Expected one D6 image for {obs_id}; found {len(rows)}")
        row = rows[0]
        observed = Time(float(row["t_min"]), format="mjd")
        if observed.to_datetime().year != year:
            raise ValueError(f"Wrong observation year: {observed.iso}")
        url = f"{row['access_url']}?center={RA},{DEC}&size={SIZE}"
        path = OUT / f"wise0855_{year}.fits"
        response = requests.get(url, timeout=180)
        response.raise_for_status()
        with fits.open(io.BytesIO(response.content)) as hdul:
            hdul.verify("exception")
        path.write_bytes(response.content)
        manifest.append(
            {
                "year": year,
                "obs_id": obs_id,
                "date_utc": observed.isot,
                "mjd": float(row["t_min"]),
                "detector": "D6",
                "url": url,
                "bytes": path.stat().st_size,
                "sha256": hashlib.sha256(response.content).hexdigest(),
            }
        )
        print(f"Downloaded {path.name}: {observed.isot}", flush=True)
    (OUT / "inputs.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def load(year):
    with fits.open(OUT / f"wise0855_{year}.fits") as hdul:
        print(year, [(h.name, h.data.shape if h.data is not None else None) for h in hdul])
        image = hdul["IMAGE"].data.astype(float)
        header = hdul["IMAGE"].header.copy()
        wcs = WCS(header, fobj=hdul).celestial
        flags = hdul["FLAGS"].data
        flag_header = hdul["FLAGS"].header
        # SOURCE and FULLSAMPLE are informational: keep the astronomical sources!
        rejected = [
            key
            for key in flag_header
            if key.startswith("MP_") and key not in {"MP_SOURCE", "MP_FULLSAMPLE"}
        ]
        bad_bits = sum(1 << int(flag_header[key]) for key in rejected)
        good = np.isfinite(image) & ((flags & bad_bits) == 0)
        image[~good] = np.nan
        details = {
            "shape": list(image.shape),
            "bunit": header.get("BUNIT"),
            "date_obs": header.get("DATE-OBS", hdul[0].header.get("DATE-OBS")),
            "good_pixels": int(good.sum()),
            "hdu_names": [h.name for h in hdul],
            "rejected_flags": rejected,
            "bad_bits": bad_bits,
        }
        # The spectral lookup uses detector pixels; exclude celestial SIP coefficients.
        spectral_header = header.copy()
        for key in list(spectral_header):
            if key.startswith(("A_", "B_", "AP_", "BP_")):
                del spectral_header[key]
        wave_wcs = WCS(spectral_header, fobj=hdul, key="W")
        gx, gy = wcs.world_to_pixel(SkyCoord(RA, DEC, unit="deg"))
        wave, bandwidth = wave_wcs.pixel_to_world_values(gx, gy)
        details["wavelength_at_search_center_um"] = float(wave)
        details["bandwidth_at_search_center_um"] = float(bandwidth)
        return image, wcs, header, details


def export_original_previews():
    """Render the downloaded IMAGE values before any masking or reprojection."""
    for year in OBS_IDS:
        with fits.open(OUT / f"wise0855_{year}.fits") as hdul:
            raw = hdul["IMAGE"].data.astype(float)
            header = hdul["IMAGE"].header
            vmin, vmax = np.percentile(raw[np.isfinite(raw)], [2, 99.5])
            norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=AsinhStretch())
            fig, ax = plt.subplots(figsize=(7, 6), constrained_layout=True)
            im = ax.imshow(raw, origin="lower", cmap="gray", norm=norm, interpolation="nearest")
            ax.set_title(
                f"SPHEREx D6 / {year} original IMAGE\n"
                "Before mask and reproject; individual display stretch"
            )
            ax.set_xlabel("x pixel (zero based)")
            ax.set_ylabel("y pixel")
            fig.colorbar(im, ax=ax, label=header.get("BUNIT", ""))
            fig.savefig(OUT / f"wise0855_{year}_original.png", dpi=160)
            plt.close(fig)


def export_blink(reference, aligned, valid, norm, unit):
    """Blink only common valid pixels, with identical geometry and display scale."""
    frames = []
    cmap = plt.get_cmap("gray").copy()
    cmap.set_bad("#703090")
    for year, data in [(2025, reference), (2026, aligned)]:
        fig, ax = plt.subplots(figsize=(7, 7), dpi=120)
        fig.subplots_adjust(left=0.12, right=0.84, bottom=0.15, top=0.86)
        im = ax.imshow(
            np.where(valid, data, np.nan),
            origin="lower",
            cmap=cmap,
            norm=norm,
            interpolation="nearest",
        )
        ax.set_title(f"WISE 0855 field / {year}\nSame 2025 WCS grid / common valid pixels")
        ax.set_xlabel("x pixel (zero based)")
        ax.set_ylabel("y pixel")
        fig.colorbar(im, cax=fig.add_axes([0.87, 0.2, 0.025, 0.55]), label=unit)
        fig.text(
            0.5,
            0.045,
            "Different wavelengths; brightness changes are not variability evidence.",
            ha="center",
            fontsize=9,
        )
        fig.text(
            0.5,
            0.02,
            "Purple = excluded / missing data; no confirmed brown dwarf detection.",
            ha="center",
            fontsize=9,
        )
        fig.canvas.draw()
        frames.append(Image.fromarray(np.asarray(fig.canvas.buffer_rgba()).copy()).convert("RGB"))
        plt.close(fig)
    frames[0].save(
        OUT / "blink_aligned.gif",
        save_all=True,
        append_images=frames[1:],
        duration=900,
        loop=0,
        disposal=2,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.download:
        download()
    validate_inputs()
    export_original_previews()
    a, wa, _ha, da = load(2025)
    b, wb, _hb, db = load(2026)
    if not da["bunit"] or da["bunit"] != db["bunit"]:
        raise ValueError("Missing or inconsistent surface-brightness units")
    aligned, footprint = reproject_interp((b, wb), wa, shape_out=a.shape, order="bilinear")
    valid = np.isfinite(a) & np.isfinite(aligned) & (footprint > 0)
    if valid.sum() == 0:
        raise ValueError("No valid common pixels")
    # Verify geometry with independent sky points, and interpolation with constants/self-map.
    yy, xx = np.mgrid[3 : a.shape[0] - 3 : 8, 3 : a.shape[1] - 3 : 8]
    sky = wa.pixel_to_world(xx, yy)
    bx, by = wb.world_to_pixel(sky)
    roundtrip_sky = wb.pixel_to_world(bx, by)
    err_arcsec = sky.separation(roundtrip_sky).arcsec
    constant, cf = reproject_interp((np.ones_like(b), wb), wa, shape_out=a.shape)
    self_map, _sf = reproject_interp((a, wa), wa, shape_out=a.shape)
    constant_error = float(np.nanmax(np.abs(constant[cf > 0] - 1)))
    self_error = float(np.nanmax(np.abs(self_map - a)))
    print("Checks:", float(np.max(err_arcsec)), constant_error, self_error, flush=True)
    assert np.max(err_arcsec) < 1e-4
    assert constant_error < 1e-10
    finite_both = np.isfinite(self_map) & np.isfinite(a)
    assert finite_both.sum() > 0
    assert np.allclose(self_map[finite_both], a[finite_both], atol=1e-5)
    header = wa.to_header(relax=True)
    header["BUNIT"] = da["bunit"]
    header["HISTORY"] = "2026 IMAGE -> 2025 celestial WCS; bilinear; bad flag bits masked"
    fits.HDUList(
        [
            fits.PrimaryHDU(),
            fits.ImageHDU(a.astype("float32"), header=header, name="REFERENCE2025"),
            fits.ImageHDU(aligned.astype("float32"), header=header, name="ALIGNED2026"),
            fits.ImageHDU(
                footprint.astype("float32"), header=wa.to_header(relax=True), name="FOOTPRINT"
            ),
            fits.ImageHDU(
                valid.astype("uint8"), header=wa.to_header(relax=True), name="COMMONVALID"
            ),
        ]
    ).writeto(OUT / "reprojected.fits", overwrite=True)
    with fits.open(OUT / "reprojected.fits") as saved:
        for name in ["REFERENCE2025", "ALIGNED2026", "FOOTPRINT", "COMMONVALID"]:
            restored = WCS(saved[name].header).celestial
            assert np.max(sky.separation(restored.pixel_to_world(xx, yy)).arcsec) < 1e-6
    values = np.concatenate([a[np.isfinite(a)], aligned[np.isfinite(aligned)]])
    vmin, vmax = np.percentile(values, [2, 99.5])
    norm = ImageNormalize(vmin=vmin, vmax=vmax, stretch=AsinhStretch())
    export_result_previews(a, aligned, footprint, valid, norm, da["bunit"])
    export_blink(a, aligned, valid, norm, da["bunit"])
    fig, axes = plt.subplots(1, 4, figsize=(18, 5), constrained_layout=True)
    for ax, data, title in zip(
        axes,
        [a, b, aligned, footprint],
        [
            "2025 masked (reference)",
            "2026 masked (before reproject)",
            "2026 on 2025 grid (after)",
            "2026 valid footprint",
        ],
    ):
        im = (
            ax.imshow(data, origin="lower", cmap="gray", norm=norm)
            if ax != axes[3]
            else ax.imshow(data, origin="lower", vmin=0, vmax=1, cmap="viridis")
        )
        ax.set_title(title)
        ax.set_xlabel("x pixel (zero based)")
        ax.set_ylabel("y pixel")
    # Same fixed sky coordinate in all panels: an alignment guide, not a star detection.
    guide = SkyCoord(RA, DEC, unit="deg")
    for ax, wcs in zip(axes[:3], [wa, wb, wa]):
        gx, gy = wcs.world_to_pixel(guide)
        ax.plot(gx, gy, "+", color="red", markersize=12)
    fig.colorbar(axes[0].images[0], ax=list(axes[:3]), label=da["bunit"], shrink=0.65)
    fig.colorbar(im, ax=axes[3], shrink=0.65)
    fig.suptitle("WISE 0855 field / SPHEREx D6 | + = fixed search coordinate, not detection")
    fig.savefig(OUT / "comparison.png", dpi=160)
    plt.close(fig)
    report = {
        "inputs": json.loads((OUT / "inputs.json").read_text(encoding="utf-8")),
        "image2025": da,
        "image2026": db,
        "output_shape": list(aligned.shape),
        "common_pixels": int(valid.sum()),
        "common_fraction": float(valid.mean()),
        "footprint_fraction": float((footprint > 0).mean()),
        "search_center_pixel_2025": list(map(float, wa.world_to_pixel(guide))),
        "search_center_pixel_2026_native": list(map(float, wb.world_to_pixel(guide))),
        "wcs_roundtrip_max_arcsec": float(np.max(err_arcsec)),
        "constant_max_error": constant_error,
        "self_reproject_max_error": self_error,
        "versions": {
            p: importlib.metadata.version(p)
            for p in ["numpy", "astropy", "reproject", "matplotlib", "requests"]
        },
    }
    report["display"] = {"stretch": "asinh", "vmin": float(vmin), "vmax": float(vmax)}
    report["interpretation"] = {
        "purpose": "Spatial reprojection demonstration around WISE 0855",
        "brown_dwarf_detection_confirmed": False,
        "matched_wavelengths": False,
        "input_validation": "SHA256, OBSID, detector and FITS observation year passed",
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    captured = io.StringIO()
    try:
        with contextlib.redirect_stdout(captured):
            main()
    finally:
        (OUT / "run.log").write_text(captured.getvalue(), encoding="utf-8")
        print(captured.getvalue(), end="")
