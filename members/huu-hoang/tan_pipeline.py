"""Reproducible TAN reprojection of real IRSA cutouts; products are local only."""

import argparse
import hashlib
import io
import json
import platform
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import requests
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy.visualization import AsinhStretch, ImageNormalize
from astropy.wcs import WCS
from reproject import reproject_interp
from scipy.ndimage import maximum_filter

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data" / "tan_wise0855"
RA, DEC, FOV, SCALE = 133.7951, -7.2451, 0.1, 6.2


def tan_grid(ra, dec, fov, scale=SCALE):
    """North up, east left; odd shape puts the requested center on a pixel."""
    if not (0 <= ra < 360 and -90 <= dec <= 90 and 0 < fov <= 2 and scale > 0):
        raise ValueError("Invalid sky center, FOV in degrees, or scale in arcsec/pixel")
    n = int(np.ceil(fov * 3600 / scale))
    n += n % 2 == 0
    w = WCS(naxis=2)
    w.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    w.wcs.crval = [ra, dec]
    w.wcs.crpix = [(n + 1) / 2, (n + 1) / 2]
    w.wcs.cdelt = [-scale / 3600, scale / 3600]
    w.wcs.radesys = "ICRS"
    return w, (n, n)


def load_cutout(path, ra=RA, dec=DEC):
    with fits.open(path) as h:
        header = h["IMAGE"].header
        raw = h["IMAGE"].data.astype(float)
        wcs = WCS(header, fobj=h).celestial
        flags = h["FLAGS"].data
        fh = h["FLAGS"].header
        rejected = {
            k: int(fh[k])
            for k in fh
            if k.startswith("MP_") and k not in {"MP_SOURCE", "MP_FULLSAMPLE"}
        }
        bits = sum(1 << bit for bit in set(rejected.values()))
        flagged = (flags & bits) != 0
        good = np.isfinite(raw) & ~flagged
        spectral = header.copy()
        for k in list(spectral):
            if k.startswith(("A_", "B_", "AP_", "BP_")):
                del spectral[k]
        x, y = wcs.world_to_pixel(SkyCoord(ra, dec, unit="deg"))
        wave, width = WCS(spectral, fobj=h, key="W").pixel_to_world_values(x, y)
        info = {
            "obs_id": header["OBSID"],
            "detector": int(header["DETECTOR"]),
            "date_obs": header["DATE-OBS"],
            "bunit": header.get("BUNIT"),
            "wave_um": float(wave),
            "bandwidth_um": float(width),
            "rejected_flags": rejected,
            "valid_pixels": int(good.sum()),
            "bad_pixel_frac": float(flagged.mean()),
            "flag_counts": {
                k: int(((flags & (1 << int(fh[k]))) != 0).sum()) for k in fh if k.startswith("MP_")
            },
        }
        return np.where(good, raw, np.nan), wcs, info


