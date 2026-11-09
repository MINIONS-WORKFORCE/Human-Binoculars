import logging
import os
from time import perf_counter

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .frame_jobs import router as jobs_router
from .mock_api import router

app = FastAPI(title="SPHEREx Training API")
cors_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_methods=["GET"],
    expose_headers=["Server-Timing", "X-Cache", "Retry-After"],
)
app.include_router(router)
app.include_router(jobs_router)
logger = logging.getLogger("uvicorn.error")


@app.middleware("http")
async def record_request_time(request: Request, call_next):
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        elapsed_ms = (perf_counter() - started) * 1000
        response.headers["Server-Timing"] = f"app;dur={elapsed_ms:.2f}"
        return response
    finally:
        logger.info(
            "%s %s status=%d duration_ms=%.2f",
            request.method,
            request.url.path,
            status,
            (perf_counter() - started) * 1000,
        )


@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    fields = sorted({str(e["loc"][-1]) for e in exc.errors() if len(e["loc"]) > 1})
    if not fields:
        fields = ["t_min", "t_max"]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid query or inconsistent time bounds.",
                "fields": fields,
            }
        },
    )


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
def unexpected_error(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "PROCESSING_ERROR",
                "message": "Local mock processing failed.",
                "fields": [],
            }
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    """Report application liveness without checking external services."""
    return {"status": "ok"}
