"""prediction_service.py fallback 로직 확장 테스트 (9개)."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from backend.app.services.prediction_service import (
    generate_alert_report_http,
    get_risk_prediction,
    get_tft_forecast,
)


# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------

def _make_mock_client(method: str = "get", response_data: dict | None = None,
                      side_effect=None) -> AsyncMock:
    """httpx.AsyncClient 컨텍스트 매니저 mock 생성."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = response_data or {"result": "ok"}
    mock_resp.raise_for_status = MagicMock()

    mock_client = AsyncMock()
    if side_effect is not None:
        getattr(mock_client, method).side_effect = side_effect
    else:
        getattr(mock_client, method).return_value = mock_resp

    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    return mock_client


# ---------------------------------------------------------------------------
# get_risk_prediction
# ---------------------------------------------------------------------------

async def test_get_risk_prediction_success() -> None:
    """200 응답 → dict 반환 (fallback 없음)."""
    mock_client = _make_mock_client("get", response_data={"risk_score": 0.72})
    with patch("backend.app.services.prediction_service.httpx.AsyncClient", return_value=mock_client):
        result = await get_risk_prediction(0.5, 0.6, 0.7, 15.0, 60.0, "서울특별시")
    assert result["risk_score"] == 0.72
    assert "fallback" not in result


async def test_get_risk_prediction_timeout() -> None:
    """TimeoutException → fallback dict 반환."""
    mock_client = _make_mock_client("get", side_effect=httpx.TimeoutException("timeout"))
    with patch("backend.app.services.prediction_service.httpx.AsyncClient", return_value=mock_client):
        result = await get_risk_prediction(0.5, 0.6, 0.7, 15.0, 60.0, "서울특별시")
    assert result["fallback"] is True
    assert result["region"] == "서울특별시"


async def test_get_risk_prediction_connect_error() -> None:
    """ConnectError → fallback dict 반환."""
    mock_client = _make_mock_client("get", side_effect=httpx.ConnectError("refused"))
    with patch("backend.app.services.prediction_service.httpx.AsyncClient", return_value=mock_client):
        result = await get_risk_prediction(0.5, 0.6, 0.7, 15.0, 60.0, "부산광역시")
    assert result["fallback"] is True
    assert result["region"] == "부산광역시"


async def test_get_risk_prediction_http_error() -> None:
    """HTTPStatusError → fallback dict 반환."""
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500", request=MagicMock(), response=MagicMock()
    )
    mock_client = AsyncMock()
    mock_client.get = AsyncMock(return_value=mock_resp)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)

    with patch("backend.app.services.prediction_service.httpx.AsyncClient", return_value=mock_client):
        result = await get_risk_prediction(0.5, 0.6, 0.7, 15.0, 60.0, "대구광역시")
    assert result["fallback"] is True
    assert "error" in result


# ---------------------------------------------------------------------------
# get_tft_forecast
# ---------------------------------------------------------------------------

async def test_get_tft_forecast_success() -> None:
    """200 응답 → TFT 예측 dict 반환."""
    mock_client = _make_mock_client("post", response_data={"forecast": [1.2, 1.5, 1.8]})
    with patch("backend.app.services.prediction_service.httpx.AsyncClient", return_value=mock_client):
        result = await get_tft_forecast("서울특별시")
    assert result["forecast"] == [1.2, 1.5, 1.8]
    assert "fallback" not in result


async def test_get_tft_forecast_timeout() -> None:
    """TimeoutException → fallback dict 반환."""
    mock_client = _make_mock_client("post", side_effect=httpx.TimeoutException("tft timeout"))
    with patch("backend.app.services.prediction_service.httpx.AsyncClient", return_value=mock_client):
        result = await get_tft_forecast("인천광역시")
    assert result["fallback"] is True
    assert result["region"] == "인천광역시"


# ---------------------------------------------------------------------------
# generate_alert_report_http
# ---------------------------------------------------------------------------

async def test_generate_alert_report_success() -> None:
    """200 POST 응답 → 리포트 dict 반환."""
    mock_client = _make_mock_client("post", response_data={"report": "경보 리포트 내용"})
    with patch("backend.app.services.prediction_service.httpx.AsyncClient", return_value=mock_client):
        result = await generate_alert_report_http("서울특별시", {"l1": 62.5, "l2": 71.0})
    assert result["report"] == "경보 리포트 내용"
    assert "fallback" not in result


async def test_generate_alert_report_timeout() -> None:
    """TimeoutException → fallback dict 반환."""
    mock_client = _make_mock_client("post", side_effect=httpx.TimeoutException("report timeout"))
    with patch("backend.app.services.prediction_service.httpx.AsyncClient", return_value=mock_client):
        result = await generate_alert_report_http("경기도", {"l1": 55.0})
    assert result["fallback"] is True
    assert result["region"] == "경기도"


async def test_generate_alert_report_connect_error() -> None:
    """ConnectError → fallback dict 반환 (signals 포함)."""
    signals = {"l1": 80.0, "l2": 75.0, "l3": 60.0}
    mock_client = _make_mock_client("post", side_effect=httpx.ConnectError("no route"))
    with patch("backend.app.services.prediction_service.httpx.AsyncClient", return_value=mock_client):
        result = await generate_alert_report_http("전라남도", signals)
    assert result["fallback"] is True
    assert result["region"] == "전라남도"
    assert result["signals"] == signals