def acquire(limit=50):
    """Use distinct observations, D3 first to get enough stars for centroids."""
    OUT.mkdir(parents=True, exist_ok=True)
    catalog = Table.read(ROOT / "data/reproject_wise0855/catalog.ecsv")
    rows = sorted(
        catalog,
        key=lambda r: (
            str(r["energy_bandpassname"]) != "SPHEREx-D3",
            str(r["energy_bandpassname"]) != "SPHEREx-D6",
            float(r["t_min"]),
            str(r["obs_id"]),
        ),
    )[:limit]

    def fetch(row):
        det = str(row["energy_bandpassname"]).split("-")[-1]
        name = f"{row['obs_id']}_{det}.fits"
        path = OUT / "inputs" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        url = str(row["access_url"])
        if not path.exists():
            for attempt in range(4):
                response = requests.get(f"{url}?center={RA},{DEC}&size={FOV}", timeout=180)
                if response.status_code not in {429, 500, 502, 503, 504} or attempt == 3:
                    response.raise_for_status()
                    break
                time.sleep(2**attempt)
            with fits.open(io.BytesIO(response.content)) as hdul:
                hdul.verify("exception")
            path.write_bytes(response.content)
        with fits.open(path) as hdul:
            hdr = hdul["IMAGE"].header
            if hdr["OBSID"] != str(row["obs_id"]) or int(hdr["DETECTOR"]) != int(det[1:]):
                raise ValueError(f"Identity mismatch: {name}")
        return {
            "path": str(path.relative_to(ROOT)),
            "url": url,
            "cutout_center": [RA, DEC],
            "cutout_size_deg": FOV,
            "obs_id": str(row["obs_id"]),
            "detector": det,
            "mjd": float(row["t_min"]),
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        entries = list(pool.map(fetch, rows))
    (OUT / "inputs.json").write_text(json.dumps(entries, indent=2), encoding="utf-8")
    print(f"Validated {len(entries)} distinct cutouts", flush=True)
    return entries


def centroids(image):
    """Independent local maxima and positive background-subtracted 5x5 centroids."""
    finite = np.isfinite(image)
    if finite.sum() < 25:
        return np.empty((0, 2))
    bg = np.nanmedian(image)
    noise = 1.4826 * np.nanmedian(np.abs(image - bg))
    work = np.where(finite, image, -np.inf)
    yy, xx = np.where((work == maximum_filter(work, size=7)) & (work > bg + 7 * noise))
    result = []
    for y, x in zip(yy, xx):
        if min(x, y, image.shape[1] - 1 - x, image.shape[0] - 1 - y) < 4:
            continue
        patch = image[y - 2 : y + 3, x - 2 : x + 3]
        if not np.isfinite(patch).all():
            continue
        weights = np.maximum(
            patch
            - np.median(
                image[y - 4 : y + 5, x - 4 : x + 5][
                    np.isfinite(image[y - 4 : y + 5, x - 4 : x + 5])
                ]
            ),
            0,
        )
        py, px = np.mgrid[y - 2 : y + 3, x - 2 : x + 3]
        if weights.sum() > 0:
            result.append(
                [
                    float((px * weights).sum() / weights.sum()),
                    float((py * weights).sum() / weights.sum()),
                ]
            )
    return np.array(result).reshape(-1, 2)


def match_sources(pa, pb, shape):
    matches = []
    for index, p in enumerate(pa):
        if len(pb) == 0:
            continue
        distances = np.linalg.norm(pb - p, axis=1)
        k = int(np.argmin(distances))
        q = pb[k]
        if (
            distances[k] < 2
            and int(np.argmin(np.linalg.norm(pa - q, axis=1))) == index
            and np.linalg.norm(p - (np.array(shape[::-1]) - 1) / 2) > 5
        ):
            matches.append(
                {"a_xy": p.tolist(), "b_xy": q.tolist(), "shift_pix": float(distances[k])}
            )
    return matches


def run(download=False):
    OUT.mkdir(parents=True, exist_ok=True)
    entries = acquire() if download else json.loads((OUT / "inputs.json").read_text())
    loaded = []
    for entry in entries:
        path = ROOT / entry["path"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Checksum mismatch: {path}")
        loaded.append(load_cutout(path))
    wcs, shape = tan_grid(RA, DEC, FOV)
    center = SkyCoord(RA, DEC, unit="deg")
    np.testing.assert_allclose(wcs.world_to_pixel(center), (29, 29), atol=1e-8)
    yy, xx = np.mgrid[5 : shape[0] - 5 : 7, 5 : shape[1] - 5 : 7]
    sky = wcs.pixel_to_world(xx, yy)
    rx, ry = wcs.world_to_pixel(sky)
    roundtrip = float(np.max(np.hypot(rx - xx, ry - yy)))
    assert roundtrip < 1e-6
    constant, fp = reproject_interp(
        (np.ones_like(loaded[0][0]), loaded[0][1]), wcs, shape_out=shape
    )
    constant_error = float(np.max(np.abs(constant[fp > 0] - 1)))
    assert constant_error < 1e-10
    timings = {}
    for count in (10, 50):
        if len(loaded) < count:
            raise ValueError(f"Need {count} distinct cutouts for benchmark")
        samples = []
        reproject_interp(loaded[0][:2], wcs, shape_out=shape)
        for _ in range(3):
            start = time.perf_counter()
            for image, native, _info in loaded[:count]:
                reproject_interp((image, native), wcs, shape_out=shape, order="bilinear")
            samples.append(time.perf_counter() - start)
        timings[str(count)] = {
            "seconds": samples,
            "median_seconds": float(np.median(samples)),
            "scope": "reproject only; resident arrays; sequential; one warmup",
        }
    aligned, metadata = [], []
    for image, native, info in loaded:
        frame, footprint = reproject_interp((image, native), wcs, shape_out=shape)
        aligned.append(np.where(footprint > 0, frame, np.nan))
        metadata.append(info)
    # Compare the closest-wavelength pair in different seasons in D3.
    candidates = [
        (abs(a["wave_um"] - b["wave_um"]), i, j)
        for i, a in enumerate(metadata)
        for j, b in enumerate(metadata[:i])
        if a["detector"] == b["detector"] == 3 and abs(entries[i]["mjd"] - entries[j]["mjd"]) > 100
    ]
    if not candidates:
        raise ValueError("No cross-season D3 comparison")
    _, i, j = min(candidates)
    pa, pb = centroids(aligned[j]), centroids(aligned[i])
    matches = match_sources(pa, pb, shape)
    series = []
    for k, frame in enumerate(aligned):
        if metadata[k]["detector"] != metadata[j]["detector"] or k == j:
            continue
        found = match_sources(pa, centroids(frame), shape)
        median = float(np.median([m["shift_pix"] for m in found])) if found else None
        series.append(
            {
                "index": k,
                "date_obs": metadata[k]["date_obs"],
                "n_matches": len(found),
                "median_shift_pix": median,
                "status": "insufficient_sources"
                if len(found) < 3
                else ("pass" if median < 0.5 else "fail"),
                "wave_offset_um": metadata[k]["wave_um"] - metadata[j]["wave_um"],
            }
        )
    status = "insufficient_sources"
    if len(matches) >= 3:
        status = "pass" if np.median([m["shift_pix"] for m in matches]) < 0.5 else "fail"
    common = np.isfinite(aligned[i]) & np.isfinite(aligned[j])
    values = np.concatenate([aligned[k][common] for k in (j, i)])
    lo, hi = np.percentile(values, [2, 99.5])
    norm = ImageNormalize(vmin=lo, vmax=hi, stretch=AsinhStretch())
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), constrained_layout=True)
    for ax, k in zip(axes[:2], (j, i)):
        ax.imshow(np.where(common, aligned[k], np.nan), origin="lower", cmap="gray", norm=norm)
        ax.set_title(metadata[k]["date_obs"][:10] + f" / {metadata[k]['wave_um']:.4f} um")
        for index, m in enumerate(matches):
            x, y = m["a_xy"]
            ax.plot(x, y, "ro", fillstyle="none", markersize=10)
            ax.text(x + 1, y + 1, str(index + 1), color="red")
    for m in matches:
        p, q = np.array(m["a_xy"]), np.array(m["b_xy"])
        axes[2].plot(*p, "ko")
        axes[2].arrow(*p, *((q - p) * 10), width=0.05, color="red")
    axes[2].set(xlim=(0, shape[1]), ylim=(0, shape[0]), title="Centroid shifts (arrows x10)")
    fig.savefig(OUT / "alignment_evidence.png", dpi=150)
    plt.close(fig)
    hdus = [fits.PrimaryHDU()]
    for k in (j, i):
        header = wcs.to_header()
        header["BUNIT"] = metadata[k]["bunit"]
        header["DATE-OBS"] = metadata[k]["date_obs"]
        header["OBSID"] = metadata[k]["obs_id"]
        hdus.append(fits.ImageHDU(aligned[k].astype("float32"), header=header, name=f"FRAME{k}"))
    fits.HDUList(hdus).writeto(OUT / "tan_pair.fits", overwrite=True)
    with fits.open(OUT / "tan_pair.fits") as saved:
        for hdu in saved[1:]:
            restored = WCS(hdu.header)
            assert np.max(sky.separation(restored.pixel_to_world(xx, yy)).arcsec) < 1e-6
    report = {
        "checks": {
            "roundtrip_max_pix": roundtrip,
            "constant_max_error": constant_error,
            "saved_wcs_roundtrip": "pass",
        },
        "machine": {"platform": platform.platform(), "python": platform.python_version()},
        "grid": {
            "ra_deg": RA,
            "dec_deg": DEC,
            "fov_deg": FOV,
            "scale_arcsec": SCALE,
            "shape": shape,
            "center_xy": list(map(float, wcs.world_to_pixel(SkyCoord(RA, DEC, unit="deg")))),
        },
        "benchmark": timings,
        "metadata": metadata,
        "alignment": {
            "status": status,
            "pair_indices": [j, i],
            "matches": matches,
            "all_D3_against_reference": series,
            "median_shift_pix": float(np.median([m["shift_pix"] for m in matches]))
            if matches
            else None,
            "max_shift_pix": max((m["shift_pix"] for m in matches), default=None),
            "criterion": ">=3 mutual matches within 2px; median shift <0.5px",
            "limits": "Image-source consistency only; not external absolute astrometry; false associations possible.",
        },
    }
    (OUT / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(
        json.dumps({"benchmark": timings, "alignment": report["alignment"]}, indent=2), flush=True
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    run(parser.parse_args().download)
