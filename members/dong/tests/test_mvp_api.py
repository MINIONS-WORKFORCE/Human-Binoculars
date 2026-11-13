"""MVP v1 HTTP acceptance checks, separate from the public API 0.1 suite."""

import hashlib
import json
import shutil
import time
from pathlib import Path
from threading import Event

import numpy as np
import pytest
import yaml
from app.mvp_models import MVPQuery
from app.services import mvp_frames
from astropy.io import fits
from astropy.wcs import WCS
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

QUERY = {
    "s_ra": 269.4464,
    "s_dec": 4.7668,
    "obs_collection": "spherex_qr2",
    "energy_bandpassname": "SPHEREx-D6",
    "cutout_size_deg": 0.0333,
}


@pytest.fixture
def client(monkeypatch, tmp_path):
    from app.mvp_main import app

    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setenv("API_MODE", "mock")
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


def test_mock_contract_and_png_do_not_require_fits(client):
    response = client.get("/api/frames", params=QUERY)
    assert response.status_code == 200, response.text
    payload = response.json()
    validate_frames(client, payload)
    assert payload["data_kind"] == "mock"
    assert payload["warnings"][0]["code"] == "MOCK_DATA"
    assert len(payload["frames"]) >= 2
    assert payload["display"]["stretch"] == "asinh"
    for frame in payload["frames"]:
        image = client.get(frame["image_url"])
        assert image.status_code == 200
        assert image.headers["content-type"] == "image/png"


def test_targets_have_propagated_centers(client):
    response = client.get("/api/targets")
    assert response.status_code == 200, response.text
    targets = {target["id"]: target for target in response.json()}
    assert set(targets) == {"barnard", "wise0855", "epsindib", "rwaur", "rdra"}
    assert targets["barnard"]["dec_deg"] == pytest.approx(4.7668, abs=0.001)
    assert targets["wise0855"]["default_detector"] == 6


def test_validation_error_names_input_field(client):
    response = client.get("/api/frames", params={**QUERY, "cutout_size_deg": 0.3})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert response.json()["error"]["fields"] == ["cutout_size_deg"]


def validate_frames(client, payload):
    schema = client.get("/openapi.json").json()
    components = schema["components"]
    response_schema = schema["paths"]["/api/frames"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    Draft202012Validator({**response_schema, "components": components}).validate(payload)


def test_generated_openapi_matches_mvp_snapshot(client):
    root = Path(__file__).resolve().parents[3]
    snapshot = root / "shared/api-contract/openapi-mvp-v1.yaml"
    assert (
        yaml.safe_load(snapshot.read_text(encoding="utf-8")) == client.get("/openapi.json").json()
    )


@pytest.fixture
def cutout(tmp_path):
    path = tmp_path / "generated.fits"
    wcs = WCS(naxis=2)
    wcs.wcs.ctype = ["RA---TAN", "DEC--TAN"]
    wcs.wcs.crval = [QUERY["s_ra"], QUERY["s_dec"]]
    wcs.wcs.crpix = [21, 21]
    wcs.wcs.cdelt = [-6.2 / 3600, 6.2 / 3600]
    header = wcs.to_header()
    header.update({"BUNIT": "MJy/sr", "OBSID": "example", "DETECTOR": 6})
    flags = fits.ImageHDU(np.zeros((41, 41), dtype=np.int32), name="FLAGS")
    flags.header["MP_BAD"] = 0
    pixels = np.arange(41 * 41, dtype=float).reshape(41, 41)
    fits.HDUList(
        [fits.PrimaryHDU(), fits.ImageHDU(pixels, header=header, name="IMAGE"), flags]
    ).writeto(path)
    source = {
        "obs_id": "example",
        "obs_publisher_did": "ivo://test/example",
        "obs_collection": "spherex_qr2",
        "energy_bandpassname": "SPHEREx-D6",
        "t_min": 60900,
        "t_max": 60900.01,
        "access_url": "https://irsa.ipac.caltech.edu/example.fits",
    }
    return source, path


def test_real_http_renders_fits_and_reuses_cache(client, cutout, monkeypatch):
    monkeypatch.setenv("API_MODE", "real")
    source, path = cutout
    calls = []

    def find(*args, **kwargs):
        calls.append("find")
        assert args[2:4] == ("spherex_qr2", "SPHEREx-D6")
        assert kwargs["search_radius_deg"] == pytest.approx(0.0333 / np.sqrt(2))
        return [source]

    def download(images, ra, dec, size, out, **kwargs):
        calls.append("download")
        assert kwargs["max_per_visit"] == 6
        out.mkdir()
        saved = out / "generated.fits"
        shutil.copyfile(path, saved)
        manifest = out / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "entries": [
                        {
                            "obs_publisher_did": source["obs_publisher_did"],
                            "path": str(saved.relative_to(out.parent)),
                            "sha256": hashlib.sha256(saved.read_bytes()).hexdigest(),
                        }
                    ],
                    "failed": [{"obs_id": "second-observation"}],
                }
            ),
            encoding="utf-8",
        )
        return manifest

    monkeypatch.setattr(mvp_frames.irsa, "find_images", find)
    monkeypatch.setattr(mvp_frames.irsa, "fetch_cutouts", download)
    first = client.get("/api/frames", params=QUERY)
    assert first.status_code == 200, first.text
    assert first.headers["x-cache"] == "MISS"
    data = first.json()
    validate_frames(client, data)
    assert data["data_kind"] == "observational"
    assert data["frames"][0]["source_obs_publisher_dids"] == [source["obs_publisher_did"]]
    assert data["frames"][0]["n_images"] == 1
    assert {"SINGLE_VISIT", "PARTIAL_DOWNLOAD"} <= {item["code"] for item in data["warnings"]}
    assert client.get(data["frames"][0]["image_url"]).status_code == 200
    second = client.get("/api/frames", params=QUERY)
    assert second.headers["x-cache"] == "HIT"
    assert second.json() == data
    assert calls == ["find", "download"]


