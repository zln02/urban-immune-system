"""Layer 신호 조회 API."""
from datetime import datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Query

router = APIRouter()


@router.get("/latest")
async def get_latest_signals(
    region: str = Query("서울특별시", description="지역명"),
    layer: Literal["L1", "L2", "L3", "ALL"] = Query("ALL"),
) -> dict:
    """각 Layer 최신 정규화 신호값 반환."""
    # TODO: TimescaleDB에서 실제 데이터 조회
    return {
        "region": region,
        "layer": layer,
        "data": [],
        "updated_at": datetime.utcnow().isoformat(),
    }


@router.get("/timeseries")
async def get_timeseries(
    region: str = Query("서울특별시"),
    layer: str = Query("ALL"),
    weeks: int = Query(12, ge=1, le=52),
) -> dict:
    """주간 시계열 데이터 반환 (차트용)."""
    since = datetime.utcnow() - timedelta(weeks=weeks)
    # TODO: TimescaleDB time_bucket('1 week', ...) 쿼리
    return {
        "region": region,
        "layer": layer,
        "since": since.isoformat(),
        "series": [],
    }
