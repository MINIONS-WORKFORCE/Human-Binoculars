"""API 0.1 models matching the team's The-API-contract wiki, Issue #14."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

RA = Annotated[float, Field(ge=0, lt=360)]
Dec = Annotated[float, Field(ge=-90, le=90)]
Detector = Annotated[int, Field(ge=1, le=6)]
Pixel = tuple[float, float]


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Versioned(Model):
    api_version: Literal["0.1"] = "0.1"


class Health(Versioned):
    status: Literal["ok", "degraded"]
    mode: Literal["fixture", "live"]
    fixture_targets: list[str]
    irsa_reachable: bool | None
    git_sha: str


class ResolveQuery(Model):
    name: str = Field(min_length=1, max_length=200)


class Resolve(Versioned):
    query: str
    target_key: str
    name: str
    ra: RA
    dec: Dec
    epoch: str
    pmra: float | None
    pmdec: float | None
    parallax_mas: float | None = Field(ge=0)
    kind: Literal["high_pm", "variable", "other"]
    source: Literal["targets_table", "simbad"]


class SkyQuery(Model):
    ra: RA
    dec: Dec
    target_key: str | None = Field(default=None, max_length=80)


class FramesQuery(SkyQuery):
    detector: Detector = 6
    size: float = Field(default=0.1, ge=0.02, le=0.3)
    max_frames: int = Field(default=60, ge=1, le=200)


class ScienceQuery(SkyQuery):
    detector: Detector | None = None


class PhotometryQuery(ScienceQuery):
    aperture_arcsec: float = Field(default=12.3, gt=0)


class Target(Model):
    ra: RA
    dec: Dec
    name: str | None
    target_key: str | None


class Grid(Model):
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    pixscale_arcsec: float = Field(gt=0)
    projection: Literal["TAN"]
    center_ra: RA
    center_dec: Dec


class Norm(Model):
    vmin: float
    vmax: float
    stretch: Literal["asinh"]

    @model_validator(mode="after")
    def ordered(self):
        if self.vmin >= self.vmax:
            raise ValueError("vmin must be less than vmax")
        return self


class Frame(Model):
    id: str
    mjd: float
    iso: str
    wavelength_um: float = Field(gt=0)
    bandwidth_um: float = Field(gt=0)
    release: str
    survey: int
    bad_pixel_frac: float = Field(ge=0, le=1)
    predicted_px: Pixel | None
    png: str
    diff_png: str


class Frames(Versioned):
    target: Target
    detector: Detector
    grid: Grid
    norm: Norm
    reference_frame_id: str | None
    frames: list[Frame]
    warnings: list[Literal["SATURATION_POSSIBLE", "FEW_FRAMES", "TRUNCATED", "MIXED_WAVELENGTH", "TARGET_OUTSIDE_COVERAGE"]]

    @model_validator(mode="after")
    def references(self):
        ids = [frame.id for frame in self.frames]
        if len(ids) != len(set(ids)) or ids != [
            f.id for f in sorted(self.frames, key=lambda f: f.mjd)
        ]:
            raise ValueError("Frames must have unique IDs in chronological order")
        if self.reference_frame_id is not None and self.reference_frame_id not in ids:
            raise ValueError("Reference frame is absent")
        return self


class ReferenceStar(Model):
    gaia_source_id: str
    ra: RA
    dec: Dec


class PhotometryPoint(Model):
    frame_id: str
    mjd: float
    wavelength_um: float = Field(gt=0)
    detector: Detector
    release: str
    survey: int
    flux_mjy: float | None
    err_mjy: float | None = Field(ge=0)
    snr: float | None
    detected: bool
    flagged: bool
    is_reference_star: bool


class Variability(Model):
    chi2_reduced: float = Field(ge=0)
    dof: int = Field(gt=0)
    is_variable: bool
    method: str


class Photometry(Versioned):
    target: Target
    reference_star: ReferenceStar | None
    points: list[PhotometryPoint]
    variability: Variability | None
    warnings: list[str] = []


class Position(Model):
    ra: RA
    dec: Dec


class Measurement(Position):
    err_arcsec: float = Field(ge=0)


class AstrometryPoint(Model):
    frame_id: str
    mjd: float
    measured: Measurement | None
    predicted: Position | None
    offset_arcsec: float | None = Field(ge=0)
    residual_ra_mas: float | None = None
    residual_dec_mas: float | None = None
    measured_px: Pixel | None


class CatalogPM(Model):
    pmra: float | None
    pmdec: float | None
    source: str
    epoch: str


class MotionFit(Model):
    pmra: float
    pmdec: float
    pmra_err: float = Field(ge=0)
    pmdec_err: float = Field(ge=0)
    n_points: int = Field(ge=3)
    baseline_days: float = Field(ge=30)


class Astrometry(Versioned):
    target: Target
    catalog_pm: CatalogPM
    points: list[AstrometryPoint]
    fit: MotionFit | None
    warnings: list[str] = []


class ErrorDetail(Model):
    code: str
    message: str
    details: dict


class ErrorResponse(Versioned):
    error: ErrorDetail
