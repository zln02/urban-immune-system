from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


@router.get("/forecast")
async def get_forecast(horizon: int = 14) -> dict:
    # Phase 2: TFT 모델 서빙 연동
    return {
        "horizon_days": horizon,
        "status": "model_not_loaded",
        "message": "TFT 모델 체크포인트 로드 후 예측 가능",
    }
