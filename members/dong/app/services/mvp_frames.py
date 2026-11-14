"""Synchronous MVP frame orchestration with prebuilt and cached PNG bundles."""

import hashlib
import json
import logging
import math
import os
import time
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory
from urllib.parse import urlsplit
from uuid import uuid4

from astropy.time import Time
from diskcache import Cache
from pydantic import ValidationError

from shared.frames_pipeline import render_cutouts
from shared.pipeline import irsa

from ..legacy.schemas import WarningMessage
from ..mvp_models import MVPFrames, MVPQuery, MVPSource
from .catalog import position_at, targets

ROOT = Path(__file__).resolve().parents[4]
SAMPLES = ROOT / "api_samples"
REQUEST_TIMEOUT = 120
QR2_MIDPOINT_MJD = (60800 + 61174) / 2
VERSION = "mvp-tan-visit-v1"
logger = logging.getLogger("uvicorn.error")
OBJECT_TYPES = {
    "barnard": "red dwarf",
    "wise0855": "brown dwarf",
    "epsindib": "brown dwarf pair",
    "rwaur": "T Tauri star",
    "rdra": "Mira variable",
}


class MVPError(Exception):
    def __init__(self, status, code, message):
        super().__init__(message)
        self.status = status
        self.code = code


def timeout_error():
    return MVPError(504, "UPSTREAM_TIMEOUT", "The frame request exceeded its time budget.")


def check_deadline(deadline):
    if time.monotonic() >= deadline:
        raise timeout_error()


@contextmanager
def timed_stage(name, deadline):
    check_deadline(deadline)
    started = time.monotonic()
    try:
        yield
        check_deadline(deadline)
    finally:
        logger.info(
            "mvp_frames stage=%s duration_ms=%.2f", name, (time.monotonic() - started) * 1000
        )


def data_dir():
    return (ROOT / os.getenv("DATA_DIR", "data")).resolve()


def open_cache():
    return Cache(str(data_dir() / "cache" / "mvp"), size_limit=512 * 1024 * 1024, timeout=1)


def target_options():
    epoch = Time(QR2_MIDPOINT_MJD, format="mjd", scale="utc").tt.jyear
    for key, (record, _) in targets().items():
        center = position_at(key, QR2_MIDPOINT_MJD)
        yield {
            "id": key,
            "name": record["name"],
            "object_type": OBJECT_TYPES[key],
            "ra_deg": float(center.ra.deg),
            "dec_deg": float(center.dec.deg),
            "epoch_jyear": float(epoch),
            "default_detector": 6,
            "default_fov_arcmin": 10 if key == "epsindib" else 2,
        }


def sky_bucket(ra, dec):
    return round(ra, 4) % 360, round(dec, 4)


def query_key(query, mode):
    # The rounded sky bucket follows the SRS. The exact query avoids reusing
    # a different WCS center or time interval within that bucket.
    content = (VERSION, mode, sky_bucket(query.s_ra, query.s_dec), query.model_dump())
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def prebuilt_directory(query):
    bucket = sky_bucket(query.s_ra, query.s_dec)
    for target in target_options():
        if bucket == sky_bucket(target["ra_deg"], target["dec_deg"]):
            detector = query.energy_bandpassname.removeprefix("SPHEREx-")
            key = hashlib.sha256(json.dumps(prebuilt_identity(query)).encode()).hexdigest()[:24]
            return data_dir() / "prebuilt" / target["id"] / detector / key
    return None


def prebuilt_identity(query):
    return (
        VERSION,
        sky_bucket(query.s_ra, query.s_dec),
        round(query.cutout_size_deg, 4),
        query.energy_bandpassname,
        query.obs_collection,
        query.t_min,
        query.t_max,
    )


def warning(code, message):
    return {"code": code, "message": message}


