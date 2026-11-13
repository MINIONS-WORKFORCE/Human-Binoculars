"""Find local SPHEREx cutouts and cache the products of rendering them."""

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from shared.pipeline.irsa import find_frames, group_images_into_visits

from ..api_models import Frames, FramesQuery, PhotometryQuery, Target
from .catalog import position_at, targets
from .frame_rendering import PIXEL_SCALE, build_frames

ROOT = Path(__file__).resolve().parents[4]
RENDER_VERSION = "api-0.1-tan-median-v3"
FIVE_TARGETS_FOLDERS = {
    "barnard": "barnard",
    "wise0855": "wise-0855",
    "epsindib": "eps-ind-b",
    "rwaur": "rw-aur",
    "rdra": "r-dra",
}


@dataclass(frozen=True)
class Cutout:
    path: Path
    obs_id: str
    detector: int
    mjd: float
    release: str
    sha256: str
    size_bytes: int
    modified_ns: int


def pack_entries(data_dir, query):
    """Adapt the earlier notebook pack using its SIA2 index and cutout paths."""
    pack = data_dir / "fixture_pack_v1"
    if not (pack / "metadata.csv").is_file() or not (pack / "rendered/frames.json").is_file():
        return []
    with (pack / "metadata.csv").open(encoding="utf-8-sig", newline="") as handle:
        rows = {urlsplit(row["cutout_url"]).path: row for row in csv.DictReader(handle)}
    index = json.loads((pack / "rendered/frames.json").read_text(encoding="utf-8"))
    keys = {"Barnards_Star": "barnard", "WISE_0855": "wise0855"}
    entries = []
    for frame in index["frames"]:
        source = frame["source"]
        row = rows.get(urlsplit(source["access_url"]).path)
        if row is None or (query.target_key and query.target_key != keys.get(row["target_name"])):
            continue
        path = (pack / row["filename"]).resolve()
        if not path.is_relative_to(pack.resolve()):
            raise ValueError("Invalid notebook fixture path")
        entries.append(
            {
                "fits_path": str(path),
                "obs_id": source["obs_id"],
                "obs_publisher_did": source["obs_publisher_did"],
                "detector": source["energy_bandpassname"],
                "mjd": source["t_min"],
                "ra": float(row["target_ra_deg"]),
                "dec": float(row["target_dec_deg"]),
            }
        )
    return entries


