"""Offline API 0.1 fixtures, with observed FITS preferred for frame requests."""

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
    Target,
)
from .catalog import resolve_name, targets
from .frame_rendering import NoCoverage
from .live_cutouts import cached_result, load_cutouts, workspace
from .observed_frames import matching_cutouts, render_cached
from .observed_science import measure
from shared.pipeline.irsa import UpstreamError, UpstreamTimeout

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


def require_fixture_mode():
    if os.getenv("DATA_MODE", "fixture") != "fixture":
        fail(500, "INTERNAL", "Unsupported data mode.")


def live_mode():
    return os.getenv("DATA_MODE", "live") == "live"


def archive_cutouts(query, directory):
    try:
        return load_cutouts(query, directory)
    except UpstreamTimeout:
        fail(504, "UPSTREAM_TIMEOUT", "IRSA did not respond before the deadline.")
    except UpstreamError:
        fail(502, "UPSTREAM_ERROR", "Unable to retrieve SPHEREx data from IRSA.")


def sample(filename):
    require_fixture_mode()
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
    result = (
        {"status": "ok", "mode": "live", "fixture_targets": [], "irsa_reachable": None}
        if live_mode() else sample("health.json")
    )
    result["git_sha"] = os.getenv("GIT_SHA", "unknown")
    return result


def resolve(query: ResolveQuery):
    result = resolve_name(query.name)
    if result is None:
        fail(404, "UNKNOWN_TARGET", "Name absent from fixture resolver.", {"name": query.name})
    return result


def frames(query: FramesQuery, response=None):
    requested_target = Target.model_validate(target(query))
    if live_mode():
        def build():
            with workspace() as directory:
                result, pngs = render(query, requested_target, archive_cutouts(query, directory))
                return result.model_dump(mode="json"), pngs

        (result, published), status = cached_result("frames", query, build)
        if response is not None:
            response.headers["X-Cache"] = status
    else:
        require_fixture_mode()
        cutouts = matching_cutouts(query)
        if cutouts is None:
            result, published = sample_frames(query, requested_target)
        else:
            result, published = render(query, requested_target, cutouts)
    with image_lock:
        for frame_id, content in published.items():
            images[frame_id] = content
            images.move_to_end(frame_id)
        while len(images) > 1200:
            images.popitem(last=False)
    return result


def render(query, requested_target, cutouts):
    try:
        return render_cached(query.model_dump_json(), requested_target.model_dump_json(), cutouts)
    except NoCoverage:
        fail(404, "NO_FRAMES", "No SPHEREx images cover this sky grid.",
             {"ra": query.ra, "dec": query.dec})


def sample_frames(query, requested_target):
    result = sample("frames_barnard_d6.json")
    result["target"] = requested_target
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
    return Frames.model_validate(result), published


def image(frame_id, difference):
    with image_lock:
        content = images.get(frame_id)
        if content is not None:
            images.move_to_end(frame_id)
    if content is None:
        fail(404, "FRAME_NOT_FOUND", "Call /api/frames first or reload the list.", {"id": frame_id})
    return content[difference]


def measured_science(query, operation, aperture_arcsec=None):
    if live_mode():
        requested_target = target(query)
        entry = targets().get(query.target_key)
        catalog = entry[0] if entry else {
            **requested_target, "epoch": "J2000", "pmra": 0.0, "pmdec": 0.0,
            "source": "request",
        }
        def build():
            with workspace() as directory:
                cutouts = archive_cutouts(query, directory)
                return measure(operation, cutouts, tuple(catalog.items()), query.detector, aperture_arcsec)

        result, _ = cached_result(operation, query, build)
        if entry is None and operation == "astrometry":
            result = {**result, "catalog_pm": {
                "pmra": None, "pmdec": None, "epoch": "unknown", "source": "unknown",
            }}
        return {**result, "target": requested_target}
    require_fixture_mode()
    requested_target = target(query)
    entry = targets().get(query.target_key)
    if entry is None:
        return None
    catalog, _ = entry
    cutouts = matching_cutouts(query)
    if cutouts is None:
        return None
    result = measure(operation, cutouts, tuple(catalog.items()), query.detector, aperture_arcsec)
    return {**result, "target": requested_target}


def photometry(query: PhotometryQuery):
    observed = measured_science(query, "photometry", query.aperture_arcsec)
    if observed is not None:
        return observed
    result = sample("photometry_rdra.json")
    if query.target_key != result["target"]["target_key"]:
        result.update(reference_star=None, points=[], variability=None)
    result["target"] = target(query)
    if query.detector is not None:
        result["points"] = [p for p in result["points"] if p["detector"] == query.detector]
    result["variability"] = None
    return result


def astrometry(query: ScienceQuery):
    observed = measured_science(query, "astrometry")
    if observed is not None:
        return observed
    result = sample("astrometry_barnard.json")
    if query.target_key != result["target"]["target_key"]:
        entry = targets().get(query.target_key)
        record = entry[0] if entry is not None else {}
        result.update(
            points=[],
            fit=None,
            catalog_pm={
                "pmra": record.get("pmra"),
                "pmdec": record.get("pmdec"),
                "epoch": record.get("epoch", "unknown"),
                "source": record.get("source", "unknown"),
            },
        )
    result["target"] = target(query)
    # The supplied astrometry sample contains D6 measurements only.
    if query.detector is not None and query.detector != 6:
        result["points"] = []
        result["fit"] = None
    return result
