"""End-to-end fixture-mode checks for E3, E4 and E5."""

import hashlib
import io
import json
from pathlib import Path

import numpy as np
import pytest
import requests
from app.api_models import ErrorResponse, Frames, FramesQuery
from app.main import app
from app.services import observed_frames
from app.services.fixtures import image_lock, images
from astropy.io import fits
from astropy.wcs import WCS
from fastapi.testclient import TestClient
from PIL import Image

QUERY = {
    "ra": 269.44636864652,
    "dec": 4.766880108377093,
    "detector": 6,
    "size": 0.05,
    "target_key": "barnard",
}
ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def client(monkeypatch, tmp_path):
    def reject_network(*args, **kwargs):
        pytest.fail("Fixture mode made a network request")

    monkeypatch.setattr(requests.sessions.Session, "request", reject_network)
    monkeypatch.setenv("DATA_MODE", "fixture")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    observed_frames.render_cached.cache_clear()
    with image_lock:
        images.clear()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture
def manifest(tmp_path):
    """Three generated FITS exposures over two visits, with real WCS and FLAGS."""
    fixture_dir = tmp_path / "fixtures"
    fixture_dir.mkdir()
    shape = (31, 31)
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [QUERY["ra"], QUERY["dec"]]
    wcs.wcs.crpix = [16, 16]
    wcs.wcs.cdelt = [-6.15 / 3600, 6.15 / 3600]
    y, x = np.indices(shape)
    entries = []
    for index, mjd in enumerate([60900, 60901, 61000]):
        obs_id = f"test-{index}"
        path = fixture_dir / f"{obs_id}.fits"
        header = wcs.to_header()
        header.update(
            {
                "BUNIT": "MJy/sr",
                "OBSID": obs_id,
                "DETECTOR": 6,
                "DATE-OBS": "2025-08-15",
                "WCSAXESW": 2,
                "CTYPE1W": "LINEAR",
                "CTYPE2W": "LINEAR",
                "CRPIX1W": 1.0,
                "CRPIX2W": 1.0,
                "CRVAL1W": 4.8,
                "CRVAL2W": 0.037,
                "CDELT1W": 0.001,
                "CDELT2W": 0.00001,
            }
        )
        source_y = 18 if index == 2 else 12
        pixels = 1 + 20 * np.exp(-((x - 15) ** 2 + (y - source_y) ** 2) / 4)
        flags = fits.ImageHDU(np.zeros(shape, dtype=np.int32), name="FLAGS")
        flags.header["MP_BAD"] = 0
        flags.data[0, 0] = 1
        fits.HDUList(
            [
                fits.PrimaryHDU(),
                fits.ImageHDU(pixels, header=header, name="IMAGE"),
                flags,
            ]
        ).writeto(path)
        entries.append(
            {
                "target_key": QUERY["target_key"],
                "obs_id": obs_id,
                "obs_publisher_did": f"ivo://irsa.ipac/spherex_qr2?{obs_id}/D6",
                "detector": "D6",
                "ra": QUERY["ra"],
                "dec": QUERY["dec"],
                "mjd": mjd,
                "fits_path": str(path),
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
        )
    manifest = fixture_dir / "manifest.json"
    manifest.write_text(json.dumps({"entries": entries}), encoding="utf-8")
    return manifest


def read_png(client, url):
    response = client.get(url)
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    image = Image.open(io.BytesIO(response.content))
    assert image.mode == "L"
    return np.asarray(image)


def test_frames_render_and_publish_both_pngs_from_cache(client, manifest):
    query = {key: value for key, value in QUERY.items() if key != "target_key"}
    response = client.get("/api/frames", params=query)
    assert response.status_code == 200, response.text
    result = Frames.model_validate(response.json())
    assert result.grid.width == result.grid.height == 31
    assert result.grid.center_ra == QUERY["ra"]
    first, second = result.frames
    assert first.id.startswith("observed-")
    assert [first.mjd, second.mjd] == [60900.5, 61000]
    assert first.wavelength_um == pytest.approx(4.815)
    assert first.release == "qr2"
    assert first.bad_pixel_frac == pytest.approx(1 / (31 * 31))
    assert first.predicted_px is None
    assert result.reference_frame_id == first.id

    assert read_png(client, first.png).shape == (31, 31)
    assert (read_png(client, first.diff_png) == 128).all()
    diff = read_png(client, second.diff_png)
    assert diff[12, 15] > 128 > diff[18, 15]
    assert observed_frames.render_cached.cache_info().misses == 1

    # Repeating E3 republishes PNGs even after the serving registry is cleared.
    with image_lock:
        images.clear()
    assert client.get("/api/frames", params=query).json() == response.json()
    assert observed_frames.render_cached.cache_info().hits == 1
    np.testing.assert_array_equal(read_png(client, second.diff_png), diff)

    limited = client.get("/api/frames", params={**query, "max_frames": 1})
    one_frame = Frames.model_validate(limited.json())
    assert len(one_frame.frames) == 1
    assert set(one_frame.warnings) == {"FEW_FRAMES", "TRUNCATED"}
    assert one_frame.frames[0].id != first.id


def test_changed_fixture_cannot_reuse_cached_frames(client, manifest):
    assert client.get("/api/frames", params=QUERY).status_code == 200
    entry = json.loads(manifest.read_text(encoding="utf-8"))["entries"][0]
    Path(entry["fits_path"]).write_bytes(b"corrupted after cache publication")
    response = client.get("/api/frames", params=QUERY)
    assert response.status_code == 500
    assert ErrorResponse.model_validate(response.json()).error.code == "INTERNAL"


def test_live_reload_reuses_cached_frames_and_pngs(client, manifest, monkeypatch):
    from app.services import fixtures

    cutouts = observed_frames.matching_cutouts(FramesQuery(**QUERY))
    monkeypatch.setenv("DATA_MODE", "live")
    calls = []

    def download(query, directory):
        calls.append(query)
        return cutouts

    monkeypatch.setattr(fixtures, "load_cutouts", download)
    first = client.get("/api/frames", params=QUERY)
    assert first.status_code == 200, first.text
    assert first.headers["X-Cache"] == "MISS"
    png = first.json()["frames"][0]["png"]
    expected = client.get(png).content
    with image_lock:
        images.clear()

    second = client.get("/api/frames", params=QUERY)
    assert second.headers["X-Cache"] == "HIT"
    assert second.json() == first.json()
    assert client.get(png).content == expected
    assert len(calls) == 1
    assert client.get("/api/frames", params={**QUERY, "size": 0.06}).headers["X-Cache"] == "MISS"


def test_frames_accept_dr1_alongside_quick_release(client, manifest):
    index = json.loads(manifest.read_text(encoding="utf-8"))
    entry = index["entries"][-1]
    entry["obs_publisher_did"] = entry["obs_publisher_did"].replace("spherex_qr2", "spherex_dr1")
    manifest.write_text(json.dumps(index), encoding="utf-8")

    response = client.get("/api/frames", params=QUERY)
    assert response.status_code == 200, response.text
    result = Frames.model_validate(response.json())
    assert [frame.release for frame in result.frames] == ["qr2", "dr1"]


def test_partial_visit_missing_target_is_omitted(client, manifest):
    index = json.loads(manifest.read_text(encoding="utf-8"))
    for entry in index["entries"][:2]:
        path = Path(entry["fits_path"])
        with fits.open(path, mode="update") as hdus:
            # The image still overlaps the output grid, but its target is outside.
            hdus["IMAGE"].header["CRPIX2"] = -4.0
        entry["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(index), encoding="utf-8")
    response = client.get("/api/frames", params=QUERY)
    assert response.status_code == 200, response.text
    result = Frames.model_validate(response.json())
    assert [frame.mjd for frame in result.frames] == [61000]
    assert "TARGET_OUTSIDE_COVERAGE" in result.warnings


def test_cutouts_removed_by_detector_filter_return_empty_frames(client, manifest):
    response = client.get("/api/frames", params={**QUERY, "detector": 1})
    assert response.status_code == 200, response.text
    result = Frames.model_validate(response.json())
    assert result.frames == []
    assert result.reference_frame_id is None
    assert result.warnings == ["FEW_FRAMES"]


def test_coordinates_outside_fits_return_no_frames_error(client, manifest):
    query = {"ra": QUERY["ra"], "dec": QUERY["dec"] + 0.12, "size": QUERY["size"]}
    response = client.get("/api/frames", params=query)
    assert response.status_code == 404
    assert ErrorResponse.model_validate(response.json()).error.code == "NO_FRAMES"


def test_observed_barnard_fixture_pack(client, monkeypatch):
    data_dir = ROOT / "data"
    pack = data_dir / "fixture_pack_v1"
    if not list(pack.glob("Barnards_Star/*.fits")):
        pytest.skip("Local Barnard FITS fixture pack is absent")
    monkeypatch.setenv("DATA_DIR", str(data_dir))

    response = client.get("/api/frames", params=QUERY)
    assert response.status_code == 200, response.text
    result = Frames.model_validate(response.json())
    assert result.frames
    for frame in result.frames:
        assert frame.id.startswith("observed-")
        assert frame.release == "qr2"
        assert 4.4 < frame.wavelength_um < 5.1
        png = read_png(client, frame.png)
        assert png.shape == (result.grid.height, result.grid.width)
        assert np.ptp(png) > 0
        assert frame.predicted_px is not None
    assert (read_png(client, result.frames[0].diff_png) == 128).all()
