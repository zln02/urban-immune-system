"""예측 API — ML 서비스 연동 + DB fallback."""
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
    """ML 모델 기반 위험도 예측 (ML 서비스 미연결 시 가중평균 fallback).

    최근 28일 평균(value > 0)으로 단일 시점 noise를 흡수.
    """
    query = text("""
        SELECT layer, AVG(value) AS value
        FROM layer_signals
        WHERE region = :region
          AND layer IN ('otc', 'wastewater', 'search', 'aux')
          AND time >= NOW() - INTERVAL '28 days'
          AND value > 0
        GROUP BY layer
    """)
    result = await db.execute(query, {"region": region})
    signals = {r["layer"]: float(r["value"]) for r in result.mappings().all()}

    if not signals:
        return {
            "region": region,
            "status": "no_data",
            "message": "DB에 신호 데이터가 없습니다. 수집기를 먼저 실행하세요.",
        }

    l1 = signals.get("otc", 0.0)
    l2 = signals.get("wastewater", 0.0)
    l3 = signals.get("search", 0.0)
    aux = signals.get("aux", 15.0)

    try:
        return await get_risk_prediction(
            l1=l1, l2=l2, l3=l3, temperature=aux, region=region,
        )
    except Exception as exc:
        logger.warning("ML 서비스 미연결, fallback 사용: %s", exc)
        score = round(0.35 * l1 + 0.40 * l2 + 0.25 * l3, 2)
        level = "GREEN" if score < 30 else "YELLOW" if score < 55 else "RED"
        return {
            "region": region,
            "status": "fallback",
            "composite_score": score,
            "alert_level": level,
            "l1_score": l1,
            "l2_score": l2,
            "l3_score": l3,
            "message": "ML 서비스 미연결 — 가중평균 fallback",
        }
