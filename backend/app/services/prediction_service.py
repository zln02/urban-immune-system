"""예측 서비스 — ML 모듈과 Backend 연동."""
from __future__ import annotations

import httpx

from ..config import settings

ML_SERVICE_URL = settings.ml_service_url


async def get_tft_forecast(region: str) -> dict:
    """ML 서비스에서 TFT 예측 결과를 받아온다."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{ML_SERVICE_URL}/predict/tft",
            params={"region": region},
        )
        resp.raise_for_status()
        return resp.json()


async def get_anomaly_result(region: str) -> dict:
    """ML 서비스에서 Autoencoder 이상탐지 결과를 받아온다."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{ML_SERVICE_URL}/predict/anomaly",
            params={"region": region},
        )
        resp.raise_for_status()
        return resp.json()


async def generate_alert_report_http(region: str, signals: dict) -> dict:
    """ML 서비스에서 RAG-LLM 경보 리포트를 생성한다."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{ML_SERVICE_URL}/report/generate",
            json={"region": region, "signals": signals},
        )
        resp.raise_for_status()
        return resp.json()
