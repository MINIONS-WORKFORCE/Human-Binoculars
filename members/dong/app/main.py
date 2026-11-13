"""Issue #14 entry point. Historical training uses app.legacy_main."""

import logging
import os
from time import perf_counter

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .api_models import ErrorResponse
from .fixture_api import router
from .services.fixtures import FixtureError

app = FastAPI(title="Human Binoculars API", version="0.1")


# Registered before CORSMiddleware, so it runs inside it. Starlette otherwise answers
# an unhandled exception in its outermost layer, outside CORS: that 500 would carry no
# Access-Control-Allow-Origin, the browser would hide it, and the frontend could only
# report NETWORK instead of the contract's INTERNAL.
@app.middleware("http")
async def unexpected_error_inside_cors(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as exc:  # noqa: BLE001 - every bug must become the contract's INTERNAL
        return unexpected_error(request, exc)


app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(
        {
            "http://localhost:5173",
            *(v.strip() for v in os.getenv("CORS_ALLOW_ORIGINS", "").split(",") if v.strip()),
        }
    ),
    allow_methods=["GET"],
    expose_headers=["Server-Timing", "Cache-Control"],
)
app.include_router(router)
logger = logging.getLogger("uvicorn.error")


def error_response(status, code, message, details):
    body = ErrorResponse(error={"code": code, "message": message, "details": details})
    return JSONResponse(body.model_dump(), status_code=status)


@app.exception_handler(FixtureError)
def fixture_error(request: Request, exc: FixtureError):
    return error_response(exc.status, exc.code, exc.message, exc.details)


@app.exception_handler(RequestValidationError)
def validation_error(request: Request, exc: RequestValidationError):
    fields = sorted({str(e["loc"][-1]) for e in exc.errors()})
    code = "BAD_COORDS" if {"ra", "dec"}.intersection(fields) else "BAD_PARAM"
    return error_response(400, code, "Invalid request parameters.", {"fields": fields})


@app.exception_handler(StarletteHTTPException)
def http_error(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(exc.detail, status_code=exc.status_code)
    return error_response(exc.status_code, "INTERNAL", "Request failed.", {})


@app.exception_handler(Exception)
def unexpected_error(request: Request, exc: Exception):
    logger.error("request_failed error_type=%s", type(exc).__name__)
    return error_response(500, "INTERNAL", "Internal processing error.", {})


@app.middleware("http")
async def timing(request: Request, call_next):
    started = perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        response.headers["Server-Timing"] = f"app;dur={(perf_counter() - started) * 1000:.2f}"
        return response
    finally:
        logger.info(
            "%s %s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            status,
            (perf_counter() - started) * 1000,
        )


def contract_openapi():
    if app.openapi_schema is None:
        schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
        for path in schema["paths"].values():
            for operation in path.values():
                operation.get("responses", {}).pop("422", None)
        app.openapi_schema = schema
    return app.openapi_schema


app.openapi = contract_openapi
