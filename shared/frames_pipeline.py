"""Training pipeline adapted from Khoi's cutout notebook and Huu Hoang's
reproject_demo.py (9c30daf). All outputs use a fixed ICRS sky grid.
"""

import csv
import io
import json
import math
import time
import warnings
from urllib.parse import urlsplit

import numpy as np
import requests
from astropy.io import fits
from astropy.table import Table
from astropy.time import Time
from astropy.wcs import WCS
from PIL import Image

from shared.image_processing import build_frames, diff_png, mask_flags, rgb_png  # noqa: F401

# Official API 0.1 build_frames implementation by Huu Hoang (Contract section 6)
import sys
from pathlib import Path

_HH_DIR = Path(__file__).resolve().parents[1] / "members" / "huu-hoang"
if str(_HH_DIR) not in sys.path:
    sys.path.insert(0, str(_HH_DIR))
try:
    from build_frames import build_frames
except ImportError:
    build_frames = None

VERSION = "fixed-grid-median-gap30-preview-v1"


def request(url, params=None):
    for attempt in range(3):
        try:
            response = requests.get(url, params=params, timeout=120)
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)


def discover(query):
    params = {
        "COLLECTION": query["obs_collection"],
        "POS": f"CIRCLE {query['s_ra']} {query['s_dec']} {query['cutout_size_deg'] / math.sqrt(2)}",
    }
    if query.get("t_min") is not None or query.get("t_max") is not None:
        params["TIME"] = (
            f"{query.get('t_min') if query.get('t_min') is not None else '-Inf'} {query.get('t_max') if query.get('t_max') is not None else '+Inf'}"
        )
    table = Table.read(
        io.BytesIO(request("https://irsa.ipac.caltech.edu/SIA", params)),
        format="votable",
        use_names_over_ids=True,
    )
    fields = (
        "obs_id",
        "obs_publisher_did",
        "obs_collection",
        "energy_bandpassname",
        "s_ra",
        "s_dec",
        "t_min",
        "t_max",
        "access_url",
        "access_format",
    )
    sources = {}
    for row in table:
        if str(row["energy_bandpassname"]) != query["energy_bandpassname"]:
            continue
        source = {key: row[key].item() if hasattr(row[key], "item") else row[key] for key in fields}
        if source["obs_collection"] == query["obs_collection"]:
            sources[source["obs_publisher_did"]] = source
    return sorted(sources.values(), key=lambda source: source["t_min"])


def local_inputs(query, data_dir):
    pack = data_dir / "fixture_pack_v1"
    index = json.loads((pack / "rendered/frames.json").read_text(encoding="utf-8"))
    with (pack / "metadata.csv").open(encoding="utf-8-sig") as handle:
        paths = {
            urlsplit(row["cutout_url"]).path: pack / row["filename"]
            for row in csv.DictReader(handle)
        }
    result = []
    for row in index["frames"]:
        source = row["source"]
        if (
            abs(row["target_ra_deg"] - query["s_ra"]) <= 1e-6
            and abs(row["target_dec_deg"] - query["s_dec"]) <= 1e-6
            and query["cutout_size_deg"] <= row["cutout_size_deg"]
            and source["obs_collection"] == query["obs_collection"]
            and source["energy_bandpassname"] == query["energy_bandpassname"]
            and (query.get("t_min") is None or source["t_max"] >= query["t_min"])
            and (query.get("t_max") is None or source["t_min"] <= query["t_max"])
        ):
            path = paths[urlsplit(source["access_url"]).path].resolve()
            if not path.is_relative_to(pack.resolve()):
                raise ValueError("Invalid fixture path")
            result.append((source, path))
    return sorted(result, key=lambda item: item[0]["t_min"])


