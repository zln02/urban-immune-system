"""API Key 인증 미들웨어 (ISMS-P 2.5.1).

development 환경에서는 api_keys 가 비어 있으면 통과 (로컬 개발 편의).
production 환경에서는 settings.api_keys 가 반드시 1개 이상 설정되어야 하며
모든 요청은 X-API-Key 헤더에 등록된 키를 보내야 한다.
"""
from __future__ import annotations

import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    # /health, /docs, /openapi.json, /redoc 는 공개 (모니터링·문서)
    PUBLIC_PATHS: frozenset[str] = frozenset({
        "/health",
        "/docs",
        "/openapi.json",
        "/redoc",
    })

    def __init__(
        self,
        app,
        api_keys: list[str],
        environment: str,
        header_name: str = "X-API-Key",
    ) -> None:
        super().__init__(app)
        self._keys = [k for k in api_keys if k]
        self._is_production = environment.lower() == "production"
        self._header = header_name

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if path in self.PUBLIC_PATHS or path.startswith("/docs") or path.startswith("/redoc"):
            return await call_next(request)

        # development 환경에서 키 미등록 시 통과 (로컬 편의)
        if not self._is_production and not self._keys:
            return await call_next(request)

        # production 또는 키 등록된 development 는 검증 강제
        provided = request.headers.get(self._header, "")
        if not provided or not any(hmac.compare_digest(provided, k) for k in self._keys):
            return JSONResponse(
                status_code=401,
                content={"detail": "missing or invalid API key"},
                headers={"WWW-Authenticate": f"ApiKey header={self._header}"},
            )

        return await call_next(request)
