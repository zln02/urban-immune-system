"""보안 헤더 미들웨어 (ISMS-P 2.10.1 — 웹 취약점 대응).

추가 헤더:
  X-Content-Type-Options: nosniff          — MIME sniffing 방지
  X-Frame-Options: DENY                    — Clickjacking 방지
  Strict-Transport-Security: ...           — HSTS (production only)
  Content-Security-Policy: default-src ... — XSS/코드 인젝션 방지 (느슨한 초기 정책)
  Referrer-Policy: strict-origin-when-cross-origin
  X-XSS-Protection: 1; mode=block         — 레거시 브라우저 XSS 필터 활성화
  Permissions-Policy: ...                 — 브라우저 API 권한 최소화
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# SSE 스트림 응답은 헤더가 이미 flush된 상태일 수 있으나,
# Starlette BaseHTTPMiddleware 는 최종 Response 에 헤더를 append 하므로 안전.
_HSTS_MAX_AGE = 31_536_000  # 1 year


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """모든 응답에 보안 HTTP 헤더를 추가하는 미들웨어."""

    def __init__(self, app, environment: str = "development") -> None:
        super().__init__(app)
        self._is_production = environment.lower() == "production"

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        response = await call_next(request)

        # MIME 타입 강제 — 브라우저가 content-type 을 무시하고 추측하는 것 차단
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Clickjacking 방지 — <iframe> 임베딩 전면 차단
        response.headers["X-Frame-Options"] = "DENY"

        # 레거시 브라우저 XSS 필터 강제 활성화
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Referer 헤더 — 크로스오리진에서 origin 만 전달 (경로 노출 방지)
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 브라우저 민감 API 비활성화 (geolocation, camera, mic 등)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), camera=(), microphone=(), payment=(), usb=()"
        )

        # CSP — production 엄격 / development 느슨 (Streamlit/Next dev HMR 호환).
        # backend 응답은 주로 API JSON·SSE 이지만, 직접 렌더링 페이지(`/docs` 등) 대비 정책 명시.
        # ISMS-P 2.10.1: production 에서 'unsafe-inline' script 차단 (XSS 차단력 강화).
        if self._is_production:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "  # FastAPI Swagger UI 인라인 style 필요
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )
        else:
            # 개발 환경 — Streamlit Phase1 fallback·Swagger UI 호환 (script unsafe-inline 허용)
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data:; "
                "connect-src 'self'; "
                "frame-ancestors 'none';"
            )

        # HSTS — production 에서만 활성화 (개발 환경 http 접속 차단 방지)
        if self._is_production:
            response.headers["Strict-Transport-Security"] = (
                f"max-age={_HSTS_MAX_AGE}; includeSubDomains"
            )

        return response