def sync_five_targets_manifest(data_dir: Path) -> None:
    """Keep data/fixtures/manifest.json synchronized with data/five_targets/*/inputs.json."""
    targets_dir = data_dir / "five_targets"
    manifest_path = data_dir / "fixtures" / "manifest.json"
    if not targets_dir.is_dir() or not manifest_path.is_file():
        return
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return

    catalog_targets = targets()
    rebuilt_entries = []
    for target_key, folder_name in FIVE_TARGETS_FOLDERS.items():
        folder = targets_dir / folder_name
        inputs_json = folder / "inputs.json"
        if not inputs_json.is_file():
            continue
        target_meta = {}
        if (folder / "target.json").is_file():
            target_meta = json.loads((folder / "target.json").read_text(encoding="utf-8"))
        record = catalog_targets.get(target_key, ({}, ""))[0]
        target_name = record.get("name", target_key)
        j2000 = target_meta.get("j2000_deg")
        ra = round(float(j2000[0]), 6) if j2000 else float(record.get("ra", 0.0))
        dec = round(float(j2000[1]), 6) if j2000 else float(record.get("dec", 0.0))

        for item in json.loads(inputs_json.read_text(encoding="utf-8")):
            fpath = (ROOT / item["path"]).resolve()
            if not fpath.is_file():
                continue
            det_short = item["detector"]
            det_num = int(det_short.removeprefix("D"))
            rebuilt_entries.append(
                {
                    "target_key": target_key,
                    "target_name": target_name,
                    "obs_id": item["obs_id"],
                    "obs_publisher_did": f"ivo://irsa.ipac/spherex_qr2?{item['obs_id']}/D{det_num}",
                    "detector": f"SPHEREx-D{det_num}",
                    "detector_short": det_short,
                    "mjd": float(item["mjd"]),
                    "t_min": float(item.get("cluster_start_mjd", item["mjd"])),
                    "t_max": float(item.get("cluster_end_mjd", item["mjd"])),
                    "ra": ra,
                    "dec": dec,
                    "cutout_size_deg": float(item.get("cutout_size_deg", 0.1)),
                    "fits_path": item["path"],
                    "file_size": fpath.stat().st_size,
                    "sha256": item.get("sha256") or hashlib.sha256(fpath.read_bytes()).hexdigest(),
                    "cutout_url": item.get("url", ""),
                }
            )

    if not rebuilt_entries:
        return
    manifest_entries = manifest_data.get("entries", [])
    existing_shas = {e.get("sha256") for e in manifest_entries}
    rebuilt_shas = {e["sha256"] for e in rebuilt_entries}
    if len(manifest_entries) == len(rebuilt_entries) and existing_shas == rebuilt_shas:
        return

    manifest_path.write_text(
        json.dumps(
            {
                "version": manifest_data.get("version", "1.0.0"),
                "collection": manifest_data.get("collection", "spherex_qr2"),
                "total_targets": len(FIVE_TARGETS_FOLDERS),
                "total_frames": len(rebuilt_entries),
                "entries": rebuilt_entries,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def five_targets_entries(data_dir, query):
    """Load cutouts directly from data/five_targets/ if manifest.json is absent."""
    targets_dir = data_dir / "five_targets"
    if not targets_dir.is_dir():
        return []
    folder_map = FIVE_TARGETS_FOLDERS
    target_key = query.target_key
    if not target_key and query.ra is not None and query.dec is not None:
        coords_map = {
            "barnard": (269.452, 4.693),
            "wise0855": (133.819, -7.247),
            "epsindib": (331.044, -56.783),
            "rwaur": (77.465, 30.402),
            "rdra": (247.554, 66.705),
        }
        for k, (cra, cdec) in coords_map.items():
            if (query.ra - cra) ** 2 + (query.dec - cdec) ** 2 < 0.04:
                target_key = k
                break
    folder = folder_map.get(target_key)
    if not folder:
        return []
    inputs_json = targets_dir / folder / "inputs.json"
    if not inputs_json.is_file():
        return []
    try:
        items = json.loads(inputs_json.read_text(encoding="utf-8"))
    except Exception:
        return []
    entries = []
    for item in items:
        fpath = (ROOT / item["path"]).resolve()
        if not fpath.is_file():
            continue
        det_str = item["detector"]
        det_int = int(det_str.removeprefix("D"))
        entries.append(
            {
                "fits_path": str(fpath),
                "obs_id": item["obs_id"],
                "obs_publisher_did": f"ivo://irsa.ipac/spherex_qr2?{item['obs_id']}/D{det_int}",
                "detector": f"SPHEREx-D{det_int}",
                "mjd": float(item["mjd"]),
                "sha256": item.get("sha256", ""),
            }
        )
    return entries


def matching_cutouts(query):
    data_dir = (ROOT / os.getenv("DATA_DIR", "data")).resolve()
    sync_five_targets_manifest(data_dir)
    manifest = data_dir / "fixtures" / "manifest.json"
    if not manifest.is_file() and data_dir == ROOT / "data":
        manifest = ROOT / "members" / "khoi" / "fixtures_manifest.json"
    entries = []
    if manifest.is_file():
        entries = find_frames(
            target_key=query.target_key,
            data_dir=data_dir,
            mode="fixture",
        )
        if not entries:
            # The handoff returns [] for an unreadable manifest as well as a
            # query with no matches. A malformed index must surface as an error.
            json.loads(manifest.read_text(encoding="utf-8"))
    if not any(Path(row["fits_path"]).is_file() for row in entries):
        entries = pack_entries(data_dir, query)
    if not any(Path(row["fits_path"]).is_file() for row in entries):
        entries = five_targets_entries(data_dir, query)
    if not any(Path(row["fits_path"]).is_file() for row in entries):
        return None

    cutouts = []
    for row in entries:
        path = Path(row["fits_path"]).resolve()
        if not path.is_relative_to(data_dir):
            raise ValueError("FITS fixture path must be within DATA_DIR")
        if not path.is_file():
            raise ValueError("An indexed FITS fixture is missing")
        stat = path.stat()
        publisher = row["obs_publisher_did"]
        collection = publisher.partition("?")[0].rsplit("/", 1)[-1]
        release = collection.removeprefix("spherex_")
        if not collection.startswith("spherex_qr"):
            raise ValueError("Fixture does not identify the SPHEREx data release")
        cutouts.append(
            Cutout(
                path,
                row["obs_id"],
                int(row["detector"].removeprefix("SPHEREx-D")),
                float(row["mjd"]),
                release,
                row.get("sha256", ""),
                stat.st_size,
                stat.st_mtime_ns,
            )
        )
    return tuple(sorted(set(cutouts), key=lambda row: (row.mjd, row.obs_id, str(row.path))))


@lru_cache(maxsize=16)
def render_cached(query_json, target_json, cutouts):
    # Version, query and input revisions are part of the public image identity.
    # An old browser URL continues to identify its original bytes after a rebuild.
    digest = hashlib.sha256(RENDER_VERSION.encode())
    digest.update(query_json.encode())
    for cutout in cutouts:
        digest.update(repr(cutout).encode())
        if cutout.sha256:
            with cutout.path.open("rb") as handle:
                if hashlib.file_digest(handle, "sha256").hexdigest() != cutout.sha256:
                    raise ValueError("FITS fixture checksum mismatch")
    query = FramesQuery.model_validate_json(query_json)
    result, images = build_frames(cutouts, query, digest.hexdigest()[:24])
    frames = Frames.model_validate(
        {
            **result,
            "target": Target.model_validate_json(target_json),
            "detector": query.detector,
        }
    )
    return frames, images


@lru_cache(maxsize=32)
def _measure_target_photometry(target_key: str, data_dir_str: str, aperture_arcsec: float):
    """Measure multi-band circular aperture photometry from local FITS cutouts."""
    import math

    import numpy as np
    from astropy.io import fits
    from astropy.wcs import WCS
    from astropy.wcs.utils import proj_plane_pixel_area

    cutouts = matching_cutouts(FramesQuery(ra=0.0, dec=0.0, target_key=target_key))
    if not cutouts:
        return ()

    points = []
    groups = group_images_into_visits(
        [{"t_min": c.mjd, "cutout": c} for c in cutouts]
    )
    for visit, group in enumerate(groups, start=1):
        for item in group:
            cutout = item["cutout"]
            coord = position_at(target_key, cutout.mjd)
            if coord is None:
                continue
            with fits.open(cutout.path) as hdus:
                header = hdus["IMAGE"].header
                image = np.array(hdus["IMAGE"].data, dtype=float)
                if "ZODI" in hdus:
                    image = image - np.array(hdus["ZODI"].data, dtype=float)
                variance = (
                    np.array(hdus["VARIANCE"].data, dtype=float)
                    if "VARIANCE" in hdus
                    else np.ones_like(image)
                )
                flags = np.array(hdus["FLAGS"].data)
                fh = hdus["FLAGS"].header
                bad_bits = sum(
                    1 << int(fh[k])
                    for k in fh
                    if k.startswith("MP_") and k not in {"MP_SOURCE", "MP_FULLSAMPLE"}
                )
                is_bad = (flags & bad_bits) != 0
                source_mask = (
                    (flags & (1 << int(fh["MP_SOURCE"]))) != 0
                    if "MP_SOURCE" in fh
                    else np.zeros_like(flags, dtype=bool)
                )
                wcs = WCS(header, fobj=hdus).celestial
                px, py = wcs.world_to_pixel(coord)
                x0, y0 = float(px), float(py)
                if not (0.0 <= x0 < image.shape[1] and 0.0 <= y0 < image.shape[0]):
                    continue

                spectral = header.copy()
                for k in list(spectral):
                    if k.startswith(("A_", "B_", "AP_", "BP_")):
                        del spectral[k]
                wave, _ = WCS(spectral, fobj=hdus, key="W").pixel_to_world_values(x0, y0)
                if not (math.isfinite(float(wave)) and float(wave) > 0):
                    continue
                area = abs(float(proj_plane_pixel_area(wcs))) * (np.pi / 180) ** 2

            yy, xx = np.indices(image.shape)
            dist = np.hypot(xx - x0, yy - y0)
            r_ap = max(1.5, float(aperture_arcsec) / PIXEL_SCALE)
            ap_mask = dist <= r_ap
            ann_mask = (dist >= 6.0) & (dist <= 12.0)
            good_data = np.isfinite(image) & np.isfinite(variance) & (variance >= 0)

            bg_mask = ann_mask & good_data & (~is_bad) & (~source_mask)
            if bg_mask.sum() < 15:
                bg_mask = ann_mask & good_data & (~is_bad)
            if bg_mask.sum() < 10:
                bg_mask = good_data & (~is_bad)
            if bg_mask.sum() < 5:
                continue

            bg_level = float(np.median(image[bg_mask]))
            bg_var = float(np.sum(variance[bg_mask]) / (bg_mask.sum() ** 2))
            ap_good = ap_mask & good_data & (~is_bad)
            flagged = bool((is_bad & ap_mask).any())
            factor = area * 1e9

            if ap_good.sum() > 0:
                flux_mjy = float(np.sum(image[ap_good] - bg_level) * factor)
                var_sum = float(np.sum(variance[ap_good]) + (int(ap_good.sum()) ** 2) * bg_var)
                err_mjy = float(np.sqrt(max(var_sum, 1e-12)) * factor)
                snr = float(flux_mjy / err_mjy) if err_mjy > 0 else None
                detected = bool(snr is not None and snr >= 3.0 and flux_mjy > 0)
            else:
                flux_mjy, err_mjy, snr, detected = None, None, None, False

            if flux_mjy is not None and not math.isfinite(flux_mjy):
                flux_mjy = None
            if err_mjy is not None and not math.isfinite(err_mjy):
                err_mjy = None
            if snr is not None and not math.isfinite(snr):
                snr = None

            points.append(
                {
                    "frame_id": f"phot-{target_key}-d{cutout.detector}-{cutout.obs_id}",
                    "mjd": float(cutout.mjd),
                    "wavelength_um": float(wave),
                    "detector": int(cutout.detector),
                    "release": cutout.release,
                    "survey": int(visit),
                    "flux_mjy": flux_mjy,
                    "err_mjy": err_mjy,
                    "snr": snr,
                    "detected": detected,
                    "flagged": flagged,
                    "is_reference_star": False,
                }
            )
    points.sort(key=lambda p: (p["mjd"], p["detector"], p["frame_id"]))
    return tuple(points)


def observed_photometry(query: PhotometryQuery, target_dict: dict):
    """Return real multi-band photometry when running against local five_targets FITS data."""
    data_dir = (ROOT / os.getenv("DATA_DIR", "data")).resolve()
    if data_dir != (ROOT / "data").resolve() or not (data_dir / "five_targets").is_dir():
        return None
    if query.target_key not in {"barnard", "wise0855", "epsindib", "rwaur"}:
        return None
    points = [
        dict(p)
        for p in _measure_target_photometry(
            query.target_key, str(data_dir), float(query.aperture_arcsec)
        )
        if query.detector is None or p["detector"] == query.detector
    ]
    return {
        "api_version": "0.1",
        "target": target_dict,
        "reference_star": None,
        "points": points,
        "variability": None,
    }
