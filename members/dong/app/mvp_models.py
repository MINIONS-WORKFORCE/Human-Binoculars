"""Wire models for the MVP v1 contract described in the SRS."""

from typing import Literal

from pydantic import Field, model_validator

from .legacy.schemas import (
    Frame,
    FramesQuery,
    Model,
    Source,
    WarningMessage,
)


class MVPQuery(FramesQuery):
    obs_collection: Literal["spherex_dr1", "spherex_qr2", "spherex_qr3"]


class MVPTarget(Model):
    id: str
    name: str
    object_type: str
    ra_deg: float
    dec_deg: float
    epoch_jyear: float
    default_detector: int = Field(ge=1, le=6)
    default_fov_arcmin: float = Field(gt=0, le=12)


class Grid(Model):
    projection: Literal["TAN"]
    center_ra_deg: float
    center_dec_deg: float
    pixel_scale_arcsec: float = Field(gt=0)
    width_px: int = Field(gt=0)
    height_px: int = Field(gt=0)


class Display(Model):
    stretch: Literal["asinh"]
    vmin: float
    vmax: float
    unit: Literal["MJy/sr"]


class MVPSource(Source):
    # The TAP fallback can omit these source-image fields.
    s_ra: float | None = None
    s_dec: float | None = None
    access_format: str | None = None


class MVPFrame(Frame):
    visit_index: int = Field(ge=0)
    visit_label: str


class DifferenceFrame(Model):
    frame_id: str
    image_url: str
    later_frame_id: str
    earlier_frame_id: str
    warnings: list[WarningMessage]


class MVPFrames(Model):
    data_kind: Literal["mock", "observational"]
    query: MVPQuery
    grid: Grid
    display: Display | None
    frames: list[MVPFrame]
    difference_frames: list[DifferenceFrame] = Field(default_factory=list)
    sources: list[MVPSource]
    warnings: list[WarningMessage]

    @model_validator(mode="after")
    def check_provenance(self):
        if self.frames and self.display is None:
            raise ValueError("Rendered frames require a display scale")
        if self.display and self.display.vmax <= self.display.vmin:
            raise ValueError("Invalid display range")
        if any(a.t_min > b.t_min for a, b in zip(self.frames, self.frames[1:])):
            raise ValueError("Frames must be ordered by visit time")
        dids = {source.obs_publisher_did for source in self.sources}
        for frame in self.frames:
            ids = set(frame.source_obs_publisher_dids)
            if (
                frame.obs_collection != self.query.obs_collection
                or frame.energy_bandpassname != self.query.energy_bandpassname
                or frame.t_min > frame.t_max
                or frame.n_images != len(ids)
                or not ids <= dids
            ):
                raise ValueError("Frame provenance must match the query and its source records")
            if self.data_kind == "observational" and not ids:
                raise ValueError("An observed frame requires at least one contributing product")
        return self
