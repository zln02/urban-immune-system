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


async def get_risk_prediction(
    l1: float = 50.0,
    l2: float = 50.0,
    l3: float = 50.0,
    temperature: float = 15.0,
    humidity: float = 50.0,
    region: str = "서울특별시",
) -> dict:
    """ML 서비스에서 XGBoost 위험도 예측 결과를 받아온다."""
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
