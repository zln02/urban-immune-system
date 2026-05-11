"""backend/app/api/signals.py 단위 테스트.

FastAPI dependency_overrides 패턴으로 실제 DB 연결 없이
GET /api/v1/signals/latest, GET /api/v1/signals/timeseries 양 라우트의
정상·빈 데이터·DB 에러(503) 경로를 커버한다.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.exc import SQLAlchemyError
from starlette.testclient import TestClient


# ---------------------------------------------------------------------------
# 헬퍼: 가짜 AsyncSession
# ---------------------------------------------------------------------------

class _FakeMapping(dict):
    """dict-like row 객체."""


class _FakeResult:
    """AsyncSession.execute() 반환값을 흉내 내는 객체."""

    def __init__(self, rows: list[dict]):
        self._rows = rows

    def mappings(self) -> "_FakeResult":
        return self

    def all(self) -> list[_FakeMapping]:
        return [_FakeMapping(r) for r in self._rows]


def _make_session(rows: list[dict]) -> AsyncMock:
    """rows 를 반환하는 mock AsyncSession 생성."""
    session = AsyncMock()
    result = _FakeResult(rows)
    session.execute.return_value = result
    return session


def _make_error_session(exc: Exception) -> AsyncMock:
    """execute() 호출 시 예외를 발생시키는 mock AsyncSession."""
    session = AsyncMock()
    session.execute.side_effect = exc
    return session


# ---------------------------------------------------------------------------
# 픽스처: broker mock + TestClient 팩토리
# ---------------------------------------------------------------------------

def _make_client(mock_session: AsyncMock) -> TestClient:
    """DB 의존성을 override 한 TestClient 반환."""
    from backend.app.database import get_db
    from backend.app.main import app

    async def _override_get_db():
        yield mock_session

    app.dependency_overrides[get_db] = _override_get_db
    client = TestClient(app, raise_server_exceptions=False)
    return client


def _clear_overrides() -> None:
    from backend.app.main import app
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# GET /api/v1/signals/latest
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def patch_broker():
    """broker startup/shutdown 을 테스트 전 구간에서 mock 처리."""
    with patch("backend.app.tasks.broker.startup", new_callable=AsyncMock), \
         patch("backend.app.tasks.broker.shutdown", new_callable=AsyncMock):
        yield


def test_get_latest_signals_normal():
    """정상 데이터 반환 시 200 + data 배열 + count 확인."""
    rows = [
        {"layer": "otc",        "region": "서울특별시", "value": 55.0, "time": "2026-04-01T00:00:00"},
        {"layer": "wastewater", "region": "서울특별시", "value": 70.0, "time": "2026-04-01T00:00:00"},
    ]
    session = _make_session(rows)
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/latest")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert "data" in body
    assert "count" in body
    assert body["count"] == 2
    assert len(body["data"]) == 2


def test_get_latest_signals_empty():
    """DB 에 행 없을 때 200 + 빈 data 배열 + count=0."""
    session = _make_session([])
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/latest")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["data"] == []
    assert body["count"] == 0


def test_get_latest_signals_db_error_returns_503():
    """SQLAlchemyError 발생 시 503 반환."""
    session = _make_error_session(SQLAlchemyError("db down"))
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/latest")
    finally:
        _clear_overrides()

    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"]


def test_get_latest_signals_timeout_returns_503():
    """asyncio.TimeoutError 발생 시 503 반환."""
    session = _make_error_session(asyncio.TimeoutError())
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/latest")
    finally:
        _clear_overrides()

    assert resp.status_code == 503


def test_get_latest_signals_data_fields():
    """반환 row 에 layer·region·value·time 필드가 포함되는지 확인."""
    rows = [
        {"layer": "search", "region": "부산광역시", "value": 42.0, "time": "2026-03-15T00:00:00"},
    ]
    session = _make_session(rows)
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/latest")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    row = resp.json()["data"][0]
    assert row["layer"] == "search"
    assert row["region"] == "부산광역시"
    assert row["value"] == 42.0


# ---------------------------------------------------------------------------
# GET /api/v1/signals/timeseries — 유효성 검증 (쿼리 파라미터)
# ---------------------------------------------------------------------------

def test_timeseries_missing_layer_returns_422():
    """layer 파라미터 누락 시 422 Unprocessable Entity."""
    session = _make_session([])
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/timeseries?region=서울특별시&days=30&pathogen=influenza")
    finally:
        _clear_overrides()

    assert resp.status_code == 422


def test_timeseries_invalid_layer_returns_422():
    """layer 값이 패턴 불일치(invalid) → 422."""
    session = _make_session([])
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/timeseries?layer=invalid&region=서울특별시&days=30&pathogen=influenza")
    finally:
        _clear_overrides()

    assert resp.status_code == 422


def test_timeseries_invalid_pathogen_returns_422():
    """pathogen 값이 패턴 불일치 → 422."""
    session = _make_session([])
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/timeseries?layer=otc&region=서울특별시&days=30&pathogen=sars")
    finally:
        _clear_overrides()

    assert resp.status_code == 422


def test_timeseries_days_below_min_returns_422():
    """days < 7 → 422."""
    session = _make_session([])
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/timeseries?layer=otc&region=서울특별시&days=3&pathogen=influenza")
    finally:
        _clear_overrides()

    assert resp.status_code == 422


def test_timeseries_days_above_max_returns_422():
    """days > 365 → 422."""
    session = _make_session([])
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/timeseries?layer=otc&region=서울특별시&days=400&pathogen=influenza")
    finally:
        _clear_overrides()

    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/signals/timeseries — 정상·빈 데이터·에러 경로
# ---------------------------------------------------------------------------

def test_timeseries_otc_normal():
    """layer=otc, 정상 데이터 → 200 + 응답 스키마 확인."""
    rows = [
        {"time": "2026-03-01T00:00:00", "value": 55.5},
        {"time": "2026-03-08T00:00:00", "value": 60.1},
    ]
    session = _make_session(rows)
    client = _make_client(session)
    try:
        resp = client.get(
            "/api/v1/signals/timeseries?layer=otc&region=서울특별시&days=90&pathogen=influenza"
        )
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["layer"] == "otc"
    assert body["region"] == "서울특별시"
    assert body["pathogen"] == "influenza"
    assert len(body["data"]) == 2


def test_timeseries_wastewater_normal():
    """layer=wastewater, 정상 데이터 → 200."""
    rows = [{"time": "2026-03-01T00:00:00", "value": 71.0}]
    session = _make_session(rows)
    client = _make_client(session)
    try:
        resp = client.get(
            "/api/v1/signals/timeseries?layer=wastewater&region=부산광역시&days=30&pathogen=covid"
        )
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["layer"] == "wastewater"
    assert body["region"] == "부산광역시"
    assert body["pathogen"] == "covid"


def test_timeseries_search_normal():
    """layer=search, 정상 데이터 → 200."""
    rows = [{"time": "2026-03-01T00:00:00", "value": 48.3}]
    session = _make_session(rows)
    client = _make_client(session)
    try:
        resp = client.get(
            "/api/v1/signals/timeseries?layer=search&region=대구광역시&days=60&pathogen=norovirus"
        )
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["layer"] == "search"
    assert body["pathogen"] == "norovirus"


def test_timeseries_composite_normal():
    """layer=composite (가중합 쿼리 분기) → 200."""
    rows = [
        {"time": "2026-03-01T00:00:00", "value": 63.5},
        {"time": "2026-03-08T00:00:00", "value": 67.0},
    ]
    session = _make_session(rows)
    client = _make_client(session)
    try:
        resp = client.get(
            "/api/v1/signals/timeseries?layer=composite&region=서울특별시&days=90&pathogen=influenza"
        )
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["layer"] == "composite"
    assert len(body["data"]) == 2


def test_timeseries_empty_data():
    """결과 행 없음 → 200 + 빈 data 배열."""
    session = _make_session([])
    client = _make_client(session)
    try:
        resp = client.get(
            "/api/v1/signals/timeseries?layer=otc&region=제주특별자치도&days=7&pathogen=influenza"
        )
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    assert resp.json()["data"] == []


def test_timeseries_db_error_returns_503():
    """timeseries 쿼리 중 SQLAlchemyError → 503."""
    session = _make_error_session(SQLAlchemyError("connection lost"))
    client = _make_client(session)
    try:
        resp = client.get(
            "/api/v1/signals/timeseries?layer=otc&region=서울특별시&days=30&pathogen=influenza"
        )
    finally:
        _clear_overrides()

    assert resp.status_code == 503
    assert "unavailable" in resp.json()["detail"]


def test_timeseries_timeout_returns_503():
    """timeseries 쿼리 중 asyncio.TimeoutError → 503."""
    session = _make_error_session(asyncio.TimeoutError())
    client = _make_client(session)
    try:
        resp = client.get(
            "/api/v1/signals/timeseries?layer=wastewater&region=서울특별시&days=30&pathogen=influenza"
        )
    finally:
        _clear_overrides()

    assert resp.status_code == 503


def test_timeseries_composite_db_error_returns_503():
    """composite 분기에서도 503 fallback 동작."""
    session = _make_error_session(SQLAlchemyError("timeout"))
    client = _make_client(session)
    try:
        resp = client.get(
            "/api/v1/signals/timeseries?layer=composite&region=서울특별시&days=90&pathogen=influenza"
        )
    finally:
        _clear_overrides()

    assert resp.status_code == 503


def test_timeseries_default_region():
    """region 기본값 서울특별시 적용 — region 파라미터 생략 시 정상 처리."""
    rows = [{"time": "2026-03-01T00:00:00", "value": 50.0}]
    session = _make_session(rows)
    client = _make_client(session)
    try:
        # region 생략 → 기본값 "서울특별시"
        resp = client.get("/api/v1/signals/timeseries?layer=otc&pathogen=influenza&days=30")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["region"] == "서울특별시"


def test_timeseries_default_days():
    """days 기본값 90 적용 — days 파라미터 생략 시 정상 처리."""
    rows = [{"time": "2026-03-01T00:00:00", "value": 55.0}]
    session = _make_session(rows)
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/timeseries?layer=otc&pathogen=influenza")
    finally:
        _clear_overrides()

    assert resp.status_code == 200


def test_timeseries_default_pathogen():
    """pathogen 기본값 influenza 적용."""
    rows = [{"time": "2026-03-01T00:00:00", "value": 44.0}]
    session = _make_session(rows)
    client = _make_client(session)
    try:
        resp = client.get("/api/v1/signals/timeseries?layer=otc")
    finally:
        _clear_overrides()

    assert resp.status_code == 200
    body = resp.json()
    assert body["pathogen"] == "influenza"
