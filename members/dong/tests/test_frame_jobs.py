"""Check job publication, deduplication, failure and persistent result reuse."""

import time
from threading import Event

import pytest
from app import frame_jobs
from app.legacy_main import app
from fastapi.testclient import TestClient

QUERY = {
    "s_ra": 269.44636864652,
    "s_dec": 4.766880108377093,
    "obs_collection": "spherex_qr2",
    "energy_bandpassname": "SPHEREx-D6",
    "cutout_size_deg": 0.05,
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    monkeypatch.setenv("FRAMES_MODE", "pipeline")
    monkeypatch.setenv("PIPELINE_SOURCE", "live")
    with TestClient(app) as client:
        yield client


def wait_for_job(client, url):
    for _ in range(100):
        body = client.get(url).json()
        if body["status"] in {"succeeded", "failed"}:
            return body
        time.sleep(0.02)
    pytest.fail("Job did not finish")


def test_duplicate_requests_and_disk_result(client, monkeypatch):
    entered, release = Event(), Event()
    calls = []

    def pipeline(query, mode, data_dir, work_dir, stage):
        calls.append(query)
        entered.set()
        assert release.wait(5)
        return {
            "data_kind": "observational",
            "query": query,
            "frames": [],
            "sources": [],
            "warnings": [{"code": "NO_DATA", "message": "Empty sample"}],
        }, {}

    monkeypatch.setattr(frame_jobs, "make_frames", pipeline)
    first = client.get("/api/frames", params=QUERY)
    try:
        assert first.status_code == 202
        assert entered.wait(5)
        second = client.get("/api/frames", params=QUERY)
        assert second.status_code == 202
        assert second.json()["job_id"] == first.json()["job_id"]
    finally:
        release.set()
    assert wait_for_job(client, first.json()["status_url"])["status"] == "succeeded"
    cached = client.get("/api/frames", params=QUERY)
    assert cached.status_code == 200
    assert cached.headers["x-cache"] == "HIT"
    assert len(calls) == 1
    with frame_jobs.open_cache() as reopened:
        assert reopened[first.json()["job_id"]]["status"] == "succeeded"


def test_failure_is_public_and_can_retry(client, monkeypatch):
    def broken(*args):
        raise ValueError("private-local-path")

    monkeypatch.setattr(frame_jobs, "make_frames", broken)
    first = client.get("/api/frames", params=QUERY).json()
    failed = wait_for_job(client, first["status_url"])
    assert failed["status"] == "failed"
    assert "private-local-path" not in str(failed)
    retry = client.get("/api/frames", params=QUERY)
    assert retry.status_code == 202
    assert retry.json()["job_id"] != first["job_id"]
    wait_for_job(client, retry.json()["status_url"])


def test_key_covers_request_and_processing_mode():
    from pathlib import Path

    from app.schemas import FramesQuery

    first = frame_jobs.identity(FramesQuery(**QUERY), "live", Path("."))
    second = frame_jobs.identity(FramesQuery(**{**QUERY, "t_min": 60902}), "live", Path("."))
    assert first != second


def test_unknown_job_and_image(client):
    assert client.get("/api/jobs/missing").status_code == 404
    assert client.get("/api/jobs/missing/images/frame-0.png").status_code == 404
