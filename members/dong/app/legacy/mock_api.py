"""Deterministic mock API with real local SIA2 metadata and synthetic outputs."""

import hashlib
import json
import math
import os
import re
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import FileResponse
from PIL import Image, ImageDraw
from pydantic import Field

from .schemas import (
    ErrorResponse,
    FramesQuery,
    FramesResponse,
    JobStatus,
    LightcurveQuery,
    LightcurveResponse,
    Model,
    SkyQuery,
    Source,
    SpectrumResponse,
)

ERROR_RESPONSES = {422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}
ROOT = Path(__file__).resolve().parents[4]
router = APIRouter()
MOCK_WARNING = {
    "code": "MOCK_DATA",
    "message": "Real SIA2 source metadata; PNG pixels, wavelengths and fluxes are synthetic UI fixtures, not SPHEREx measurements.",
}
PACK_WARNING = {
    "code": "LOCAL_FIXTURE_PREVIEW",
    "message": (
        "PNGs use observed QR2 FITS pixels from a fixed local pack. "
        "The cutouts retain their original centres and orientations; "
        "they have not been registered to a common sky grid or quality masked."
    ),
}
NO_DATA_WARNING = {
    "code": "NO_DATA",
    "message": "No local mock fixture rows match the query; archive coverage has not been checked.",
}


class PackFrame(Model):
    frame_id: str = Field(pattern=r"^fixture-[a-f0-9]{24}$")
    target_ra_deg: float
    target_dec_deg: float
    cutout_size_deg: float
    source: Source


def data_dir() -> Path:
    return ROOT / os.environ.get("DATA_DIR", "data")


def rendered_dir() -> Path:
    return data_dir() / "fixture_pack_v1" / "rendered"


def processing_error():
    return HTTPException(
        500,
        detail={
            "error": {
                "code": "PROCESSING_ERROR",
                "message": "Mock metadata fixture is unavailable or invalid. Follow the backend README to generate it.",
                "fields": [],
            }
        },
    )


def load_sources() -> list[Source]:
    path = data_dir() / "wise0855_qr2_sources.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        sources = [Source.model_validate(row) for row in payload["sources"]]
        if not sources or len({s.obs_publisher_did for s in sources}) != len(sources):
            raise ValueError("Missing or duplicate sources")
        if any(s.t_min > s.t_max or s.obs_collection != "spherex_qr2" for s in sources):
            raise ValueError("Invalid source metadata")
        return sorted(sources, key=lambda s: (s.t_min, s.obs_publisher_did))
    except (OSError, ValueError, KeyError, TypeError):
        raise processing_error() from None


def is_legacy_wise_query(query: SkyQuery) -> bool:
    return (
        abs(query.s_ra - 133.79513) <= 1e-6
        and abs(query.s_dec + 7.24515) <= 1e-6
        and query.obs_collection == "spherex_qr2"
    )


def select_sources(query: SkyQuery):
    warnings = [MOCK_WARNING]
    if not is_legacy_wise_query(query):
        sources = []
        warnings.append(
            {
                "code": "MOCK_TARGET_ONLY",
                "message": "This fixture supports only WISE 0855 at RA 133.79513, Dec -7.24515 in spherex_qr2; this is not a live archive search.",
            }
        )
    else:
        sources = [
            s
            for s in load_sources()
            if (query.t_min is None or s.t_max >= query.t_min)
            and (query.t_max is None or s.t_min <= query.t_max)
            and (
                not hasattr(query, "energy_bandpassname")
                or s.energy_bandpassname == query.energy_bandpassname
            )
        ]
    if not sources:
        warnings.append(NO_DATA_WARNING)
    return sources, warnings


def frame_id(source: Source) -> str:
    return "mock-" + hashlib.sha256(source.obs_publisher_did.encode()).hexdigest()[:16]


def midpoint(source: Source) -> float:
    return (source.t_min + source.t_max) / 2


def describe_frame(source: Source, image_id: str):
    observation_time = datetime(1858, 11, 17, tzinfo=UTC) + timedelta(days=midpoint(source))
    return {
        "frame_id": image_id,
        "image_url": f"/mock/frames/{image_id}.png",
        "t_min": source.t_min,
        "t_max": source.t_max,
        "observation_time": observation_time.isoformat().replace("+00:00", "Z"),
        "energy_bandpassname": source.energy_bandpassname,
        "obs_collection": source.obs_collection,
        "n_images": 1,
        "source_obs_publisher_dids": [source.obs_publisher_did],
        "warnings": [],
    }


def select_pack_frames(index: Path, query: FramesQuery) -> list[PackFrame]:
    try:
        payload = json.loads(index.read_text(encoding="utf-8"))
        frames = [PackFrame.model_validate(row) for row in payload["frames"]]
    except (OSError, ValueError, KeyError, TypeError):
        raise processing_error() from None
    matches = [
        row
        for row in frames
        if abs(row.target_ra_deg - query.s_ra) <= 1e-6
        and abs(row.target_dec_deg - query.s_dec) <= 1e-6
        and abs(row.cutout_size_deg - query.cutout_size_deg) <= 1e-9
        and row.source.obs_collection == query.obs_collection
        and row.source.energy_bandpassname == query.energy_bandpassname
        and (query.t_min is None or row.source.t_max >= query.t_min)
        and (query.t_max is None or row.source.t_min <= query.t_max)
    ]
    return sorted(matches, key=lambda row: (row.source.t_min, row.frame_id))


