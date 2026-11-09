"""Bounded training jobs and disk-backed, atomically published frame bundles."""

import hashlib
import json
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import BoundedSemaphore
from uuid import uuid4

from diskcache import Cache
from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse, Response

from shared.frames_pipeline import VERSION, make_frames

from .schemas import FramesQuery, FramesResponse, JobStatus

ROOT = Path(__file__).resolve().parents[3]
router = APIRouter()
logger = logging.getLogger("uvicorn.error")
executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="frames")
slots = BoundedSemaphore(2)
LEASE = 1800


def cache_dir():
    return ROOT / os.getenv("CACHE_DIR", ".cache") / "frame-jobs"


def open_cache():
    return Cache(str(cache_dir()), size_limit=512 * 1024 * 1024)


def identity(query, source_mode, data_dir):
    revision = "archive-ttl-3600"
    if source_mode == "fixture":
        pack = data_dir / "fixture_pack_v1"
        digest = hashlib.sha256()
        for path in sorted(
            [pack / "metadata.csv", pack / "rendered/frames.json", *pack.rglob("*.fits")]
        ):
            digest.update(path.relative_to(pack).as_posix().encode())
            with path.open("rb") as handle:
                digest.update(hashlib.file_digest(handle, "sha256").digest())
        revision = digest.hexdigest()
    values = {
        key: (0.0 if isinstance(value, float) and value == 0 else value)
        for key, value in query.model_dump().items()
    }
    payload = {"query": values, "mode": source_mode, "revision": revision, "pipeline": VERSION}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()


def public_job(job_id, record):
    result = {"job_id": job_id, "status": record["status"], "status_url": f"/api/jobs/{job_id}"}
    if "error" in record:
        result["error"] = record["error"]
    if record["status"] == "succeeded":
        result["result"] = record["result"]
    return result


def run_job(job_id, key, query, mode, data_dir):
    started = time.perf_counter()
    with open_cache() as cache:

        @contextmanager
        def stage(name):
            begin = time.perf_counter()
            outcome = "error"
            try:
                cache.touch(job_id, expire=LEASE)
                yield
                outcome = "ok"
            finally:
                logger.info(
                    "job_id=%s stage=%s outcome=%s duration_ms=%.2f",
                    job_id,
                    name,
                    outcome,
                    (time.perf_counter() - begin) * 1000,
                )

        try:
            cache.set(job_id, {"status": "running"}, expire=LEASE)
            with TemporaryDirectory(dir=cache_dir()) as temporary:
                result, images = make_frames(query, mode, data_dir, Path(temporary), stage)
            for frame in result["frames"]:
                frame["image_url"] = f"/api/jobs/{job_id}/images/{frame['image_url']}"
            result = FramesResponse.model_validate(result).model_dump(exclude_none=True)
            ttl = 3600 if result["frames"] else 60
            with stage("publish"):
                cache.set(
                    job_id, {"status": "succeeded", "result": result, "images": images}, expire=ttl
                )
                cache.set(key, job_id, expire=ttl)
        except Exception as error:  # noqa: BLE001 -- worker boundary must persist a failed state
            # Public errors deliberately omit remote URLs and filesystem paths.
            logger.error("job_id=%s stage=pipeline error_type=%s", job_id, type(error).__name__)
            cache.set(
                job_id,
                {
                    "status": "failed",
                    "error": {
                        "code": "PROCESSING_ERROR",
                        "message": "Frame processing failed. Check input data, archive availability or narrow the time range.",
                    },
                },
                expire=300,
            )
        finally:
            slots.release()
            logger.info(
                "job_id=%s stage=total duration_ms=%.2f",
                job_id,
                (time.perf_counter() - started) * 1000,
            )


def submit(query: FramesQuery):
    mode = os.getenv("PIPELINE_SOURCE", "live")
    if mode not in {"live", "fixture"}:
        raise HTTPException(500, "Invalid pipeline source configuration")
    data_dir = ROOT / os.getenv("DATA_DIR", "data")
    try:
        key = "frames:" + identity(query, mode, data_dir)
    except OSError:
        raise HTTPException(500, "Prepare the local fixture before starting this job") from None
    with open_cache() as cache:
        with cache.transact():
            job_id = cache.get(key)
            record = cache.get(job_id) if job_id else None
            if record and record["status"] == "succeeded":
                logger.info("job_id=%s cache=hit", job_id)
                return JSONResponse(record["result"], headers={"X-Cache": "HIT"})
            if record and record["status"] in {"queued", "running"}:
                return JSONResponse(
                    public_job(job_id, record), status_code=202, headers={"Retry-After": "2"}
                )
            if not slots.acquire(blocking=False):
                raise HTTPException(503, "Two frame jobs are already active. Retry later.")
            job_id = uuid4().hex
            record = {"status": "queued"}
            cache.set(job_id, record, expire=LEASE)
            cache.set(key, job_id, expire=LEASE)
        try:
            executor.submit(
                run_job, job_id, key, query.model_dump(exclude_none=True), mode, data_dir
            )
        except Exception:
            slots.release()
            cache.delete(job_id)
            cache.delete(key)
            raise
    logger.info("job_id=%s cache=miss", job_id)
    return JSONResponse(
        public_job(job_id, record), status_code=202, headers={"Retry-After": "2", "X-Cache": "MISS"}
    )


@router.get("/api/jobs/{job_id}", response_model=JobStatus, response_model_exclude_none=True)
def get_job(job_id: str):
    with open_cache() as cache:
        record = cache.get(job_id)
    if not isinstance(record, dict) or "status" not in record:
        raise HTTPException(404, "Job expired or missing. Submit the frames request again.")
    return public_job(job_id, record)


@router.get("/api/jobs/{job_id}/images/{filename}")
def get_image(job_id: str, filename: str):
    with open_cache() as cache:
        record = cache.get(job_id)
    content = record.get("images", {}).get(filename) if isinstance(record, dict) else None
    if content is None:
        raise HTTPException(404, "Image expired or missing. Submit the frames request again.")
    return Response(content, media_type="image/png")
