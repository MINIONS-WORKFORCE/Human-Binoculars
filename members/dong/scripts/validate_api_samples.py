"""Validate committed API samples against the same models used by FastAPI."""

import sys
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.api_models import Astrometry, ErrorResponse, Frames, Health, Photometry, Resolve

SAMPLES = Path(__file__).resolve().parents[3] / "api_samples"
MODELS = {
    "health.json": Health,
    "resolve_barnard.json": Resolve,
    "frames_barnard_d6.json": Frames,
    "photometry_rdra.json": Photometry,
    "astrometry_barnard.json": Astrometry,
    "error_no_frames.json": ErrorResponse,
}


def validate():
    for filename, model in MODELS.items():
        model.model_validate_json((SAMPLES / filename).read_text(encoding="utf-8"))
    frames = Frames.model_validate_json((SAMPLES / "frames_barnard_d6.json").read_text())
    for index, frame in enumerate(frames.frames):
        for suffix in ("", "_diff"):
            with Image.open(SAMPLES / f"png/frame-{index}{suffix}.png") as image:
                if image.mode != "L" or image.size != (frames.grid.width, frames.grid.height):
                    raise ValueError("Sample PNG format or dimensions disagree with grid")
        if frame.predicted_px is not None:
            x, y = frame.predicted_px
            with Image.open(SAMPLES / f"png/frame-{index}.png") as image:
                if image.getpixel((round(x), round(y))) < 200:
                    raise ValueError("Sample predicted pixel does not lie on the source")
    print(f"Validated {len(MODELS)} API samples")


if __name__ == "__main__":
    validate()
