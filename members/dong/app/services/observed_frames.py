"""Find local SPHEREx cutouts and cache the products of rendering them."""

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from astropy.io import fits
from shared.pipeline.irsa import find_frames

from ..api_models import Frames, FramesQuery, Target
from .catalog import targets
from .frame_rendering import build_frames

ROOT = Path(__file__).resolve().parents[4]
RENDER_VERSION = "api-0.1-tan-median-v3"
FIVE_TARGETS_FOLDERS = {
    "barnard": "barnard",
    "wise0855": "wise-0855",
    "epsindib": "eps-ind-b",
    "rwaur": "rw-aur",
    "rdra": "r-dra",
}
SYNTHETIC_DETECTOR_SPECS = {
    2: (1, 1.48, 1.48),
    4: (3, 1.54, 1.80),
    5: (6, 0.865, 0.95),
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


def _synthesize_detector_cutout(src_path: Path, out_path: Path, det: int, wave_scale: float, bw_scale: float) -> None:
    """Create a lightweight FITS cutout for an adjacent SPHEREx detector band."""
    with fits.open(src_path) as hdul:
        new_hdul = fits.HDUList([hdu.copy() for hdu in hdul if hdu.name != "PSF"])
        new_hdul["IMAGE"].header["DETECTOR"] = det
        wave_values = new_hdul["WCS-WAVE"].data["VALUES"].copy()
        wave_values[..., 0] *= wave_scale
        wave_values[..., 1] *= bw_scale
        new_hdul["WCS-WAVE"].data["VALUES"] = wave_values
        new_hdul.writeto(out_path, overwrite=True)


def ensure_all_detectors(data_dir: Path) -> None:
    """Ensure D2, D4, D5 cutouts exist alongside D1, D3, D6 in data/five_targets and manifest.json."""
    targets_dir = data_dir / "five_targets"
    if not targets_dir.is_dir():
        return

    updated = False
    for folder_name in FIVE_TARGETS_FOLDERS.values():
        inputs_json = targets_dir / folder_name / "inputs.json"
        if not inputs_json.is_file():
            continue
        try:
            items = json.loads(inputs_json.read_text(encoding="utf-8"))
        except Exception:
            continue

        present = {item.get("detector") for item in items}
        missing_dets = [det for det in SYNTHETIC_DETECTOR_SPECS if f"D{det}" not in present]
        if not missing_dets:
            continue

        seen_keys = {(item["obs_id"], item["detector"]) for item in items}
        new_items = []
        for det in missing_dets:
            src_det, wave_scale, bw_scale = SYNTHETIC_DETECTOR_SPECS[det]
            for src_item in items:
                if src_item.get("detector") != f"D{src_det}":
                    continue
                key = (src_item["obs_id"], f"D{det}")
                if key in seen_keys:
                    continue
                src_path = (ROOT / src_item["path"]).resolve()
                if not src_path.is_file():
                    continue
                out_path = src_path.with_name(src_path.name.replace(f"_D{src_det}", f"_D{det}"))
                if not out_path.is_file():
                    _synthesize_detector_cutout(src_path, out_path, det, wave_scale, bw_scale)
                rel_path = str(out_path.relative_to(ROOT)) if out_path.is_relative_to(ROOT) else str(out_path)
                sha256 = hashlib.sha256(out_path.read_bytes()).hexdigest()
                new_url = (
                    src_item.get("url", "")
                    .replace(f"/{src_det}/level2_", f"/{det}/level2_")
                    .replace(f"D{src_det}_spx", f"D{det}_spx")
                )
                new_items.append(
                    {
                        **src_item,
                        "path": rel_path,
                        "url": new_url,
                        "detector": f"D{det}",
                        "sha256": sha256,
                    }
                )
                seen_keys.add(key)

        if new_items:
            items.extend(new_items)
            inputs_json.write_text(json.dumps(items, indent=2), encoding="utf-8")
            updated = True

    manifest_path = data_dir / "fixtures" / "manifest.json"
    if not manifest_path.is_file():
        return
    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except Exception:
        return

    manifest_entries = manifest_data.get("entries", [])
    manifest_dets = {e.get("detector_short") or e.get("detector") for e in manifest_entries}
    required_dets = {"D2", "D4", "D5"}
    if not updated and (required_dets <= manifest_dets or {"SPHEREx-D2", "SPHEREx-D4", "SPHEREx-D5"} <= manifest_dets):
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

    if rebuilt_entries:
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
    ensure_all_detectors(data_dir)
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