def make_frames(query, source_mode, data_dir, work_dir, stage):
    """Return a FramesResponse-compatible dict and PNG bytes indexed by filename."""
    from shared.image_processing import reproject_compatible as reproject_interp

    notices = [
        {
            "code": "EXPERIMENTAL_GROUPING",
            "message": "Training preview: groups split at gaps over 30 days. Wavelength/PSF/background matching and motion validation require science review.",
        }
    ]
    with stage("discovery"):
        if source_mode == "fixture":
            inputs = local_inputs(query, data_dir)
        else:
            sources = discover(query)
            if len(sources) > 40:
                raise ValueError("More than 40 images; narrow the requested time range")
            inputs = []
    if source_mode == "live":
        for index, source in enumerate(sources):
            url = source["access_url"]
            parsed = urlsplit(url)
            if parsed.scheme != "https" or parsed.hostname != "irsa.ipac.caltech.edu":
                raise ValueError("Unexpected archive URL")
            with stage("download"):
                content = request(
                    url,
                    {
                        "center": f"{query['s_ra']},{query['s_dec']}",
                        "size": query["cutout_size_deg"],
                    },
                )
                path = work_dir / f"{index}.fits"
                path.write_bytes(content)
                inputs.append((source, path))
    if not inputs:
        return {
            "data_kind": "mock" if source_mode == "fixture" else "observational",
            "query": query,
            "sources": [],
            "frames": [],
            "warnings": [
                {"code": "NO_DATA", "message": "No observations match the selected data source."}
            ],
        }, {}
    grid = WCS(naxis=2)
    size = max(1, math.ceil(query["cutout_size_deg"] * 3600 / 6.2))
    grid.wcs.crpix = [(size + 1) / 2] * 2
    grid.wcs.crval = [query["s_ra"], query["s_dec"]]
    grid.wcs.cdelt = [-6.2 / 3600, 6.2 / 3600]
    grid.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    groups = []
    unit = None
    for source, path in inputs:
        with stage("reproject"), fits.open(path, memmap=False) as hdus:
            hdu = hdus["IMAGE"]
            if (
                hdu.header["OBSID"] != source["obs_id"]
                or f"SPHEREx-D{hdu.header['DETECTOR']}" != source["energy_bandpassname"]
            ):
                raise ValueError("Source identity mismatch")
            current_unit = hdu.header.get("BUNIT")
            if not current_unit or (unit is not None and current_unit != unit):
                raise ValueError("Inconsistent image units")
            unit = current_unit
            pixels = hdu.data.astype(float)
            flags = hdus["FLAGS"]
            rejected = [
                key
                for key in flags.header
                if key.startswith("MP_") and key not in {"MP_SOURCE", "MP_FULLSAMPLE"}
            ]
            if not rejected:
                raise ValueError("Missing flag definitions")
            pixels = mask_flags(pixels, flags.data, flags.header)
            aligned, footprint = reproject_interp(
                (pixels, WCS(hdu.header, fobj=hdus).celestial),
                grid,
                shape_out=(size, size),
                order="bilinear",
            )
            aligned[footprint <= 0] = np.nan
        if not groups or source["t_min"] - groups[-1][-1][0]["t_min"] > 30:
            groups.append([])
        groups[-1].append((source, aligned))
    with stage("stack"):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            stacks = [
                np.nanmedian(np.stack([pixels for _, pixels in group]), axis=0) for group in groups
            ]
        finite = np.concatenate([pixels[np.isfinite(pixels)] for pixels in stacks])
        if not finite.size:
            raise ValueError("No usable pixels after masking and reprojection")
        low, high = np.percentile(finite, [2, 99.5])
    images = {}
    frames = []
    with stage("render"):
        for index, (group, pixels) in enumerate(zip(groups, stacks)):
            valid = np.isfinite(pixels)
            gray = np.zeros(pixels.shape, dtype=np.uint8)
            gray[valid] = np.rint(
                255
                * np.arcsinh(10 * np.clip((pixels[valid] - low) / max(high - low, 1e-12), 0, 1))
                / np.arcsinh(10)
            )
            image = Image.fromarray(
                np.flipud(np.stack([gray, valid.astype(np.uint8) * 255], axis=-1))
            )
            buffer = io.BytesIO()
            image.save(buffer, format="PNG")
            name = f"frame-{index}.png"
            images[name] = buffer.getvalue()
            start = min(source["t_min"] for source, _ in group)
            end = max(source["t_max"] for source, _ in group)
            frames.append(
                {
                    "frame_id": f"frame-{index}",
                    "image_url": name,
                    "t_min": start,
                    "t_max": end,
                    "observation_time": Time((start + end) / 2, format="mjd").isot + "Z",
                    "energy_bandpassname": query["energy_bandpassname"],
                    "obs_collection": query["obs_collection"],
                    "n_images": len(group),
                    "source_obs_publisher_dids": [
                        source["obs_publisher_did"] for source, _ in group
                    ],
                    "warnings": notices,
                }
            )
    return {
        "data_kind": "mock" if source_mode == "fixture" else "observational",
        "query": query,
        "sources": [source for source, _ in inputs],
        "frames": frames,
        "warnings": notices,
    }, images
