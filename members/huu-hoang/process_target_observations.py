"""Download a bounded five-target fixture and render detector/visit frames and RGB."""

import argparse
import hashlib
import io
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor

import astropy.units as u
import matplotlib.pyplot as plt
import numpy as np
import requests
from align_sky_images import FOV, ROOT, load_cutout
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
from astropy.visualization import AsinhStretch, ImageNormalize
from combine_observation_frames import make_frames

BASE = ROOT / "data" / "target_observations"
TARGETS = {
    "barnard": "GJ 699",
    "eps-ind-b": "2MASS J22041052-5646577",
    "wise-0855": "WISE J085510.83-071442.5",
    "rw-aur": "RW Aur",
    "r-dra": "R Dra",
}


def get(url, **kwargs):
    for attempt in range(4):
        try:
            response = requests.get(url, timeout=120, **kwargs)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2**attempt)


def resolve(target, ident):
    folder = BASE / target
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / "simbad.txt"
    if not path.exists() or "Identifier not found" in path.read_text(encoding="utf-8"):
        response = get(
            "https://simbad.cfa.harvard.edu/simbad/sim-id",
            params={"Ident": ident, "output.format": "ASCII"},
        )
        path.write_text(response.text, encoding="utf-8")
    text = path.read_text(encoding="utf-8")
    if target == "eps-ind-b" and not re.search(r"Object \* eps Ind B\s+---\s+BD\*", text):
        raise ValueError("Resolver did not return the Epsilon Indi brown-dwarf pair")
    match = re.search(
        r"Coordinates\(ICRS,ep=J2000,eq=2000\):\s*([0-9. ]+)\s+([+-][0-9. ]+)\s*\(", text
    )
    pm = re.search(r"Proper motions:\s*([+-]?[0-9.]+)\s+([+-]?[0-9.]+)", text)
    if not match or not pm:
        raise ValueError(f"Cannot safely parse J2000 coordinates/PM for {ident}; inspect {path}")
    coord = SkyCoord(
        match[1].strip(),
        match[2].strip(),
        unit=(u.hourangle, u.deg),
        pm_ra_cosdec=float(pm[1]) * u.mas / u.yr,
        pm_dec=float(pm[2]) * u.mas / u.yr,
        obstime=Time("J2000"),
    )
    moved = coord.apply_space_motion(new_obstime=Time("J2026"))
    ra, dec = float(moved.ra.deg), float(moved.dec.deg)
    info = {
        "id": target,
        "identifier": ident,
        "ra_deg": ra,
        "dec_deg": dec,
        "center_epoch": "J2026 fixed grid",
        "source": "https://simbad.cfa.harvard.edu/simbad/sim-id?Ident=" + ident,
        "j2000_deg": [float(coord.ra.deg), float(coord.dec.deg)],
        "pm_mas_yr": [float(pm[1]), float(pm[2])],
        "limits": "Linear space-motion search position; no annual parallax, orbital motion, or radial velocity; not a measured detection.",
    }
    (folder / "target_coordinates.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return info


def acquire_target(info):
    folder = BASE / info["id"]
    ra, dec = info["ra_deg"], info["dec_deg"]
    catalog = folder / ("catalog_j2026.xml" if info["id"] == "wise-0855" else "catalog.xml")
    if not catalog.exists():
        response = get(
            "https://irsa.ipac.caltech.edu/SIA",
            params={"POS": f"CIRCLE {ra} {dec} 0.03", "COLLECTION": "spherex_qr2"},
        )
        catalog.write_bytes(response.content)
    table = Table.read(catalog, use_names_over_ids=True)
    rows = sorted(table, key=lambda r: float(r["t_min"]))
    groups = []
    for row in rows:
        if not groups or float(row["t_min"]) - float(groups[-1][-1]["t_min"]) > 30:
            groups.append([])
        groups[-1].append(row)
    selected = []
    for group_id, group in enumerate(groups):
        for det in (1, 3, 6):
            candidates = [r for r in group if str(r["energy_bandpassname"]) == f"SPHEREx-D{det}"]
            # At most two distinct exposures per detector/visit; deterministic evenly spaced sample.
            if candidates:
                selected.extend(
                    (group_id, candidates[k], float(group[0]["t_min"]), float(group[-1]["t_min"]))
                    for k in sorted({0, len(candidates) - 1})
                )
    if not selected:
        raise ValueError(f"No QR2 observations for {info['id']}")

    def fetch(item):
        group_id, row, start, end = item
        det = str(row["energy_bandpassname"]).split("-")[-1]
        suffix = "_j2026" if info["id"] == "wise-0855" else ""
        path = folder / "fits_cutouts" / f"{row['obs_id']}_{det}{suffix}.fits"
        path.parent.mkdir(parents=True, exist_ok=True)
        url = str(row["access_url"])
        if not path.exists():
            response = get(f"{url}?center={ra},{dec}&size={FOV}")
            with fits.open(io.BytesIO(response.content)) as h:
                h.verify("exception")
                if str(h["IMAGE"].header["OBSID"]) != str(row["obs_id"]):
                    raise ValueError("Unexpected observation")
            path.write_bytes(response.content)
        return {
            "path": str(path.relative_to(ROOT)),
            "url": url,
            "obs_id": str(row["obs_id"]),
            "detector": det,
            "mjd": float(row["t_min"]),
            "cluster_id": group_id,
            "cluster_start_mjd": start,
            "cluster_end_mjd": end,
            "cutout_center": [ra, dec],
            "cutout_size_deg": FOV,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        }

    with ThreadPoolExecutor(max_workers=4) as pool:
        entries = list(pool.map(fetch, selected))
    (folder / "observation_manifest.json").write_text(
        json.dumps(entries, indent=2), encoding="utf-8"
    )
    (folder / "observation_time_groups.json").write_text(
        json.dumps(
            {
                "gap_days": 30,
                "groups": [
                    {
                        "start_mjd": float(g[0]["t_min"]),
                        "end_mjd": float(g[-1]["t_min"]),
                        "catalog_rows": len(g),
                    }
                    for g in groups
                ],
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"{info['id']}: {len(entries)} cutouts", flush=True)


def render(info):
    folder = BASE / info["id"]
    # Remove only named products owned by this renderer, to avoid stale visit labels.
    for pattern in (
        "detector_[136]_visit_*.fits",
        "detector_[136]_visit_*.png",
        "false_color_visit_*.png",
    ):
        for path in (folder / "combined_frames").glob(pattern):
            path.unlink()
    reports = {}
    for det in (1, 3, 6):
        reports[det] = make_frames(
            info["ra_deg"],
            info["dec_deg"],
            FOV,
            det,
            manifest=folder / "observation_manifest.json",
            output=folder / "combined_frames",
        )
    # One global scale per RGB channel across visits, preserving changes between frames.
    visits = sorted(
        set.intersection(*[{f["cluster_id"] for f in r["frames"]} for r in reports.values()])
    )
    rgb_report = []
    for visit in visits:
        channels, valid = [], None
        for det in (6, 3, 1):  # red -> long wavelength, blue -> short wavelength
            path = folder / "combined_frames" / f"detector_{det}_visit_{visit:02}.fits"
            with fits.open(path) as h:
                data = h["MEDIAN"].data.astype(float)
            good = np.isfinite(data)
            valid = good if valid is None else valid & good
            scale = reports[det]["display"]
            span = scale["vmax"] - scale["vmin"]
            channel = np.clip((data - scale["vmin"]) / (span if span > 0 else 1), 0, 1)
            channels.append(AsinhStretch()(np.nan_to_num(channel)))
        rgb = np.stack(channels, axis=-1)
        rgb[~valid] = [0.44, 0.19, 0.56]
        fig, ax = plt.subplots(figsize=(6, 6), constrained_layout=True)
        ax.imshow(rgb, origin="lower")
        ax.set_title(f"{info['id']} / visit {visit}\nFalse color R=D6 G=D3 B=D1")
        fig.savefig(folder / "combined_frames" / f"false_color_visit_{visit:02}.png", dpi=150)
        plt.close(fig)
        rgb_report.append({"visit": visit, "valid_fraction": float(valid.mean())})
    (folder / "false_color_report.json").write_text(
        json.dumps(
            {
                "mapping": {"R": 6, "G": 3, "B": 1},
                "visits": rgb_report,
                "limits": "Non-simultaneous, broad detector medians; false color only. Purple=missing/masked channel.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(
        f"{info['id']}: rendered {sum(len(r['frames']) for r in reports.values())} frames, {len(visits)} RGB",
        flush=True,
    )
    if info["id"] in {"barnard", "r-dra"}:
        saturation_evidence(info)


def saturation_evidence(info):
    """Show native flags before interpolation; never infer saturation from brightness."""
    folder = BASE / info["id"]
    entries = json.loads((folder / "observation_manifest.json").read_text(encoding="utf-8"))
    records = []
    for entry in entries:
        with fits.open(ROOT / entry["path"]) as h:
            fh, flags = h["FLAGS"].header, h["FLAGS"].data
            keys = [
                k
                for k in fh
                if k.startswith("MP_")
                and any(word in k for word in ("OVERFLOW", "NONLINEAR", "SATUR"))
            ]
            bits = sum(1 << bit for bit in {int(fh[k]) for k in keys})
            affected = (flags & bits) != 0
            records.append(
                {
                    "path": entry["path"],
                    "detector": entry["detector"],
                    "obs_id": entry["obs_id"],
                    "flags": keys,
                    "affected_pixels": int(affected.sum()),
                }
            )
    worst = max(records, key=lambda r: r["affected_pixels"])
    masked, _wcs, _meta = load_cutout(ROOT / worst["path"], info["ra_deg"], info["dec_deg"])
    with fits.open(ROOT / worst["path"]) as h:
        raw = h["IMAGE"].data.astype(float)
        flags, fh = h["FLAGS"].data, h["FLAGS"].header
        bits = sum(1 << bit for bit in {int(fh[k]) for k in worst["flags"]})
        affected = (flags & bits) != 0
    assert np.isnan(masked[affected]).all()
    lo, hi = np.percentile(raw[np.isfinite(raw)], [2, 99.5])
    norm = ImageNormalize(vmin=lo, vmax=hi, stretch=AsinhStretch())
    fig, axes = plt.subplots(1, 3, figsize=(14, 5), constrained_layout=True)
    cmap = plt.get_cmap("gray").with_extremes(bad="#703090")
    for ax, data, title in zip(
        axes,
        (raw, affected, masked),
        ("Native IMAGE", "OVERFLOW / NONLINEAR flags", "All selected bad flags masked"),
    ):
        ax.imshow(
            data,
            origin="lower",
            cmap="magma" if data.dtype == bool else cmap,
            norm=None if data.dtype == bool else norm,
            interpolation="nearest",
        )
        ax.set_title(title)
    fig.suptitle(f"{info['id']} / {worst['detector']} / {worst['obs_id']}")
    fig.savefig(folder / "saturation_flag_check.png", dpi=150)
    plt.close(fig)
    (folder / "saturation_report.json").write_text(
        json.dumps(
            {
                "inputs": records,
                "shown_input": worst,
                "masked_flagged_pixels_check": "pass",
                "limits": "Counts cover the cutout, not an identified target aperture. Masking excludes unreliable pixels and cannot recover saturated flux.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--target", choices=list(TARGETS))
    args = parser.parse_args()
    for target, ident in TARGETS.items():
        if args.target and args.target != target:
            continue
        if args.download:
            info = resolve(target, ident)
            acquire_target(info)
        else:
            info = json.loads(
                (BASE / target / "target_coordinates.json").read_text(encoding="utf-8")
            )
        render(info)
