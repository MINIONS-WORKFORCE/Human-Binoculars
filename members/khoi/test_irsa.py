"""Unit tests for Khôi's IRSA data pipeline module (shared/pipeline/irsa.py).
Fulfills Issue #21 test requirements:
- Offline fixture mode execution without network.
- 5 targets verification (>= 3 frames each).
- Detector filtering (D6 vs D1).
- Manifest structure and FITS integrity.

Run with: pytest members/khoi/test_irsa.py -v
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from shared.pipeline.irsa import (
    _normalize_detector,
    find_images,
    fetch_cutouts,
    find_frames,
    make_cutout_url,
    group_images_into_visits,
)


def test_normalize_detector():
    assert _normalize_detector("1") == "SPHEREx-D1"
    assert _normalize_detector("D6") == "SPHEREx-D6"
    assert _normalize_detector("d3") == "SPHEREx-D3"
    assert _normalize_detector("SPHEREx-D2") == "SPHEREx-D2"
    assert _normalize_detector("spherex-d5") == "SPHEREx-D5"
    assert _normalize_detector(None) is None


def test_make_cutout_url():
    base = "https://irsa.ipac.caltech.edu/ibe/data/test.fits"
    url = make_cutout_url(base, 133.795, -7.245, 0.05)
    assert "center=133.79500000,-7.24500000d" in url
    assert "size=0.050000" in url


def test_group_images_into_visits():
    imgs = [
        {"t_min": 60800.0, "obs_id": "1"},
        {"t_min": 60805.0, "obs_id": "2"},
        {"t_min": 60900.0, "obs_id": "3"},
        {"t_min": 60910.0, "obs_id": "4"},
    ]
    visits = group_images_into_visits(imgs, gap_days=30.0)
    assert len(visits) == 2
    assert len(visits[0]) == 2
    assert len(visits[1]) == 2


@pytest.mark.parametrize("target_key", ["barnard", "wise0855", "epsindib", "rwaur", "rdra"])
def test_find_frames_five_targets_offline(target_key: str):
    """Verify that find_frames in fixture mode works 100% offline and returns >= 3 frames for each target."""
    with patch("requests.get", side_effect=RuntimeError("Network access forbidden in fixture mode")):
        frames = find_frames(target_key=target_key, mode="fixture")
        assert len(frames) >= 3, f"Expected >= 3 frames for {target_key}, got {len(frames)}"

        # Check required fields in each frame
        for f in frames:
            assert f["target_key"] == target_key
            assert f["detector"] in ("SPHEREx-D6", "SPHEREx-D1")
            assert "obs_id" in f
            assert "mjd" in f
            assert "fits_path" in f
            assert "sha256" in f

            fits_path = Path(f["fits_path"])
            assert fits_path.exists(), f"FITS file does not exist: {fits_path}"
            assert fits_path.stat().st_size > 10000, f"FITS file too small: {fits_path}"
            # Verify valid FITS magic bytes
            with open(fits_path, "rb") as fp:
                assert fp.read(8) == b"SIMPLE  "


def test_find_frames_detector_filtering():
    """Verify detector filtering for SPHEREx-D6 and SPHEREx-D1."""
    with patch("requests.get", side_effect=RuntimeError("Network access forbidden in fixture mode")):
        d6_frames = find_frames(target_key="barnard", detector="D6", mode="fixture")
        assert len(d6_frames) >= 3
        assert all(f["detector"] == "SPHEREx-D6" for f in d6_frames)

        d1_frames = find_frames(target_key="barnard", detector="SPHEREx-D1", mode="fixture")
        assert len(d1_frames) >= 3
        assert all(f["detector"] == "SPHEREx-D1" for f in d1_frames)


def test_find_frames_query_dict_and_coords():
    """Verify query dict and coordinate matching."""
    with patch("requests.get", side_effect=RuntimeError("Network access forbidden in fixture mode")):
        # Query dict format matching Section 5 contract
        q = {"target_key": "wise0855", "energy_bandpassname": "SPHEREx-D6"}
        frames = find_frames(q, mode="fixture")
        assert len(frames) >= 3
        assert all(f["target_key"] == "wise0855" for f in frames)

        # Spatial lookup near Barnard (RA=269.446, Dec=4.767)
        spatial_frames = find_frames(ra_deg=269.446, dec_deg=4.767, mode="fixture")
        assert len(spatial_frames) >= 3
        assert any(f["target_key"] == "barnard" for f in spatial_frames)


def test_fixtures_manifest_integrity():
    """Verify manifest.json contains all 5 targets and valid schema."""
    manifest_path = ROOT_DIR / "members" / "khoi" / "fixtures_manifest.json"
    assert manifest_path.exists()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))

    assert data["total_targets"] == 5
    assert data["total_frames"] >= 15
    for key in ["barnard", "wise0855", "epsindib", "rwaur", "rdra"]:
        assert key in data["targets_summary"]
        assert data["targets_summary"][key]["total"] >= 3


def test_download_cutout_mock(tmp_path):
    """Verify download_cutout creates valid file and validates FITS header."""
    from shared.pipeline.irsa import download_cutout
    from unittest.mock import MagicMock

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b"SIMPLE  =                    T / standard FITS" + b" " * 2800

    dest = tmp_path / "test_cutout.fits"
    with patch("requests.get", return_value=mock_resp):
        res = download_cutout(
            "https://irsa.ipac.caltech.edu/test.fits",
            10.0,
            20.0,
            0.05,
            dest,
        )
        assert res.exists()
        assert res.read_bytes().startswith(b"SIMPLE  =")


def test_verify_fixtures_script():
    """Verify scripts/download_fixtures.py verify_fixtures() passes on current fixtures."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("download_fixtures", ROOT_DIR / "scripts" / "download_fixtures.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.verify_fixtures(ROOT_DIR / "data" / "fixtures") is True
