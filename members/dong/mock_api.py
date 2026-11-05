"""Deterministic mock API with real local SIA2 metadata and synthetic outputs."""

import hashlib
import json
import math
import os
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Response
from PIL import Image, ImageDraw
from pydantic import BaseModel, ConfigDict, Field, model_validator

Collection = Literal["spherex_qr2", "spherex_qr2_deep", "spherex_qr3", "spherex_qr3_deep"]
Band = Literal["SPHEREx-D1", "SPHEREx-D2", "SPHEREx-D3", "SPHEREx-D4", "SPHEREx-D5", "SPHEREx-D6"]
ROOT = Path(__file__).resolve().parents[2]
router = APIRouter()
MOCK_WARNING = {
    "code": "MOCK_DATA",
    "message": "Real SIA2 source metadata; PNG pixels, wavelengths and fluxes are synthetic UI fixtures, not SPHEREx measurements.",
}


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SkyQuery(Model):
    s_ra: float = Field(ge=0, lt=360)
    s_dec: float = Field(ge=-90, le=90)
    obs_collection: Collection
    t_min: float | None = None
    t_max: float | None = None

    @model_validator(mode="after")
    def ordered_times(self):
        if self.t_min is not None and self.t_max is not None and self.t_min > self.t_max:
            raise ValueError("t_min must be less than or equal to t_max")
        return self


class FramesQuery(SkyQuery):
    energy_bandpassname: Band
    cutout_size_deg: float = Field(gt=0, le=0.2)


class LightcurveQuery(SkyQuery):
    energy_bandpassname: Band


class WarningMessage(Model):
    code: str
    message: str


class ErrorDetail(Model):
    code: str
    message: str
    fields: list[str]


class ErrorResponse(Model):
    error: ErrorDetail


ERROR_RESPONSES = {422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}}


class Source(Model):
    obs_id: str
    obs_publisher_did: str
    obs_collection: Collection
    energy_bandpassname: Band
    s_ra: float
    s_dec: float
    t_min: float
    t_max: float
    access_url: str
    access_format: str
    s_region: str | None = None
    s_fov: float | None = None
    em_min: float | None = None
    em_max: float | None = None


class Frame(Model):
    frame_id: str
    image_url: str
    t_min: float
    t_max: float
    observation_time: str
    energy_bandpassname: Band
    obs_collection: Collection
    n_images: int
    source_obs_publisher_dids: list[str]
    warnings: list[WarningMessage]


class SpectrumPoint(Model):
    wavelength_um: float
    flux: float | None
    flux_error: float | None
    energy_bandpassname: Band
    t_min: float
    t_max: float
    source_obs_publisher_dids: list[str]
    warnings: list[WarningMessage]


class LightcurvePoint(Model):
    time_mjd: float
    t_min: float
    t_max: float
    flux: float | None
    flux_error: float | None
    source_obs_publisher_dids: list[str]
    warnings: list[WarningMessage]


class CommonResponse(Model):
    data_kind: Literal["mock"] = "mock"
    sources: list[Source]
    warnings: list[WarningMessage]


class FramesResponse(CommonResponse):
    query: FramesQuery
    frames: list[Frame]


class SpectrumResponse(CommonResponse):
    query: SkyQuery
    wavelength_unit: Literal["um"] = "um"
    flux_unit: str | None
    measurement_method: str | None
    points: list[SpectrumPoint]


class LightcurveResponse(CommonResponse):
    query: LightcurveQuery
    time_unit: Literal["MJD day"] = "MJD day"
    flux_unit: str | None
    measurement_method: str | None
    wavelength_min_um: float | None
    wavelength_max_um: float | None
    points: list[LightcurvePoint]


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
    path = ROOT / os.environ.get("DATA_DIR", "data") / "wise0855_qr2_sources.json"
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


def select_sources(query: SkyQuery):
    warnings = [MOCK_WARNING]
    if (
        abs(query.s_ra - 133.79513) > 1e-6
        or abs(query.s_dec + 7.24515) > 1e-6
        or query.obs_collection != "spherex_qr2"
    ):
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
        warnings.append(
            {
                "code": "NO_DATA",
                "message": "No local mock fixture rows match the query; archive coverage has not been checked.",
            }
        )
    return sources, warnings


def frame_id(source: Source) -> str:
    return "mock-" + hashlib.sha256(source.obs_publisher_did.encode()).hexdigest()[:16]


def midpoint(source: Source) -> float:
    return (source.t_min + source.t_max) / 2


@router.get(
    "/api/frames",
    response_model=FramesResponse,
    response_model_exclude_unset=True,
    responses=ERROR_RESPONSES,
)
def frames(query: Annotated[FramesQuery, Query()]):
    sources, warnings = select_sources(query)
    return {
        "data_kind": "mock",
        "query": query.model_dump(exclude_none=True),
        "sources": [s.model_dump(exclude_none=True) for s in sources],
        "warnings": warnings,
        "frames": [
            {
                "frame_id": frame_id(s),
                "image_url": f"/mock/frames/{frame_id(s)}.png",
                "t_min": s.t_min,
                "t_max": s.t_max,
                "observation_time": (
                    datetime(1858, 11, 17, tzinfo=UTC) + timedelta(days=midpoint(s))
                )
                .isoformat()
                .replace("+00:00", "Z"),
                "energy_bandpassname": s.energy_bandpassname,
                "obs_collection": s.obs_collection,
                "n_images": 1,
                "source_obs_publisher_dids": [s.obs_publisher_did],
                "warnings": [],
            }
            for s in sources
        ],
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
