from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import alerts, chat, forecast, predictions, signals
from .config import settings
from .middleware import APIKeyAuthMiddleware, AuditLogMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from .tasks import broker


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    await broker.startup()
    yield
    await broker.shutdown()


app = FastAPI(
    title="Urban Immune System API",
    version="0.2.0",
    docs_url="/docs",
    lifespan=lifespan,
)

# 미들웨어 적용 순서 (Starlette add_middleware 역순 wrap):
#   SecurityHeaders (가장 바깥) → Audit → CORS → RateLimit → APIKey (가장 안쪽)
# SecurityHeaders 를 가장 바깥에 배치해 에러 응답 포함 모든 응답에 보안 헤더 보장.
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
    # 명시 화이트리스트 — ISMS-P 2.10.1·OWASP CORS 가이드.
    # `*` 와일드카드는 preflight 우회 위험 + Spec 상 credentials 모드에서 무효.
    # 추가 필요 시 본 리스트에 명시적 등재 후 PR 리뷰.
    allow_headers=["Accept", "Authorization", "Content-Type", "X-API-Key", "X-Requested-With"],
)
app.add_middleware(AuditLogMiddleware)
app.add_middleware(SecurityHeadersMiddleware, environment=settings.environment)

app.include_router(signals.router)
app.include_router(predictions.router)
app.include_router(alerts.router)
app.include_router(chat.router)
app.include_router(forecast.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "version": "0.2.0"}