def test_prebuilt_bypasses_archive(client, cutout, monkeypatch):
    monkeypatch.setenv("API_MODE", "real")
    target = client.get("/api/targets").json()[0]
    query = MVPQuery.model_validate(
        {
            **QUERY,
            "s_ra": target["ra_deg"],
            "s_dec": target["dec_deg"],
            "cutout_size_deg": target["default_fov_arcmin"] / 60,
        }
    )
    payload, images = mvp_frames.build_observed(query, [cutout], 0, time.monotonic() + 30)
    mvp_frames.write_prebuilt(query, payload, images)

    def reject_network(*args, **kwargs):
        pytest.fail("Prebuilt requests must not use IRSA")

    monkeypatch.setattr(mvp_frames.irsa, "find_images", reject_network)
    request = {**QUERY, "s_ra": round(query.s_ra, 4), "s_dec": round(query.s_dec, 4)}
    response = client.get("/api/frames", params=request)
    assert response.status_code == 200, response.text
    assert response.headers["x-cache"] == "PREBUILT"
    payload = response.json()
    assert payload["warnings"][0]["code"] == "PREBUILT"
    assert client.get(payload["frames"][0]["image_url"]).status_code == 200


def test_empty_release_is_no_data_without_fallback(client, monkeypatch):
    monkeypatch.setenv("API_MODE", "real")
    calls = []

    def empty(ra, dec, collection, *args, **kwargs):
        calls.append(collection)
        return []

    monkeypatch.setattr(mvp_frames.irsa, "find_images", empty)
    response = client.get("/api/frames", params={**QUERY, "obs_collection": "spherex_qr3"})
    assert response.status_code == 200, response.text
    payload = response.json()
    validate_frames(client, payload)
    assert payload["frames"] == []
    assert payload["warnings"][0]["code"] == "NO_DATA"
    assert calls == ["spherex_qr3"]


@pytest.mark.parametrize(
    "error,status,code",
    [
        (mvp_frames.irsa.UpstreamError, 502, "UPSTREAM_ERROR"),
        (mvp_frames.irsa.UpstreamTimeout, 504, "UPSTREAM_TIMEOUT"),
    ],
)
def test_upstream_errors_follow_contract(client, monkeypatch, error, status, code):
    monkeypatch.setenv("API_MODE", "real")

    def fail(*args, **kwargs):
        raise error("detail must stay private")

    monkeypatch.setattr(mvp_frames.irsa, "find_images", fail)
    response = client.get("/api/frames", params=QUERY)
    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert "detail must stay private" not in response.text


def test_response_deadline_bounds_unresponsive_worker(client, monkeypatch):
    finish = Event()
    finished = Event()

    def wait(query, deadline):
        finish.wait(2)
        finished.set()

    monkeypatch.setattr(mvp_frames, "REQUEST_TIMEOUT", 0.15)
    monkeypatch.setattr(mvp_frames, "get_frames", wait)
    try:
        response = client.get("/api/frames", params=QUERY)
        assert response.status_code == 504
        assert response.json()["error"]["code"] == "UPSTREAM_TIMEOUT"
        assert not finished.is_set()
    finally:
        finish.set()


def test_processing_error_reaches_cross_origin_frontend(client, monkeypatch):
    def fail(*args):
        raise ValueError("private processing detail")

    monkeypatch.setattr(mvp_frames, "get_frames", fail)
    response = client.get("/api/frames", params=QUERY, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 500
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.json()["error"]["code"] == "PROCESSING_ERROR"
    assert "private processing detail" not in response.text
