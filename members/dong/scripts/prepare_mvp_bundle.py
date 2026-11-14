"""Prepare a local MVP bundle from a teammate's FITS manifest or the v1 pack."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "members" / "dong")]

from app.mvp_models import MVPQuery, MVPSource
from app.services.mvp_frames import (
    REQUEST_TIMEOUT,
    build_observed,
    data_dir,
    target_options,
    write_prebuilt,
)
from app.services.observed_frames import pack_entries


def manifest_path(entry, manifest, base):
    relative = Path(entry.get("fits_path") or entry["path"])
    if not relative.is_absolute() and relative.parts[0] == "data":
        relative = Path(*relative.parts[1:])
    for candidate in ((manifest.parent / relative).resolve(), (base / relative).resolve()):
        if candidate.is_relative_to(base) and candidate.is_file():
            return candidate
    raise ValueError(f"FITS missing from DATA_DIR for observation {entry['obs_id']}")


def manifest_entries(manifest, target):
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    for row in payload["entries"]:
        if row.get("target_key") != target:
            continue
        did = row["obs_publisher_did"]
        collection = did.split("?", 1)[0].rsplit("/", 1)[-1]
        access_url = row.get("access_url") or row["cutout_url"].split("?", 1)[0]
        detector = str(row["detector"]).removeprefix("SPHEREx-")
        yield {
            **row,
            "cutout_size_deg": row.get("cutout_size_deg") or payload.get("cutout_size_deg"),
            "source": {
                "obs_id": row["obs_id"],
                "obs_publisher_did": did,
                "obs_collection": collection,
                "energy_bandpassname": f"SPHEREx-{detector}",
                "t_min": row["mjd"],
                "t_max": row.get("t_max", row["mjd"]),
                "access_url": access_url,
                "access_format": "image/fits",
            },
        }


def prepare(target, detector, size, collection, manifest):
    query = MVPQuery(
        s_ra=target["ra_deg"],
        s_dec=target["dec_deg"],
        obs_collection=collection,
        energy_bandpassname=f"SPHEREx-D{detector}",
        cutout_size_deg=size,
    )
    base = data_dir()
    entries = (
        manifest_entries(manifest, target["id"])
        if manifest
        else pack_entries(base, SimpleNamespace(target_key=target["id"]))
    )
    inputs = []
    for row in entries:
        source = MVPSource.model_validate(row["source"])
        if (
            source.obs_collection != collection
            or source.energy_bandpassname != query.energy_bandpassname
        ):
            continue
        if row["cutout_size_deg"] is None or float(row["cutout_size_deg"]) < size:
            continue
        path = manifest_path(row, manifest, base) if manifest else Path(row["fits_path"])
        if row.get("sha256"):
            with path.open("rb") as handle:
                if hashlib.file_digest(handle, "sha256").hexdigest() != row["sha256"]:
                    raise ValueError(f"Checksum mismatch for {source.obs_id}")
        inputs.append((source.model_dump(), path))
    if not inputs:
        raise ValueError("No local cutouts match this target, detector, release and FOV.")
    result, images = build_observed(query, inputs, 0, time.monotonic() + REQUEST_TIMEOUT)
    return write_prebuilt(query, result, images)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    options = {target["id"]: target for target in target_options()}
    parser.add_argument("target", choices=options)
    parser.add_argument("--detector", type=int, choices=range(1, 7))
    parser.add_argument("--fov-arcmin", type=float)
    parser.add_argument(
        "--collection", choices=["spherex_dr1", "spherex_qr2", "spherex_qr3"], default="spherex_dr1"
    )
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    target = options[args.target]
    detector = args.detector or target["default_detector"]
    fov = target["default_fov_arcmin"] if args.fov_arcmin is None else args.fov_arcmin
    try:
        print(prepare(target, detector, fov / 60, args.collection, args.manifest))
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")


if __name__ == "__main__":
    main()
