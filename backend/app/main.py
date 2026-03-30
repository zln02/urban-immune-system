from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import alerts, predictions, signals
from .config import settings

app = FastAPI(
    title="Urban Immune System API",
    version="0.2.0",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(signals.router)
app.include_router(predictions.router)
app.include_router(alerts.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.2.0"}
