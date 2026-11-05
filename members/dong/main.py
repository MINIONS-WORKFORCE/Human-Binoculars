from fastapi import FastAPI

app = FastAPI(title="SPHEREx Training API")


@app.get("/health")
def health() -> dict[str, str]:
    """Report application liveness without checking external services."""
    return {"status": "ok"}
