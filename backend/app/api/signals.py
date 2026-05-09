from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/signals", tags=["signals"])


@router.get("/latest")
async def get_latest_signals(db: AsyncSession = Depends(get_db)) -> dict:
    query = text(
        """
        SELECT layer, region, value, time
        FROM layer_signals
        WHERE time >= NOW() - INTERVAL '30 days'
        ORDER BY time DESC
        LIMIT 100
        """
    )
    try:
        result = await db.execute(query)
        rows = result.mappings().all()
    except (SQLAlchemyError, asyncio.TimeoutError) as exc:
        logger.exception("signals/latest DB query failed")
        raise HTTPException(status_code=503, detail="signals store unavailable") from exc
    return {"data": [dict(row) for row in rows], "count": len(rows)}


@router.get("/timeseries")
async def get_timeseries(
    layer: str = Query(..., pattern="^(otc|wastewater|search|composite)$"),
    region: str = Query("서울특별시", min_length=2, max_length=100),
    days: int = Query(90, ge=7, le=365),
    pathogen: str = Query("influenza", pattern="^(influenza|covid|norovirus)$"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    if layer == "composite":
        # L1*0.35 + L2*0.40 + L3*0.25 가중합 (backend/app/config.py canonical 가중치)
        query = text(
            """
            SELECT time,
              COALESCE(0.35 * MAX(CASE WHEN layer='otc'        THEN value END), 0) +
              COALESCE(0.40 * MAX(CASE WHEN layer='wastewater' THEN value END), 0) +
              COALESCE(0.25 * MAX(CASE WHEN layer='search'     THEN value END), 0) AS value
            FROM layer_signals
            WHERE layer IN ('otc', 'wastewater', 'search')
              AND region = :region AND pathogen = :pathogen
              AND time >= NOW() - make_interval(days => :days)
            GROUP BY time
            ORDER BY time
            """
        )
    else:
        # 같은 (time, region, pathogen) 중복 row 제거 + 단일 병원체로 한정.
        query = text(
            """
            SELECT time, AVG(value)::float AS value
            FROM layer_signals
            WHERE layer = :layer AND region = :region
              AND pathogen = :pathogen
              AND time >= NOW() - make_interval(days => :days)
            GROUP BY time
            ORDER BY time
            """
        )
    try:
        result = await db.execute(
            query,
            {"layer": layer, "region": region, "days": days, "pathogen": pathogen},
        )
        rows = result.mappings().all()
    except (SQLAlchemyError, asyncio.TimeoutError) as exc:
        logger.exception(
            "signals/timeseries DB query failed (layer=%s, region=%s)", layer, region
        )
        raise HTTPException(status_code=503, detail="signals store unavailable") from exc
    return {
        "layer": layer,
        "region": region,
        "pathogen": pathogen,
        "data": [dict(row) for row in rows],
    }
