"""예측 API."""
from fastapi import APIRouter, HTTPException, Query

from ..services.prediction_service import get_anomaly_result, get_tft_forecast

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


@router.get("/forecast")
async def get_forecast(
    region: str = Query("서울특별시"),
    horizon: int = Query(14, ge=1, le=90),
) -> dict:
    """TFT 모델 예측 결과 반환."""
    try:
        result = await get_tft_forecast(region)
        return {**result, "horizon_days": horizon}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ML 서비스 연결 불가: {e}") from e


@router.get("/anomaly")
async def get_anomaly(region: str = Query("서울특별시")) -> dict:
    """Autoencoder 이상탐지 결과 반환."""
    try:
        return await get_anomaly_result(region)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"ML 서비스 연결 불가: {e}") from e
