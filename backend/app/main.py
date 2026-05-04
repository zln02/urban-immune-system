from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import alerts, chat, predictions, signals
from .config import settings
from .middleware import APIKeyAuthMiddleware, AuditLogMiddleware, RateLimitMiddleware
from .tasks import broker


@asynccontextmanager
async def lifespan(app: FastAPI):
    await broker.startup()
    yield
    await broker.shutdown()


app = FastAPI(
    title="Urban Immune System API",
    version="0.2.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# 미들웨어 적용 순서: Audit (가장 바깥) → CORS → RateLimit → APIKey (가장 안쪽)
# Starlette 는 add_middleware 역순으로 wrap 하므로 아래 순서대로 등록한다.
app.add_middleware(
    APIKeyAuthMiddleware,
    api_keys=settings.api_keys,
    environment=settings.environment,
)
app.add_middleware(
    RateLimitMiddleware,
    requests_per_minute=settings.rate_limit_per_minute,
    burst=settings.rate_limit_burst,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["*", "X-API-Key"],
)
app.add_middleware(AuditLogMiddleware)

app.include_router(signals.router)
app.include_router(predictions.router)
app.include_router(alerts.router)
app.include_router(chat.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.2.0"}
