"""Backend API 클라이언트 — Streamlit에서 FastAPI 호출."""
from __future__ import annotations

import logging
import os

import requests

logger = logging.getLogger(__name__)

API_BASE = os.getenv("UIS_API_URL", "http://localhost:8000")


def _get(endpoint: str, params: dict | None = None) -> dict | None:
    """GET 요청 래퍼. 실패 시 None 반환 (시뮬레이션 fallback용)."""
    try:
        resp = requests.get(f"{API_BASE}{endpoint}", params=params, timeout=5.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.warning("API 호출 실패 (%s): %s", endpoint, exc)
        return None


def get_latest_signals() -> dict | None:
    """최신 신호 데이터 조회."""
    return _get("/api/v1/signals/latest")


def get_timeseries(layer: str, region: str = "서울특별시", days: int = 90) -> dict | None:
    """시계열 데이터 조회."""
    return _get("/api/v1/signals/timeseries", {"layer": layer, "region": region, "days": days})


def get_current_alert(region: str = "서울특별시") -> dict | None:
    """현재 경보 상태 조회."""
    return _get("/api/v1/alerts/current", {"region": region})


def get_forecast(region: str = "서울특별시") -> dict | None:
    """위험도 예측 조회."""
    return _get("/api/v1/predictions/forecast", {"region": region})
