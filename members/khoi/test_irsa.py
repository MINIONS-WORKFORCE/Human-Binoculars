"""Unit tests for Khôi's IRSA data pipeline module (shared/pipeline/irsa.py).
Run with: pytest members/khoi/test_irsa.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import pytest

from shared.pipeline.irsa import (
    _normalize_detector,
    find_images,
    fetch_cutouts,
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


def test_manifest_structure(tmp_path):
    mock_images = [
        {
            "obs_id": "2025W33_test_1",
            "obs_publisher_did": "ivo://spx/test1",
            "obs_collection": "spherex_qr2",
            "energy_bandpassname": "SPHEREx-D6",
            "s_ra": 269.45,
            "s_dec": 4.76,
            "t_min": 60902.8,
            "t_max": 60902.9,
            "access_url": "https://irsa.ipac.caltech.edu/test.fits",
        }
    ]
    # Verify group logic works
    visits = group_images_into_visits(mock_images)
    assert len(visits) == 1
