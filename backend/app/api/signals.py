from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.get("/latest")
async def get_latest_signals(db: AsyncSession = Depends(get_db)) -> dict:
    query = text(
        """
        SELECT layer, region, value, recorded_at
        FROM signals
        WHERE recorded_at >= NOW() - INTERVAL '7 days'
        ORDER BY recorded_at DESC
        LIMIT 100
        """
    )
    result = await db.execute(query)
    rows = result.mappings().all()
    return {"data": [dict(row) for row in rows], "count": len(rows)}


@router.get("/timeseries")
async def get_timeseries(
    layer: str = Query(..., pattern="^(otc|wastewater|search)$"),
    region: str = Query("서울"),
    days: int = Query(90, ge=7, le=365),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if days < 7 or days > 365:
        raise HTTPException(status_code=400, detail="days must be between 7 and 365")

    query = text(
        """
        SELECT recorded_at, value
        FROM signals
        WHERE layer = :layer AND region = :region
          AND recorded_at >= NOW() - CAST((:days || ' days') AS INTERVAL)
        ORDER BY recorded_at
        """
    )
    result = await db.execute(query, {"layer": layer, "region": region, "days": str(days)})
    rows = result.mappings().all()
    return {"layer": layer, "region": region, "data": [dict(row) for row in rows]}
