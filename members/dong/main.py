from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mock_api import router

app = FastAPI(title="SPHEREx Training API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])
app.include_router(router)


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
