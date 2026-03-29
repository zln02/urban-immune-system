"""예측 서비스 — ML 모듈과 Backend 연동."""
from __future__ import annotations

import httpx

ML_SERVICE_URL = "http://ml:8001"


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
