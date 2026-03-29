from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import alerts, predictions, signals
from app.config import settings

app = FastAPI(
    title="Urban Immune System API",
    description="AI 기반 감염병 조기경보 시스템 — REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(signals.router, prefix="/api/v1/signals", tags=["signals"])
app.include_router(predictions.router, prefix="/api/v1/predictions", tags=["predictions"])
app.include_router(alerts.router, prefix="/api/v1/alerts", tags=["alerts"])


@app.get("/health", tags=["system"])
async def health_check() -> dict:
    return {"status": "ok", "service": "urban-immune-system"}
