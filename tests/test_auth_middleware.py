"""backend/app/middleware/auth.py 단위 테스트."""
from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.app.middleware.auth import APIKeyAuthMiddleware


def _make_middleware(api_keys: list[str], environment: str = "development") -> APIKeyAuthMiddleware:
    """테스트용 미들웨어 인스턴스 생성 (app=None 허용)."""
    mw = APIKeyAuthMiddleware.__new__(APIKeyAuthMiddleware)
    mw._keys = [k for k in api_keys if k]
    mw._is_production = environment.lower() == "production"
    mw._header = "X-API-Key"
    return mw


def _make_request(path: str, api_key: str | None = None) -> MagicMock:
    req = MagicMock()
    req.url.path = path
    if api_key is not None:
        req.headers = {APIKeyAuthMiddleware.__dict__["_header"] if "_header" in APIKeyAuthMiddleware.__dict__ else "X-API-Key": api_key}
        req.headers.get = lambda h, default="": api_key if h == "X-API-Key" else default
    else:
        req.headers.get = lambda h, default="": default
    return req


@pytest.mark.asyncio
async def test_public_path_passes_without_key() -> None:
    """공개 경로(/health 등)는 API 키 없이 통과."""
    mw = _make_middleware(api_keys=["secret-key"], environment="production")
    call_next = AsyncMock(return_value=MagicMock(status_code=200))

    req = _make_request("/health")
    resp = await mw.dispatch(req, call_next)
    call_next.assert_called_once_with(req)


@pytest.mark.asyncio
async def test_docs_path_passes() -> None:
    """/docs 로 시작하는 경로는 키 없이 통과."""
    mw = _make_middleware(api_keys=["secret-key"], environment="production")
    call_next = AsyncMock(return_value=MagicMock(status_code=200))

    req = _make_request("/docs/something")
    resp = await mw.dispatch(req, call_next)
    call_next.assert_called_once_with(req)


@pytest.mark.asyncio
async def test_development_no_keys_passes() -> None:
    """개발 환경에서 키 미등록 시 모든 요청 통과."""
    mw = _make_middleware(api_keys=[], environment="development")
    call_next = AsyncMock(return_value=MagicMock(status_code=200))

    req = _make_request("/api/v1/alerts")
    resp = await mw.dispatch(req, call_next)
    call_next.assert_called_once_with(req)


@pytest.mark.asyncio
async def test_valid_key_passes() -> None:
    """올바른 API 키로 인증 통과."""
    mw = _make_middleware(api_keys=["my-secret"], environment="production")
    call_next = AsyncMock(return_value=MagicMock(status_code=200))

    req = _make_request("/api/v1/signals")
    req.headers.get = lambda h, default="": "my-secret" if h == "X-API-Key" else default
    resp = await mw.dispatch(req, call_next)
    call_next.assert_called_once_with(req)


@pytest.mark.asyncio
async def test_invalid_key_returns_401() -> None:
    """잘못된 API 키로 401 반환."""
    from starlette.responses import JSONResponse

    mw = _make_middleware(api_keys=["my-secret"], environment="production")
    call_next = AsyncMock()

    req = _make_request("/api/v1/signals")
    req.headers.get = lambda h, default="": "wrong-key" if h == "X-API-Key" else default
    resp = await mw.dispatch(req, call_next)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 401
    call_next.assert_not_called()


@pytest.mark.asyncio
async def test_missing_key_returns_401() -> None:
    """키 미제공 시 401 반환."""
    from starlette.responses import JSONResponse

    mw = _make_middleware(api_keys=["my-secret"], environment="production")
    call_next = AsyncMock()

    req = _make_request("/api/v1/signals")
    req.headers.get = lambda h, default="": default  # 키 없음
    resp = await mw.dispatch(req, call_next)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# search_collector deprecated 동작 확인
# ---------------------------------------------------------------------------

def test_collect_search_weekly_raises_runtime_error() -> None:
    """deprecated collect_search_weekly 호출 시 RuntimeError 발생."""
    from pipeline.collectors.search_collector import collect_search_weekly

    with pytest.raises(RuntimeError, match="deprecated"):
        collect_search_weekly()
