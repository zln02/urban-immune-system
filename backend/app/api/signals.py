from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.get("/latest")
async def get_latest_signals(db: AsyncSession = Depends(get_db)) -> dict:
    query = text(
        """
        SELECT layer, region, value, time
        FROM layer_signals
        WHERE time >= NOW() - INTERVAL '7 days'
        ORDER BY time DESC
        LIMIT 100
        """
    )
    result = await db.execute(query)
    rows = result.mappings().all()
    return {"data": [dict(row) for row in rows], "count": len(rows)}


@router.get("/timeseries")
async def get_timeseries(
    layer: str = Query(..., pattern="^(otc|wastewater|search)$"),
    region: str = Query("서울", min_length=2, max_length=100),
    days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    query = text(
        """
        SELECT time, value
        FROM layer_signals
        WHERE layer = :layer AND region = :region
          AND time >= NOW() - make_interval(days => :days)
        ORDER BY time
        """
    )
    result = await db.execute(query, {"layer": layer, "region": region, "days": days})
    rows = result.mappings().all()
    return {"layer": layer, "region": region, "data": [dict(row) for row in rows]}
