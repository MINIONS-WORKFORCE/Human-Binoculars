"""Public mock behavior tests; all test metadata is synthetic, with no archive data."""

import json

import pytest
from fastapi.testclient import TestClient
from main import app

BASE = {"s_ra": 133.79513, "s_dec": -7.24515, "obs_collection": "spherex_qr2"}
PARAMS = {
    "frames": {**BASE, "energy_bandpassname": "SPHEREx-D6", "cutout_size_deg": 0.05},
    "spectrum": BASE,
    "lightcurve": {**BASE, "energy_bandpassname": "SPHEREx-D6"},
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    sources = []
    for band, time in [("SPHEREx-D6", 61002), ("SPHEREx-D1", 61000), ("SPHEREx-D6", 61001)]:
        sources.append(
            {
                "obs_id": f"synthetic-{time}",
                "obs_publisher_did": f"ivo://example.org/{band}/{time}",
                "obs_collection": "spherex_qr2",
                "energy_bandpassname": band,
                "s_ra": 134,
                "s_dec": -7,
                "t_min": time,
                "t_max": time + 0.01,
                "access_url": "https://example.org/synthetic.fits",
                "access_format": "image/fits",
            }
        )
    (tmp_path / "wise0855_qr2_sources.json").write_text(json.dumps({"sources": sources}))
    monkeypatch.setenv("DATA_DIR", str(tmp_path))
    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize("endpoint", PARAMS)
def test_success_and_determinism(client, endpoint):
    response = client.get(f"/api/{endpoint}", params=PARAMS[endpoint])
    assert response.status_code == 200
    body = response.json()
    assert body == client.get(f"/api/{endpoint}", params=PARAMS[endpoint]).json()
    assert body["data_kind"] == "mock"
    assert body["warnings"][0]["code"] == "MOCK_DATA"
    assert body["query"] == PARAMS[endpoint]
    ids = {s["obs_publisher_did"] for s in body["sources"]}
    items = body["frames" if endpoint == "frames" else "points"]
    assert items
    assert all(set(p["source_obs_publisher_dids"]) <= ids for p in items)
    key = "wavelength_um" if endpoint == "spectrum" else "t_min"
    assert [p[key] for p in items] == sorted(p[key] for p in items)


def test_frames_png_and_midpoint(client):
    frame = client.get("/api/frames", params=PARAMS["frames"]).json()["frames"][0]
    assert frame["observation_time"] == "2025-11-22T00:07:12Z"
    image = client.get(frame["image_url"])
    assert image.status_code == 200
    assert image.headers["content-type"] == "image/png"
    assert image.content.startswith(b"\x89PNG\r\n\x1a\n")
    assert client.get("/mock/frames/missing.png").status_code == 404


@pytest.mark.parametrize("endpoint", PARAMS)
@pytest.mark.parametrize(
    "change", [{"s_ra": 0}, {"obs_collection": "spherex_qr3"}, {"t_min": 70000}]
)
def test_empty_is_explicit_mock_not_archive_claim(client, endpoint, change):
    body = client.get(f"/api/{endpoint}", params={**PARAMS[endpoint], **change}).json()
    assert body["data_kind"] == "mock"
    assert body["sources"] == []
    assert body["frames" if endpoint == "frames" else "points"] == []
    assert "NO_DATA" in {w["code"] for w in body["warnings"]}
    if endpoint != "frames":
        assert body["flux_unit"] is None and body["measurement_method"] is None
    if endpoint == "lightcurve":
        assert body["wavelength_min_um"] is None and body["wavelength_max_um"] is None


@pytest.mark.parametrize(
    "change",
    [
        {"s_ra": 360},
        {"s_dec": -91},
        {"s_ra": "NaN"},
        {"t_min": "inf"},
        {"t_min": 61003, "t_max": 61000},
        {"obs_collection": "wrong"},
        {"energy_bandpassname": "D6"},
        {"cutout_size_deg": 0},
        {"cutout_size_deg": 0.3},
    ],
)
def test_contract_validation_errors(client, change):
    response = client.get("/api/frames", params={**PARAMS["frames"], **change})
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR" and error["fields"]
    assert "input" not in error


def test_time_intersection(client):
    body = client.get(
        "/api/lightcurve", params={**PARAMS["lightcurve"], "t_min": 61001.005, "t_max": 61001.008}
    ).json()
    assert len(body["points"]) == 1
    assert body["points"][0]["time_mjd"] == pytest.approx(61001.005)


def test_missing_fixture_safe_error_and_independent_health(client, tmp_path):
    (tmp_path / "wise0855_qr2_sources.json").unlink()
    response = client.get("/api/frames", params=PARAMS["frames"])
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "PROCESSING_ERROR"
    assert str(tmp_path) not in response.text
    assert client.get("/health").json() == {"status": "ok"}


def test_docs_and_cors(client):
    assert client.get("/docs").status_code == 200
    paths = client.get("/openapi.json").json()["paths"]
    assert all(f"/api/{endpoint}" in paths for endpoint in PARAMS)
    response = client.get("/api/spectrum", params=BASE, headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "*"