@router.get(
    "/api/frames",
    response_model=FramesResponse,
    response_model_exclude_unset=True,
    responses={**ERROR_RESPONSES, 202: {"model": JobStatus}, 503: {"description": "Worker capacity reached"}},
)
def frames(query: Annotated[FramesQuery, Query()]):
    if os.getenv("FRAMES_MODE", "mock") == "pipeline":
        from .frame_jobs import submit

        return submit(query)
    index = rendered_dir() / "frames.json"
    if index.parent.parent.is_dir():
        matches = select_pack_frames(index, query)
        if any(not (index.parent / f"{row.frame_id}.png").is_file() for row in matches):
            raise processing_error()
        sources = list({row.source.obs_publisher_did: row.source for row in matches}.values())
        frame_list = [describe_frame(row.source, row.frame_id) for row in matches]
        warnings = [PACK_WARNING] if matches else [PACK_WARNING, NO_DATA_WARNING]
    else:
        sources, warnings = select_sources(query)
        frame_list = [describe_frame(source, frame_id(source)) for source in sources]
    return {
        "data_kind": "mock",
        "query": query.model_dump(exclude_none=True),
        "sources": [s.model_dump(exclude_none=True) for s in sources],
        "warnings": warnings,
        "frames": frame_list,
    }


MOCK_WAVELENGTHS = [0.9, 1.35, 2.0, 3.1, 4.1, 4.7]


@router.get(
    "/api/spectrum",
    response_model=SpectrumResponse,
    response_model_exclude_unset=True,
    responses=ERROR_RESPONSES,
)
def spectrum(query: Annotated[SkyQuery, Query()]):
    candidates, warnings = select_sources(query)
    # One source per detector, solely as provenance for the illustrative chart.
    by_band = {}
    for s in candidates:
        by_band.setdefault(s.energy_bandpassname, s)
    sources = [by_band[band] for band in sorted(by_band)]
    return {
        "data_kind": "mock",
        "query": query.model_dump(exclude_none=True),
        "sources": [s.model_dump(exclude_none=True) for s in sources],
        "warnings": warnings,
        "wavelength_unit": "um",
        "flux_unit": "mJy" if sources else None,
        "measurement_method": "synthetic_ui_fixture" if sources else None,
        "points": [
            {
                "wavelength_um": MOCK_WAVELENGTHS[int(s.energy_bandpassname[-1]) - 1],
                "flux": round(0.5 + int(s.energy_bandpassname[-1]) * 0.3, 3),
                "flux_error": 0.1,
                "energy_bandpassname": s.energy_bandpassname,
                "t_min": s.t_min,
                "t_max": s.t_max,
                "source_obs_publisher_dids": [s.obs_publisher_did],
                "warnings": [],
            }
            for s in sources
        ],
    }


@router.get(
    "/api/lightcurve",
    response_model=LightcurveResponse,
    response_model_exclude_unset=True,
    responses=ERROR_RESPONSES,
)
def lightcurve(query: Annotated[LightcurveQuery, Query()]):
    sources, warnings = select_sources(query)
    band_index = int(query.energy_bandpassname[-1]) - 1
    wavelength = MOCK_WAVELENGTHS[band_index]
    return {
        "data_kind": "mock",
        "query": query.model_dump(exclude_none=True),
        "sources": [s.model_dump(exclude_none=True) for s in sources],
        "warnings": warnings,
        "time_unit": "MJD day",
        "flux_unit": "mJy" if sources else None,
        "measurement_method": "synthetic_ui_fixture" if sources else None,
        "wavelength_min_um": wavelength - 0.02 if sources else None,
        "wavelength_max_um": wavelength + 0.02 if sources else None,
        "points": [
            {
                "time_mjd": midpoint(s),
                "t_min": s.t_min,
                "t_max": s.t_max,
                "flux": round(1.0 + 0.2 * math.sin(midpoint(s)), 4),
                "flux_error": 0.1,
                "source_obs_publisher_dids": [s.obs_publisher_did],
                "warnings": [],
            }
            for s in sources
        ],
    }


@router.get("/mock/frames/{image_id}.png", include_in_schema=False)
def mock_image(image_id: str):
    if image_id.startswith("fixture-"):
        if re.fullmatch(r"fixture-[a-f0-9]{24}", image_id):
            path = rendered_dir() / f"{image_id}.png"
            if path.is_file():
                return FileResponse(path, media_type="image/png")
        raise HTTPException(404, detail="Mock frame not found")
    sources = load_sources()
    source = next((s for s in sources if frame_id(s) == image_id), None)
    if source is None:
        raise HTTPException(404, detail="Mock frame not found")
    image = Image.new("RGB", (384, 384), "#080b18")
    draw = ImageDraw.Draw(image)
    for index in range(35):
        x, y = (index * 83 + 23) % 360 + 12, (index * 137 + 41) % 280 + 60
        draw.ellipse((x - 1, y - 1, x + 1, y + 1), fill="#b3bfdc")
    x = 70 + int(midpoint(source) * 7) % 240
    draw.ellipse((x - 4, 187, x + 4, 195), fill="#ffdc65")
    draw.text((12, 12), "MOCK - SYNTHETIC PIXELS", fill="white")
    draw.text((12, 30), "NOT A SPHEREx IMAGE / NOT TO SCALE", fill="white")
    draw.text((12, 355), f"{source.energy_bandpassname}  MJD {midpoint(source):.5f}", fill="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return Response(buffer.getvalue(), media_type="image/png")
