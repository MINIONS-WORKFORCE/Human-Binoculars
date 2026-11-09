"""Offline API 0.1 fixtures. All example measurements and pixels are synthetic."""

import hashlib
import json
import os
from collections import OrderedDict
from pathlib import Path
from threading import RLock

from ..api_models import (
    Frames,
    FramesQuery,
    PhotometryQuery,
    ResolveQuery,
    ScienceQuery,
)

ROOT = Path(__file__).resolve().parents[4]
SAMPLES = ROOT / "api_samples"
TARGETS = {
    "barnard": "Barnard's Star",
    "wise0855": "WISE 0855-0714",
    "epsindib": "Epsilon Indi B",
    "rwaur": "RW Aurigae",
    "rdra": "R Draconis",
}
images = OrderedDict()
image_lock = RLock()


class FixtureError(Exception):
    def __init__(self, status, code, message, details):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.details = details


def fail(status, code, message, details=None):
    raise FixtureError(status, code, message, details or {})


def sample(filename):
    if os.getenv("DATA_MODE", "fixture") != "fixture":
        fail(500, "INTERNAL", "Live API 0.1 adapters await team integration.")
    return json.loads((SAMPLES / filename).read_text(encoding="utf-8"))


def target(query):
    if query.target_key is not None and query.target_key not in TARGETS:
        fail(404, "UNKNOWN_TARGET", "Unknown fixture target.", {"target_key": query.target_key})
    return {
        "ra": query.ra,
        "dec": query.dec,
        "target_key": query.target_key,
        "name": TARGETS.get(query.target_key),
    }


def health():
    result = sample("health.json")
    result["git_sha"] = os.getenv("GIT_SHA", "unknown")
    return result


def resolve(query: ResolveQuery):
    if query.name.strip().lower() not in {"barnard", "barnards star", "barnard's star"}:
        fail(404, "UNKNOWN_TARGET", "Name absent from fixture resolver.", {"name": query.name})
    result = sample("resolve_barnard.json")
    result["query"] = query.name
    return result


def frames(query: FramesQuery):
    result = sample("frames_barnard_d6.json")
    result["target"] = target(query)
    result["detector"] = query.detector
    result["grid"].update(center_ra=query.ra, center_dec=query.dec)
    identity = hashlib.sha256(query.model_dump_json().encode()).hexdigest()[:24]
    original_count = len(result["frames"])
    result["frames"] = result["frames"][: query.max_frames]
    if len(result["frames"]) < original_count:
        result["warnings"].append("TRUNCATED")
    if len(result["frames"]) < 3:
        result["warnings"].append("FEW_FRAMES")
    published = {}
    for index, frame in enumerate(result["frames"]):
        frame_id = f"fixture-{identity}-{index}"
        frame["id"] = frame_id
        frame["predicted_px"] = frame["predicted_px"] if query.target_key else None
        frame["png"] = f"/api/frames/{frame_id}.png"
        frame["diff_png"] = f"/api/frames/{frame_id}/diff.png"
        published[frame_id] = (
            (SAMPLES / f"png/frame-{index}.png").read_bytes(),
            (SAMPLES / f"png/frame-{index}_diff.png").read_bytes(),
        )
    result["reference_frame_id"] = result["frames"][0]["id"]
    result = Frames.model_validate(result)
    with image_lock:
        images.update(published)
        while len(images) > 1200:
            images.popitem(last=False)
    return result


def image(frame_id, difference):
    sample("health.json")
    with image_lock:
        content = images.get(frame_id)
    if content is None:
        fail(404, "FRAME_NOT_FOUND", "Call /api/frames first or reload the list.", {"id": frame_id})
    return content[difference]


def photometry(query: PhotometryQuery):
    result = sample("photometry_rdra.json")
    result["target"] = target(query)
    if query.detector is not None:
        result["points"] = [p for p in result["points"] if p["detector"] == query.detector]
    result["variability"] = None
    return result


def astrometry(query: ScienceQuery):
    result = sample("astrometry_barnard.json")
    result["target"] = target(query)
    # The supplied astrometry sample contains D6 measurements only.
    if query.detector is not None and query.detector != 6:
        result["points"] = []
        result["fit"] = None
    return result