def mock_bundle(query):
    sample = json.loads((SAMPLES / "frames_barnard_d6.json").read_text(encoding="utf-8"))
    frames, images = [], {}
    for index, source in enumerate(sample["frames"]):
        filename = f"frame-{index}.png"
        images[filename] = (SAMPLES / "png" / filename).read_bytes()
        frames.append(
            {
                "frame_id": f"mock-{index}",
                "image_url": filename,
                "visit_index": index,
                "visit_label": f"Visit {index + 1}",
                "t_min": source["mjd"],
                "t_max": source["mjd"],
                "observation_time": source["iso"],
                "energy_bandpassname": query.energy_bandpassname,
                "obs_collection": query.obs_collection,
                "n_images": 0,
                "source_obs_publisher_dids": [],
                "warnings": [],
            }
        )
    return MVPFrames(
        data_kind="mock",
        query=query,
        grid={
            "projection": "TAN",
            "center_ra_deg": query.s_ra,
            "center_dec_deg": query.s_dec,
            "pixel_scale_arcsec": query.cutout_size_deg * 3600 / sample["grid"]["width"],
            "width_px": sample["grid"]["width"],
            "height_px": sample["grid"]["height"],
        },
        display={**sample["norm"], "unit": "MJy/sr"},
        frames=frames,
        sources=[],
        warnings=[warning("MOCK_DATA", "Synthetic sample frames for testing the viewer.")],
    ), images


def read_prebuilt(query):
    directory = prebuilt_directory(query)
    if directory is None or not (directory / "bundle.json").is_file():
        return None
    result = MVPFrames.model_validate_json((directory / "bundle.json").read_bytes())
    if (
        prebuilt_identity(result.query) != prebuilt_identity(query)
        or result.data_kind != "observational"
        or not result.frames
    ):
        raise ValueError("Invalid prebuilt bundle for this query")
    images = {}
    for frame in [*result.frames, *result.difference_frames]:
        filename = frame.image_url
        image = (directory / filename).resolve()
        if image.parent != directory.resolve() or image.suffix != ".png" or image.name != filename:
            raise ValueError("Invalid prebuilt PNG filename")
        images[filename] = image.read_bytes()
        if not images[filename].startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("Invalid prebuilt PNG")
    result.warnings.insert(
        0, WarningMessage(code="PREBUILT", message="Frames are from the local prebuilt pack.")
    )
    result.query = query
    return result, images


def atomic_write(path, content):
    with NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(content)
        except OSError:
            handle.close()
            temporary.unlink(missing_ok=True)
            raise
    try:
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)


def write_prebuilt(query, result, images):
    directory = prebuilt_directory(query)
    if directory is None or not result.frames or result.data_kind != "observational":
        raise ValueError("A prebuilt bundle requires observed frames for a known target center")
    directory.mkdir(parents=True, exist_ok=True)
    for frame in [*result.frames, *result.difference_frames]:
        image = images[frame.image_url]
        filename = f"{hashlib.sha256(image).hexdigest()[:24]}.png"
        atomic_write(directory / filename, image)
        frame.image_url = filename
    atomic_write(directory / "bundle.json", result.model_dump_json(indent=2).encode())
    return directory


def build_observed(query, inputs, failed, deadline):
    def stage(name):
        return timed_stage(name, deadline)

    ordered = sorted(inputs, key=lambda item: (item[0]["t_min"], item[0]["obs_publisher_did"]))
    result, images, grid, display = render_cutouts(query.model_dump(), ordered, "live", stage)
    frames = result["frames"]
    for index, frame in enumerate(frames):
        frame.update(visit_index=index, visit_label=f"Visit {index + 1}")
    if display is not None:
        display["unit"] = display["unit"].replace(" ", "")
    if len(frames) == 1:
        result["warnings"].append(warning("SINGLE_VISIT", "Only one observing visit is available."))
    if failed:
        result["warnings"].append(
            warning("PARTIAL_DOWNLOAD", f"{failed} cutouts could not be retrieved.")
        )
    return MVPFrames.model_validate({**result, "grid": grid, "display": display}), images


