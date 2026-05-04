"""IP 기반 토큰 버킷 Rate Limiting (ISMS-P 2.6.1).

외부 라이브러리 의존 없이 in-memory 토큰버킷 구현.
단일 노드 운영 가정 — 다중 인스턴스로 확장 시 Redis 백엔드로 교체.

설계:
- IP 별 버킷 (capacity = burst, fill_rate = per_minute / 60)
- /health 와 SSE 스트림(/api/v1/alerts/stream, /api/v1/chat/*) 는 면제
  (SSE 는 단일 장기 연결이므로 RPS 산정에 부적합)
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger(__name__)


@dataclass
class _Bucket:
    tokens: float
    last: float


class RateLimitMiddleware(BaseHTTPMiddleware):
    EXEMPT_PREFIXES: tuple[str, ...] = (
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
        "/api/v1/alerts/stream",
        "/api/v1/chat",
    )

    def __init__(
        self,
        app,
        requests_per_minute: int = 120,
        burst: int = 30,
    ) -> None:
        super().__init__(app)
        self._fill_rate = max(requests_per_minute, 1) / 60.0
        self._capacity = float(burst)
        self._buckets: dict[str, _Bucket] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def _client_ip(request: Request) -> str:
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "anon"

    async def _take(self, ip: str) -> bool:
        now = time.monotonic()
        async with self._lock:
            b = self._buckets.get(ip)
            if b is None:
                b = _Bucket(tokens=self._capacity, last=now)
                self._buckets[ip] = b
            elapsed = now - b.last
            b.tokens = min(self._capacity, b.tokens + elapsed * self._fill_rate)
            b.last = now
            if b.tokens >= 1.0:
                b.tokens -= 1.0
                return True
            return False

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if any(path.startswith(p) for p in self.EXEMPT_PREFIXES):
            return await call_next(request)

        ip = self._client_ip(request)
        if not await self._take(ip):
            logger.warning("rate_limit ip=%s path=%s", ip, path)
            return JSONResponse(
                status_code=429,
                content={"detail": "rate limit exceeded"},
                headers={"Retry-After": "1"},
            )
        return await call_next(request)
