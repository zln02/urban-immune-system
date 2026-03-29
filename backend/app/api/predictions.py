"""TFT 예측 결과 API."""
from fastapi import APIRouter, Query

router = APIRouter()

HORIZONS = [7, 14, 21]


@router.get("/forecast")
async def get_forecast(
    region: str = Query("서울특별시"),
) -> dict:
    """7/14/21일 인플루엔자 위험도 예측값 반환."""
    # TODO: ml/ 서비스에서 TFT 추론 결과 조회
    return {
        "region": region,
        "horizons": HORIZONS,
        "forecasts": {h: None for h in HORIZONS},
        "confidence_intervals": {},
        "attention_weights": {},
    }


@router.get("/anomaly")
async def get_anomaly_status(
    region: str = Query("서울특별시"),
) -> dict:
    """Deep Autoencoder 이상탐지 결과 반환."""
    # TODO: ml/ Autoencoder reconstruction error → threshold 판정
    return {
        "region": region,
        "is_anomaly": False,
        "reconstruction_error": None,
        "threshold": None,
        "layers_triggered": [],
    }
