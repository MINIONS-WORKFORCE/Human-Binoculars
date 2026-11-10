"""Offline API 0.1 fixtures. All example measurements and pixels are synthetic."""

import hashlib
import json
import os
from collections import OrderedDict
from pathlib import Path
from threading import RLock
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from .api_models import (
    Astrometry,
    ErrorResponse,
    Frames,
    FramesQuery,
    Health,
    Photometry,
    PhotometryQuery,
    Resolve,
    ResolveQuery,
    ScienceQuery,
)

ROOT = Path(__file__).resolve().parents[3]
SAMPLES = ROOT / "api_samples"
TARGETS = {
    "barnard": "Barnard's Star",
    "wise0855": "WISE 0855-0714",
    "epsindib": "Epsilon Indi B",
    "rwaur": "RW Aurigae",
    "rdra": "R Draconis",
}
router = APIRouter()
images = OrderedDict()
image_lock = RLock()
ERRORS = {code: {"model": ErrorResponse} for code in (400, 404, 500, 502, 503, 504)}


def fail(status, code, message, details=None):
    raise HTTPException(
        status,
        detail={
            "api_version": "0.1",
            "error": {"code": code, "message": message, "details": details or {}},
        },
    )


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


@router.get("/api/health", response_model=Health, responses=ERRORS)
def health():
    result = sample("health.json")
    result["git_sha"] = os.getenv("GIT_SHA", "unknown")
    return result


@router.get("/api/resolve", response_model=Resolve, responses=ERRORS)
def resolve(query: Annotated[ResolveQuery, Query()]):
    if query.name.strip().lower() not in {"barnard", "barnards star", "barnard's star"}:
        fail(404, "UNKNOWN_TARGET", "Name absent from fixture resolver.", {"name": query.name})
    result = sample("resolve_barnard.json")
    result["query"] = query.name
    return result


@router.get("/api/frames", response_model=Frames, responses=ERRORS)
def frames(query: Annotated[FramesQuery, Query()]):
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
    return Response(
        content[difference],
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=86400"},
    )


@router.get(
    "/api/frames/{id}.png",
    responses={200: {"content": {"image/png": {}}}, **ERRORS},
    response_class=Response,
)
def png(id: str):
    return image(id, 0)


@router.get(
    "/api/frames/{id}/diff.png",
    responses={200: {"content": {"image/png": {}}}, **ERRORS},
    response_class=Response,
)
def diff_png(id: str):
    return image(id, 1)


@router.get("/api/photometry", response_model=Photometry, responses=ERRORS)
def photometry(query: Annotated[PhotometryQuery, Query()]):
    result = sample("photometry_rdra.json")
    result["target"] = target(query)
    if query.detector is not None:
        result["points"] = [p for p in result["points"] if p["detector"] == query.detector]
    result["variability"] = None
    return result


@router.get("/api/astrometry", response_model=Astrometry, responses=ERRORS)
def astrometry(query: Annotated[ScienceQuery, Query()]):
    result = sample("astrometry_barnard.json")
    result["target"] = target(query)
    # The supplied astrometry sample contains D6 measurements only.
    if query.detector is not None and query.detector != 6:
        result["points"] = []
        result["fit"] = None
    return result
