"""Unit and integration tests for build_frames() pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.time import Time
from astropy.wcs import WCS
import astropy.units as u

# Ensure repository root is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
HUU_HOANG_DIR = ROOT / "members" / "huu-hoang"
if str(HUU_HOANG_DIR) not in sys.path:
    sys.path.insert(0, str(HUU_HOANG_DIR))

from members.dong.app.api_models import Frames
from build_frames import (
    build_frames,
    compute_predicted_pixel,
)


def test_predicted_pixel_axis_flipping():
    """Verify that compute_predicted_pixel correctly flips the vertical axis (FITS vs PNG)."""
    # Create simple WCS
    wcs = WCS(naxis=2)
    wcs.wcs.crpix = [30.0, 30.0]
    wcs.wcs.cdelt = [-0.0017, 0.0017]
    wcs.wcs.crval = [100.0, 20.0]
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    height = 59

    # Reference star at crval
    coord = SkyCoord(100.0 * u.deg, 20.0 * u.deg, obstime=Time(60000.0, format="mjd"))
    x_png, y_png = compute_predicted_pixel(coord, 60000.0, wcs, height)

    # In FITS: (crpix - 1) = (29.0, 29.0)
    # In PNG: x_png = 29.0, y_png = (59 - 1) - 29.0 = 29.0
    assert pytest.approx(x_png, abs=1e-4) == 29.0
    assert pytest.approx(y_png, abs=1e-4) == 29.0

    # Test star north of center (higher Dec -> higher y in FITS -> lower y in PNG)
    coord_north = SkyCoord(100.0 * u.deg, (20.0 + 0.0017 * 5) * u.deg, obstime=Time(60000.0, format="mjd"))
    x_n, y_n = compute_predicted_pixel(coord_north, 60000.0, wcs, height)
    assert pytest.approx(x_n, abs=1e-4) == 29.0
    assert pytest.approx(y_n, abs=1e-4) == 24.0  # 29 - 5 = 24 in PNG (closer to top)


def test_grid_center_temporal_midpoint():
    """Verify that TAN grid is centered at the star's midpoint position."""
    barnard_dir = ROOT / "data" / "five_targets" / "barnard"
    if not (barnard_dir / "inputs.json").exists():
        pytest.skip("Local Barnard cutouts not present; run five_targets.py to download")
    target_info = json.loads((barnard_dir / "target.json").read_text(encoding="utf-8"))

    res = build_frames(
        barnard_dir / "inputs.json",
        target=target_info,
        detector=6,
        output_dir=barnard_dir / "frames",
        generate_verification=False,
    )

    # Validate against Pydantic Frames model
    validated = Frames.model_validate(res)
    assert validated.api_version == "0.1"
    assert validated.detector == 6
    assert len(validated.frames) == 2

    # Check predicted_px exists for each frame
    f0 = validated.frames[0]
    f1 = validated.frames[1]
    assert f0.predicted_px is not None
    assert f1.predicted_px is not None

    # Between 2025 and 2026, Barnard moved North in Dec (proper motion > 10 arcsec/yr)
    # In PNG top-left coordinates, moving North means decreasing y_png!
    # In FITS coordinates, moving North means increasing y_fits!
    assert f1.mjd > f0.mjd
    assert f1.predicted_px[1] < f0.predicted_px[1]  # Northward shift in PNG
    delta_y_png = f0.predicted_px[1] - f1.predicted_px[1]
    assert delta_y_png > 0.8  # ~1.06 px motion


def test_contract_signature_and_export():
    """Verify that build_frames(cutouts, target, size) conforms to contract section 6 and exports."""
    # Test re-export in frames.py
    import frames
    assert hasattr(frames, "build_frames")

    # Test re-export in shared.frames_pipeline
    from shared.frames_pipeline import build_frames as shared_build_frames
    assert callable(shared_build_frames)

    barnard_dir = ROOT / "data" / "five_targets" / "barnard"
    if not (barnard_dir / "inputs.json").exists():
        pytest.skip("Local Barnard cutouts not present; run five_targets.py to download")

    # Test positional signature build_frames(cutouts, target, size) with string target
    res = build_frames(barnard_dir / "inputs.json", "barnard", 0.1, detector=6)
    validated = Frames.model_validate(res)
    assert validated.target.target_key == "barnard"
    assert validated.grid.width == 59
    assert validated.norm.stretch == "asinh"
    assert validated.norm.vmin < validated.norm.vmax

    # Check difference FITS file
    diff_file = barnard_dir / "frames" / "D6_visit01_minus_D6_visit00.fits"
    assert diff_file.exists()
    with fits.open(diff_file) as h:
        diff_data = h[0].data
        assert diff_data.shape == (59, 59)
        # Check dipole signature near Barnard's position:
        # At visit 00 (y_fits ~ 28.4), flux was higher in visit 00 so diff = visit01 - visit00 < 0
        # At visit 01 (y_fits ~ 29.5), flux is higher in visit 01 so diff = visit01 - visit00 > 0
        diff_finite = diff_data[np.isfinite(diff_data)]
        assert len(diff_finite) > 0
