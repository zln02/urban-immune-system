"""신호 데이터 API."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


class SignalItem(BaseModel):
    timestamp: datetime
    value: float
    raw_value: float | None
    source: str | None


class SignalsLatestResponse(BaseModel):
    region: str
    layer: str
    count: int
    signals: list[SignalItem]


class TimeseriesResponse(BaseModel):
    layer: str
    region: str
    data: list[dict]


@router.get("/latest", response_model=SignalsLatestResponse)
async def get_latest_signals(
    region: str = Query("서울특별시", min_length=2, max_length=100),
    layer: str = Query("L1", pattern="^(L1|L2|L3|AUX)$"),
    limit: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> SignalsLatestResponse:
    """TimescaleDB layer_signals 하이퍼테이블에서 최신 신호 반환."""
    result = await db.execute(
        text("""
            SELECT time, value, raw_value, source
            FROM layer_signals
            WHERE layer = :layer AND region = :region
            ORDER BY time DESC
            LIMIT :limit
        """),
        {"layer": layer, "region": region, "limit": limit},
    )
    rows = result.mappings().all()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail=f"{region} / {layer} 데이터 없음. 파이프라인 수집 여부를 확인하세요.",
        )

    return SignalsLatestResponse(
        region=region,
        layer=layer,
        count=len(rows),
        signals=[
            SignalItem(
                timestamp=row["time"],
                value=row["value"],
                raw_value=row["raw_value"],
                source=row["source"],
            )
            for row in rows
        ],
    )


@router.get("/timeseries", response_model=TimeseriesResponse)
async def get_timeseries(
    layer: str = Query(..., pattern="^(L1|L2|L3|AUX)$"),
    region: str = Query("서울특별시", min_length=2, max_length=100),
    days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
) -> TimeseriesResponse:
    """기간별 시계열 신호 반환."""
    result = await db.execute(
        text("""
            SELECT time AS recorded_at, value
            FROM layer_signals
            WHERE layer = :layer AND region = :region
              AND time >= NOW() - make_interval(days => :days)
            ORDER BY time
        """),
        {"layer": layer, "region": region, "days": days},
    )
    rows = result.mappings().all()
    return TimeseriesResponse(
        layer=layer,
        region=region,
        data=[dict(row) for row in rows],
    )
