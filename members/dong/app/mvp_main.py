"""Opt-in FastAPI entry point for the SRS MVP v1 contract."""

import asyncio
import logging
import os
import time
from threading import BoundedSemaphore
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .legacy.schemas import ErrorResponse
from .mvp_models import MVPFrames, MVPQuery, MVPTarget
from .services import mvp_frames

app = FastAPI(title="SPHEREx Sky Viewer MVP API", version="1.0")
slots = BoundedSemaphore(2)
logger = logging.getLogger("uvicorn.error")
ERRORS = {status: {"model": ErrorResponse} for status in (422, 500, 502, 503, 504)}


def error_response(status, code, message, fields=()):
    body = ErrorResponse(error={"code": code, "message": message, "fields": list(fields)})
    return JSONResponse(status_code=status, content=body.model_dump())


@app.exception_handler(RequestValidationError)
def validation_error(request: Request, error: RequestValidationError):
    fields = {str(item["loc"][-1]) for item in error.errors() if len(item["loc"]) > 1}
    fields.discard("query")
    return error_response(
        422,
        "VALIDATION_ERROR",
        "Invalid query or time bounds.",
        sorted(fields or {"t_min", "t_max"}),
    )


@app.exception_handler(mvp_frames.MVPError)
def expected_error(request: Request, error: mvp_frames.MVPError):
    return error_response(error.status, error.code, str(error))


@app.middleware("http")
async def record_request_time(request: Request, call_next):
    start = time.monotonic()
    try:
        response = await call_next(request)
    except Exception as error:  # noqa: BLE001 -- HTTP boundary maps unexpected failures
        logger.error("mvp_request_failed error_type=%s", type(error).__name__)
        response = error_response(500, "PROCESSING_ERROR", "Frame processing failed.")
    elapsed_ms = (time.monotonic() - start) * 1000
    response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.2f}"
    logger.info(
        "%s %s status=%s duration_ms=%.2f",
        request.method,
        request.url.path,
        response.status_code,
        elapsed_ms,
    )
    return response


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/targets", response_model=list[MVPTarget])
def targets():
    return list(mvp_frames.target_options())


def render_request(query, deadline):
    if not slots.acquire(blocking=False):
        raise mvp_frames.MVPError(503, "BUSY", "The frame service is busy. Try again.")
    try:
        return mvp_frames.get_frames(query, deadline)
    finally:
        slots.release()


@app.get("/api/frames", response_model=MVPFrames, responses=ERRORS)
async def frames(query: Annotated[MVPQuery, Query()], response: Response):
    timeout = mvp_frames.REQUEST_TIMEOUT
    deadline = time.monotonic() + timeout
    try:
        result, cache_status = await asyncio.wait_for(
            asyncio.to_thread(render_request, query, deadline), timeout=timeout
        )
    except TimeoutError as exc:
        raise mvp_frames.timeout_error() from exc
    response.headers["X-Cache"] = cache_status
    return result


@app.get(
    "/files/{path:path}",
    response_class=Response,
    responses={200: {"content": {"image/png": {}}}, 404: {"model": ErrorResponse}},
)
def image(path: str):
    content = mvp_frames.get_image(path)
    if content is None:
        raise mvp_frames.MVPError(
            404, "FRAME_NOT_FOUND", "Image missing or expired. Reload frames."
        )
    return Response(
        content, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"}
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(
        {
            "http://localhost:5173",
            *(
                value.strip()
                for value in os.getenv("CORS_ALLOW_ORIGINS", "").split(",")
                if value.strip()
            ),
        }
    ),
    allow_methods=["GET"],
    expose_headers=["Server-Timing", "X-Cache"],
)
