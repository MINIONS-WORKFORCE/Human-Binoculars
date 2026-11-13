"""Find local SPHEREx cutouts and cache the products of rendering them."""

import csv
import hashlib
import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from shared.pipeline.irsa import find_frames

from ..api_models import Frames, FramesQuery, Target
from .frame_rendering import build_frames

ROOT = Path(__file__).resolve().parents[4]
RENDER_VERSION = "api-0.1-tan-median-v3"


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


def five_targets_entries(data_dir, query):
    """Load cutouts directly from data/five_targets/ if manifest.json is absent."""
    targets_dir = data_dir / "five_targets"
    if not targets_dir.is_dir():
        return []
    folder_map = {
        "barnard": "barnard",
        "wise0855": "wise-0855",
        "epsindib": "eps-ind-b",
        "rwaur": "rw-aur",
        "rdra": "r-dra",
    }
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
        if query.detector is not None and det_int != query.detector:
            continue
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