def archive_bundle(query, deadline):
    with timed_stage("discovery", deadline):
        sources = irsa.find_images(
            query.s_ra,
            query.s_dec,
            query.obs_collection,
            query.energy_bandpassname,
            query.t_min,
            query.t_max,
            search_radius_deg=query.cutout_size_deg / math.sqrt(2),
            timeout_s=20,
            deadline=deadline,
        )
        try:
            sources = [MVPSource.model_validate(row).model_dump() for row in sources]
        except ValidationError as exc:
            raise irsa.UpstreamError("IRSA returned incomplete source metadata") from exc
        if not sources:
            return build_observed(query, [], 0, deadline)
        for source in sources:
            parsed = urlsplit(source["access_url"])
            if parsed.scheme != "https" or parsed.netloc != "irsa.ipac.caltech.edu":
                raise irsa.UpstreamError("Unexpected source URL from IRSA")

    by_did = {source["obs_publisher_did"]: source for source in sources}
    with TemporaryDirectory(dir=data_dir() / "cache" / "mvp") as work:
        out = Path(work) / "cutouts"
        with timed_stage("download", deadline):
            manifest_path = irsa.fetch_cutouts(
                sources,
                query.s_ra,
                query.s_dec,
                query.cutout_size_deg,
                out,
                timeout_s=20,
                deadline=deadline,
                max_per_visit=6,
            )
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            inputs = []
            for entry in manifest["entries"]:
                path = (out.parent / entry["path"]).resolve()
                if not path.is_relative_to(out):
                    raise ValueError("Invalid FITS path in IRSA download manifest")
                with path.open("rb") as handle:
                    if hashlib.file_digest(handle, "sha256").hexdigest() != entry["sha256"]:
                        raise ValueError("Downloaded FITS checksum mismatch")
                inputs.append((by_did[entry["obs_publisher_did"]], path))
            failed = manifest["failed"]
            if not inputs:
                if failed and all(entry.get("kind") == "timeout" for entry in failed):
                    raise irsa.UpstreamTimeout("All cutouts timed out")
                raise irsa.UpstreamError("No requested cutouts could be downloaded")
        return build_observed(query, inputs, len(failed), deadline)


def publish(cache, key, result, images):
    digest = hashlib.sha256(result.model_dump_json().encode())
    for name, content in sorted(images.items()):
        digest.update(name.encode())
        digest.update(hashlib.sha256(content).digest())
    bundle_id = digest.hexdigest()
    for frame in [*result.frames, *result.difference_frames]:
        if frame.image_url not in images:
            raise ValueError("PNG for frame is missing")
        frame.image_url = f"/files/{bundle_id}/{frame.image_url}"
    payload = result.model_dump(mode="json")
    # One record holds both metadata and its images, so publication is atomic.
    with cache.transact():
        cache.set(("bundle", bundle_id), (payload, images), expire=86400)
        cache.set(("lookup", key), bundle_id, expire=3600 if result.frames else 60)
    return payload


def get_frames(query: MVPQuery, deadline):
    mode = os.getenv("API_MODE", "mock")
    if mode not in {"mock", "real"}:
        raise MVPError(500, "PROCESSING_ERROR", "API_MODE must be mock or real.")
    key = query_key(query, mode)
    with open_cache() as cache:
        if mode == "real":
            with timed_stage("prebuilt", deadline):
                prebuilt = read_prebuilt(query)
                if prebuilt is not None:
                    return publish(cache, key, *prebuilt), "PREBUILT"

        claim = ("claim", key)
        token = uuid4().hex
        while True:
            check_deadline(deadline)
            cached = cache.get(("bundle", cache.get(("lookup", key))))
            if cached is not None:
                logger.info("mvp_frames cache=hit")
                return cached[0], "HIT"
            if cache.add(claim, token, expire=REQUEST_TIMEOUT + 10):
                break
            time.sleep(0.05)
        try:
            try:
                result, images = (
                    mock_bundle(query) if mode == "mock" else archive_bundle(query, deadline)
                )
            except irsa.UpstreamTimeout as exc:
                raise timeout_error() from exc
            except irsa.UpstreamError as exc:
                raise MVPError(
                    502, "UPSTREAM_ERROR", "IRSA could not supply the requested frames."
                ) from exc
            with timed_stage("publish", deadline):
                return publish(cache, key, result, images), "MISS"
        finally:
            with cache.transact():
                if cache.get(claim) == token:
                    cache.delete(claim)


def get_image(path):
    bundle_id, separator, filename = path.partition("/")
    if not separator or len(bundle_id) != 64:
        return None
    with open_cache() as cache:
        bundle = cache.get(("bundle", bundle_id))
        return None if bundle is None else bundle[1].get(filename)
