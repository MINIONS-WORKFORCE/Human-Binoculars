"""Task D: cached real cutouts to verified PNG and difference products.

Runtime is not the student's independent from-scratch rebuild time.
"""

import json
import time

import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
from five_targets import BASE
from frames import make_frames
from tan_pipeline import ROOT

OUT = ROOT / "data" / "tasks_def"


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, allow_nan=False), encoding="utf-8")


def stage_d():
    """Fresh product directory; this is a runtime benchmark, not a fresh-code drill."""
    results = []
    for target in ("wise-0855", "barnard"):
        folder = BASE / target
        info = json.loads((folder / "target.json").read_text())
        start = time.perf_counter()
        reports = [
            make_frames(
                info["ra_deg"],
                info["dec_deg"],
                0.1,
                det,
                manifest=folder / "inputs.json",
                output=OUT / "D" / target,
            )
            for det in (1, 3, 6)
        ]
        checks = []
        for report in reports:
            previous = None
            for frame in report["frames"]:
                path = OUT / "D" / target / (frame["label"] + ".fits")
                with fits.open(path) as h:
                    image = h["MEDIAN"].data.copy()
                    assert np.array_equal(h["NVALID"].data == 0, ~np.isfinite(image))
                    np.testing.assert_allclose(
                        WCS(h["MEDIAN"].header).world_to_pixel(
                            SkyCoord(info["ra_deg"], info["dec_deg"], unit="deg")
                        ),
                        [29, 29],
                        atol=1e-7,
                    )
                assert path.with_suffix(".png").is_file()
                if previous is not None:
                    label, old = previous
                    diff = path.with_name(f"{frame['label']}_minus_{label}.fits")
                    with fits.open(diff) as h:
                        np.testing.assert_allclose(
                            h[0].data, image - old, atol=1e-4, rtol=1e-5, equal_nan=True
                        )
                    assert diff.with_suffix(".png").is_file()
                previous = frame["label"], image
                checks.append(frame["label"])
        results.append(
            {
                "target": target,
                "runtime_seconds": time.perf_counter() - start,
                "median_frames": len(checks),
                "difference_frames": sum(len(r["frames"]) - 1 for r in reports),
                "product_checks": "pass",
            }
        )
    save(
        OUT / "D" / "report.json",
        {
            "results": results,
            "scope": "Local cached FITS to saved FITS/PNG, including read/render/verification; no download",
            "human_rebuild_under_90_minutes": "not_measured",
            "cross_teaching": "pending teammates; demo is not attendance evidence",
        },
    )


if __name__ == "__main__":
    stage_d()
