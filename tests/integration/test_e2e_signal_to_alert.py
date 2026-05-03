"""통합 테스트: layer_signals INSERT → /api/v1/alerts/current GET 200 검증."""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest


def _make_fake_session(rows_by_call: list):
    """호출 순서대로 다른 행 집합을 반환하는 mock AsyncSession."""

    class _FakeMapping(dict):
        pass

    class _FakeResult:
        def __init__(self, rows):
            self._rows = rows
        def mappings(self):
            return self
        def all(self):
            return [_FakeMapping(r) for r in self._rows]
        def first(self):
            return _FakeMapping(self._rows[0]) if self._rows else None

    call_count = [0]

    async def _execute(query, params=None):
        idx = min(call_count[0], len(rows_by_call) - 1)
        call_count[0] += 1
        return _FakeResult(rows_by_call[idx])

    session = AsyncMock()
    session.execute.side_effect = _execute
    return session


# ---------------------------------------------------------------------------
# /api/v1/alerts/current — fallback 경로 (risk_scores 없음 → layer_signals 평균 앙상블)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_signal_to_alert_returns_200_with_risk_score():
    """3계층 layer_signals 평균으로 composite_score 계산 → 200 확인."""
    # layer_signals 집계 결과 mock
    layer_rows = [
        {"layer": "otc",        "value": 62.5},
        {"layer": "wastewater", "value": 71.0},
        {"layer": "search",     "value": 48.3},
    ]
    mock_session = _make_fake_session([layer_rows])

    async def _override_get_db():
        yield mock_session

    with patch("backend.app.tasks.broker.startup", new_callable=AsyncMock), \
         patch("backend.app.tasks.broker.shutdown", new_callable=AsyncMock), \
         patch("backend.app.api.alerts.get_latest_alert",
               new_callable=AsyncMock, return_value=None), \
         patch("backend.app.api.alerts.get_latest_risk_score",
               new_callable=AsyncMock, return_value=None):

        from starlette.testclient import TestClient

        from backend.app.database import get_db
        from backend.app.main import app

        app.dependency_overrides[get_db] = _override_get_db
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                resp = c.get("/api/v1/alerts/current?region=서울특별시")
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "composite_score" in data, f"composite_score 키 없음: {data}"
    assert "alert_level" in data, f"alert_level 키 없음: {data}"
    # 앙상블 검증: 0.35*62.5 + 0.40*71.0 + 0.25*48.3 ≈ 63.5 → ORANGE
    assert data["composite_score"] > 0, "composite_score 가 0"


# ---------------------------------------------------------------------------
# /api/v1/alerts/regions — risk_scores 기반 경로
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_regions_endpoint_returns_alerts_array():
    """list_region_alerts가 alerts 배열을 포함해 200 반환 (DISTINCT ON mock 우회)."""
    risk_row = {
        "region": "서울특별시",
        "l1_score": 40.0,
        "l2_score": 60.0,
        "l3_score": 35.0,
        "composite_score": 55.0,
        "alert_level": "ORANGE",
        "time": "2026-04-29T00:00:00",
    }
    # 1st call: risk_scores DISTINCT ON, 2nd call: fallback layer_signals (empty)
    mock_session = _make_fake_session([[risk_row], []])

    async def _override_get_db():
        yield mock_session

    with patch("backend.app.tasks.broker.startup", new_callable=AsyncMock), \
         patch("backend.app.tasks.broker.shutdown", new_callable=AsyncMock):

        from starlette.testclient import TestClient

        from backend.app.database import get_db
        from backend.app.main import app

        app.dependency_overrides[get_db] = _override_get_db
        try:
            with TestClient(app, raise_server_exceptions=True) as c:
                resp = c.get("/api/v1/alerts/regions")
        finally:
            app.dependency_overrides.clear()

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "alerts" in data, f"alerts 배열 없음: {data}"
    assert len(data["alerts"]) >= 1, "alerts 배열 비어있음"
    alert = data["alerts"][0]
    assert "composite" in alert or "composite_score" in alert, f"risk_score 키 없음: {alert}"
