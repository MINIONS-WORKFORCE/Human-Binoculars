"""Request and response models for the backend API."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Collection = Literal["spherex_qr2", "spherex_qr2_deep", "spherex_qr3", "spherex_qr3_deep"]
Band = Literal["SPHEREx-D1", "SPHEREx-D2", "SPHEREx-D3", "SPHEREx-D4", "SPHEREx-D5", "SPHEREx-D6"]


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
    data_kind: Literal["mock", "observational"] = "mock"
    query: FramesQuery
    frames: list[Frame]


class JobStatus(Model):
    job_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    status_url: str
    result: FramesResponse | None = None
    error: dict[str, str] | None = None


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
