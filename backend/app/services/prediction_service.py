"""예측 서비스 — ML 모듈과 Backend 연동."""
from __future__ import annotations

import logging

import httpx

from ..config import settings

logger = logging.getLogger(__name__)

ML_SERVICE_URL = settings.ml_service_url


async def get_risk_prediction(
    l1: float = 50.0,
    l2: float = 50.0,
    l3: float = 50.0,
    temperature: float = 15.0,
    humidity: float = 50.0,
    region: str = "서울특별시",
) -> dict:
    """ML 서비스에서 XGBoost 위험도 예측 결과를 받아온다."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                f"{ML_SERVICE_URL}/predict/risk",
                params={
                    "l1": l1, "l2": l2, "l3": l3,
                    "temperature": temperature, "humidity": humidity,
                    "region": region,
                },
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
        logger.warning("ML service unavailable for %s: %s", region, e)
        return {"error": "ML service unavailable", "fallback": True, "region": region}


async def get_tft_forecast(region: str) -> dict:
    """ML 서비스에서 TFT 예측 결과를 받아온다."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{ML_SERVICE_URL}/predict/tft-7d",
                json={"region": region},
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
        logger.warning("ML service unavailable (TFT) for %s: %s", region, e)
        return {"error": "ML service unavailable", "fallback": True, "region": region}


async def generate_alert_report_http(region: str, signals: dict) -> dict:
    """ML 서비스에서 RAG-LLM 경보 리포트를 생성한다."""
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{ML_SERVICE_URL}/report/generate",
                json={"region": region, "signals": signals},
            )
            resp.raise_for_status()
            return resp.json()
    except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError) as e:
        logger.warning("ML service unavailable (report) for %s: %s", region, e)
        return {"error": "ML service unavailable", "fallback": True, "region": region, "signals": signals}
