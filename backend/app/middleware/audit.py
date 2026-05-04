"""HTTP 접근 감사로그 미들웨어 (ISMS-P 2.9.4).

요청 IP·메서드·경로·상태코드·처리시간(ms) 을 구조화 로그로 기록한다.
민감 헤더(Authorization·X-API-Key·Cookie) 는 절대 로그에 남기지 않는다.
"""
from __future__ import annotations

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("uis.audit")


class AuditLogMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, service_name: str = "uis-backend") -> None:
        super().__init__(app)
        self._service = service_name

    @staticmethod
    def _client_ip(request: Request) -> str:
        # X-Forwarded-For 우선 (reverse proxy 뒤 운영 가정)
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            return xff.split(",")[0].strip()
        if request.client:
            return request.client.host
        return "-"

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            duration_ms = (time.perf_counter() - start) * 1000.0
            logger.info(
                "access service=%s rid=%s ip=%s method=%s path=%s status=%d dur_ms=%.1f ua=%r",
                self._service,
                request_id,
                self._client_ip(request),
                request.method,
                request.url.path,
                status,
                duration_ms,
                request.headers.get("user-agent", "-"),
            )
