from fastapi import FastAPI

from .api import router as api_router
from .config import settings

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Urban risk signal ingestion and reporting API",
)
app.include_router(api_router)


@app.get("/")
def root() -> dict[str, object]:
    return {
        "service": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, object]:
    return {
        "status": "ok",
        "environment": settings.environment,
    }
