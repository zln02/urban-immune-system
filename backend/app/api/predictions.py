"""예측 API — ML 서비스 연동."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.prediction_service import get_risk_prediction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])


@router.get("/forecast")
async def get_forecast(
    region: str = Query("서울특별시", min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """ML 모델 기반 위험도 예측."""
    # Get latest signals from DB
    query = text("""
        SELECT DISTINCT ON (layer) layer, value
        FROM layer_signals
        WHERE region = :region AND layer IN ('L1', 'L2', 'L3', 'AUX')
        ORDER BY layer, time DESC
    """)
    result = await db.execute(query, {"region": region})
    signals = {r["layer"]: r["value"] for r in result.mappings().all()}

    if not signals:
        return {
            "region": region,
            "status": "no_data",
            "message": "DB에 신호 데이터가 없습니다. 수집기를 먼저 실행하세요.",
        }

    # Call ML service
    try:
        prediction = await get_risk_prediction(
            l1=signals.get("L1", 50.0),
            l2=signals.get("L2", 50.0),
            l3=signals.get("L3", 50.0),
            temperature=signals.get("AUX", 15.0),
            region=region,
        )
        return prediction
    except Exception as exc:
        logger.error("ML 서비스 호출 실패: %s", exc)
        # Fallback: simple weighted average
        l1 = signals.get("L1", 0.0)
        l2 = signals.get("L2", 0.0)
        l3 = signals.get("L3", 0.0)
        score = round(0.35 * l1 + 0.40 * l2 + 0.25 * l3, 2)
        level = "GREEN" if score < 30 else "YELLOW" if score < 55 else "RED"
        return {
            "region": region,
            "status": "fallback",
            "composite_score": score,
            "alert_level": level,
            "message": "ML 서비스 미연결, 가중평균 fallback 사용",
        }
