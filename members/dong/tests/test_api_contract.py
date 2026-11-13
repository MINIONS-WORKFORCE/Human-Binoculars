"""Issue #14 response contract, image coordinates and offline behavior."""

import io
import socket

import pytest
from app.api_models import Astrometry, ErrorResponse, Frames, Health, Photometry, Resolve
from app.main import app
from app.services.fixtures import image_lock, images
from fastapi.testclient import TestClient
from PIL import Image

QUERY = {"ra": 269.4521, "dec": 4.6934, "target_key": "barnard"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setenv("DATA_MODE", "fixture")
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    monkeypatch.setattr(
        socket, "create_connection", lambda *a, **k: pytest.fail("Fixture called network")
    )
    with image_lock:
        images.clear()
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.mark.parametrize(
    "path,params,model",
    [
        ("/api/health", {}, Health),
        ("/api/resolve", {"name": "Barnard's Star"}, Resolve),
        ("/api/frames", QUERY, Frames),
        ("/api/photometry", QUERY, Photometry),
        ("/api/astrometry", QUERY, Astrometry),
    ],
)
def test_json_routes(client, path, params, model):
    result = client.get(path, params=params)
    assert result.status_code == 200, result.text
    model.model_validate(result.json())


@pytest.mark.parametrize(
    "name,key",
    [
        ("Barnard's Star", "barnard"),
        ("WISE 0855-0714", "wise0855"),
        ("eps Ind B", "epsindib"),
        ("RW Aur", "rwaur"),
        ("R Dra", "rdra"),
    ],
)
def test_resolve_five_targets_from_epoch_tagged_catalog(client, name, key):
    response = client.get("/api/resolve", params={"name": name})
    assert response.status_code == 200, response.text
    result = Resolve.model_validate(response.json())
    assert result.target_key == key
    assert result.epoch == "J2000.0"
    assert result.source == "targets_table"


def test_fixture_health_and_localhost_cors(client):
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.json()["mode"] == "fixture"
    assert response.json()["irsa_reachable"] is None


def test_science_samples_are_not_relabelled_as_other_objects(client):
    photometry = client.get("/api/photometry", params=QUERY).json()
    astrometry = client.get("/api/astrometry", params={**QUERY, "target_key": "rdra"}).json()
    assert photometry["points"] == []
    assert astrometry["points"] == []


@pytest.mark.parametrize("key", ["barnard", "wise0855", "epsindib", "rwaur", "rdra"])
def test_five_targets_have_three_frames(client, key):
    result = client.get("/api/frames", params={**QUERY, "target_key": key}).json()
    assert len(result["frames"]) >= 3
    for frame in result["frames"]:
        for field in ("png", "diff_png"):
            png = client.get(frame[field])
            assert png.headers["content-type"] == "image/png"
            assert png.headers["cache-control"] == "public, max-age=86400"
            image = Image.open(io.BytesIO(png.content))
            assert image.size == (39, 39) and image.mode == "L"


@pytest.mark.parametrize(
    "path,params,code,status",
    [
        ("/api/health", {"bad": "value"}, None, 200),
        ("/api/resolve", {"name": "unknown"}, "UNKNOWN_TARGET", 404),
        ("/api/frames", {"ra": 360, "dec": 0}, "BAD_COORDS", 400),
        ("/api/frames/missing.png", {}, "FRAME_NOT_FOUND", 404),
        ("/api/frames/missing/diff.png", {}, "FRAME_NOT_FOUND", 404),
        ("/api/photometry", {"ra": 1, "dec": 2, "detector": 7}, "BAD_PARAM", 400),
        ("/api/astrometry", {"ra": "NaN", "dec": 2}, "BAD_COORDS", 400),
    ],
)
def test_errors(client, path, params, code, status):
    response = client.get(path, params=params)
    assert response.status_code == status
    if code:
        assert ErrorResponse.model_validate(response.json()).error.code == code


def test_null_prediction_truncation_and_no_image_id_collision(client):
    first = client.get("/api/frames", params={"ra": 1, "dec": 2, "max_frames": 1}).json()
    second = client.get("/api/frames", params={"ra": 3, "dec": 4, "detector": 2}).json()
    assert first["frames"][0]["predicted_px"] is None
    assert set(first["warnings"]) == {"FEW_FRAMES", "TRUNCATED"}
    assert first["frames"][0]["id"] != second["frames"][0]["id"]
    assert client.get(first["frames"][0]["png"]).status_code == 200


def test_openapi_and_sample_schema(client):
    from pathlib import Path

    from app.api_models import Frames

    schema = client.get("/openapi.json").json()
    assert len(schema["paths"]) == 7
    assert all("get" in route for route in schema["paths"].values())
    root = Path(__file__).resolve().parents[3]
    Frames.model_validate_json((root / "api_samples/frames_barnard_d6.json").read_text())


def test_unexpected_error_is_contract_json_with_cors(client, monkeypatch):
    def broken():
        raise RuntimeError("simulated bug")

    monkeypatch.setattr("app.services.fixtures.health", broken)
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 500
    assert ErrorResponse.model_validate(response.json()).error.code == "INTERNAL"
    # Without this header the browser hides the 500 and the page can only say NETWORK.
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "Server-Timing" in response.headers


def test_unavailable_mode_uses_contract_error(client, monkeypatch):
    monkeypatch.setenv("DATA_MODE", "unsupported")
    response = client.get("/api/health")
    assert response.status_code == 500
    assert ErrorResponse.model_validate(response.json()).error.code == "INTERNAL"


def test_live_mode_never_falls_back_to_fixture(client, monkeypatch):
    monkeypatch.setenv("DATA_MODE", "live")
    monkeypatch.setattr("app.services.fixtures.load_cutouts", lambda *args: ())
    assert client.get("/api/health").json()["mode"] == "live"
    response = client.get("/api/frames", params=QUERY)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "NO_FRAMES"
    for endpoint in ("photometry", "astrometry"):
        response = client.get(f"/api/{endpoint}", params=QUERY)
        assert response.status_code == 200
        assert response.json()["points"] == []


def test_astrometry_detector_filter(client):
    d6 = client.get("/api/astrometry", params={**QUERY, "detector": 6}).json()
    d1 = client.get("/api/astrometry", params={**QUERY, "detector": 1}).json()
    assert len(d6["points"]) == 3
    assert d1["points"] == []
    assert d1["fit"] is None


def test_png_marker_and_difference_zero(client):
    result = client.get("/api/frames", params=QUERY).json()
    for frame in result["frames"]:
        image = Image.open(io.BytesIO(client.get(frame["png"]).content))
        x, y = map(round, frame["predicted_px"])
        assert image.getpixel((x, y)) > 200
        # Outside the artificial source and FIX label, zero difference is gray 128.
        difference = Image.open(io.BytesIO(client.get(frame["diff_png"]).content))
        assert difference.getpixel((0, 0)) == 128
