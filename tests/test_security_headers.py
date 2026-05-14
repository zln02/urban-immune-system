"""SecurityHeadersMiddleware + config production validator 단위 테스트 (ISMS-P 2.10.1)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

pytest.importorskip("starlette")
pytest.importorskip("pydantic_settings")


# ── SecurityHeadersMiddleware ──────────────────────────────────────────────────

from backend.app.middleware.security_headers import SecurityHeadersMiddleware


def _make_fake_response(headers: dict | None = None) -> MagicMock:
    """테스트용 응답 MagicMock — headers dict 에 직접 할당 허용."""
    resp = MagicMock()
    resp.headers = headers or {}
    return resp


async def _dispatch(mw: SecurityHeadersMiddleware, response: MagicMock) -> MagicMock:
    """미들웨어 dispatch 를 직접 호출하는 헬퍼."""
    call_next = AsyncMock(return_value=response)
    request = MagicMock()
    return await mw.dispatch(request, call_next)


@pytest.mark.asyncio
async def test_security_headers_development_mode() -> None:
    """개발 환경: 기본 보안 헤더 6종 추가, HSTS 없음."""
    mw = SecurityHeadersMiddleware(app=MagicMock(), environment="development")
    resp = _make_fake_response()
    result = await _dispatch(mw, resp)

    assert result.headers["X-Content-Type-Options"] == "nosniff"
    assert result.headers["X-Frame-Options"] == "DENY"
    assert result.headers["X-XSS-Protection"] == "1; mode=block"
    assert "strict-origin-when-cross-origin" in result.headers["Referrer-Policy"]
    assert "geolocation=()" in result.headers["Permissions-Policy"]
    assert "default-src" in result.headers["Content-Security-Policy"]
    # HSTS 는 개발 환경에서 없어야 함
    assert "Strict-Transport-Security" not in result.headers


@pytest.mark.asyncio
async def test_security_headers_production_hsts() -> None:
    """프로덕션 환경: HSTS 헤더 포함."""
    mw = SecurityHeadersMiddleware(app=MagicMock(), environment="production")
    resp = _make_fake_response()
    result = await _dispatch(mw, resp)

    hsts = result.headers.get("Strict-Transport-Security", "")
    assert "max-age=31536000" in hsts
    assert "includeSubDomains" in hsts


@pytest.mark.asyncio
async def test_security_headers_frame_ancestors_deny() -> None:
    """CSP 에 frame-ancestors 'none' 포함 (Clickjacking 이중 방어)."""
    mw = SecurityHeadersMiddleware(app=MagicMock(), environment="development")
    resp = _make_fake_response()
    result = await _dispatch(mw, resp)

    csp = result.headers.get("Content-Security-Policy", "")
    assert "frame-ancestors 'none'" in csp


# ── config.py production validators (pass-2 추가분) ─────────────────────────

from backend.app.config import Settings


def _prod_base() -> dict:
    """production 통과 기본 kwargs."""
    return {
        "environment": "production",
        "database_url": "postgresql+asyncpg://uis:strongpass@db:5432/uis",
        "ml_service_url": "https://ml:8001",
        "api_keys": ["prod-api-key-1"],
        "anthropic_api_key": "sk-ant-testkey123",
        "allowed_origins": ["https://uis.example.com"],
    }


def test_production_rejects_missing_anthropic_key() -> None:
    """ISMS-P 2.10.1 — ANTHROPIC_API_KEY 누락 시 production 기동 거부."""
    kwargs = _prod_base()
    kwargs["anthropic_api_key"] = ""
    with pytest.raises(ValueError, match="anthropic_api_key"):
        Settings(**kwargs)


def test_production_rejects_cors_wildcard() -> None:
    """ISMS-P 2.10.1 — CORS allow_origins='*' production 거부."""
    kwargs = _prod_base()
    kwargs["allowed_origins"] = ["*"]
    with pytest.raises(ValueError, match="CORS"):
        Settings(**kwargs)


def test_production_allows_valid_settings() -> None:
    """유효한 production 설정은 통과해야 함."""
    settings = Settings(**_prod_base())
    assert settings.environment == "production"
    assert settings.anthropic_api_key == "sk-ant-testkey123"


# ── validate_region ─────────────────────────────────────────────────────────

from fastapi import HTTPException

from backend.app.api._validators import VALID_REGIONS, validate_region


def test_validate_region_valid() -> None:
    """17개 시·도는 그대로 반환."""
    for region in VALID_REGIONS:
        assert validate_region(region) == region


def test_validate_region_invalid() -> None:
    """허용 목록 외 지역명은 HTTPException 422 반환."""
    with pytest.raises(HTTPException) as exc_info:
        validate_region("InvalidCity")
    assert exc_info.value.status_code == 422
    assert "유효하지 않은 지역" in exc_info.value.detail


def test_validate_region_injection_attempt() -> None:
    """SQL 인젝션성 입력도 422 처리 (허용 목록 초과)."""
    with pytest.raises(HTTPException) as exc_info:
        validate_region("'; DROP TABLE layer_signals;--")
    assert exc_info.value.status_code == 422


def test_valid_regions_count() -> None:
    """정확히 17개 지역이 등록돼 있어야 함."""
    assert len(VALID_REGIONS) == 17
