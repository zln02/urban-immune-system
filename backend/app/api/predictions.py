from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


@router.get("/forecast")
async def get_forecast(horizon: int = Query(14, ge=7, le=21)) -> dict:
    # Phase 2: TFT 모델 서빙 연동
    return {
        "horizon_days": horizon,
        "status": "model_not_loaded",
        "message": "TFT 모델 체크포인트 로드 후 예측 가능",
    }
