"""alert_reports 및 risk_scores DB 조회/저장 서비스."""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_latest_alert(region: str, db: AsyncSession) -> dict | None:
    result = await db.execute(
        text("""
            SELECT region, alert_level, summary, recommendations, model_used, created_at
            FROM alert_reports
            WHERE region = :region
            ORDER BY created_at DESC
            LIMIT 1
        """),
        {"region": region},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def get_latest_risk_score(region: str, db: AsyncSession) -> dict | None:
    result = await db.execute(
        text("""
            SELECT time, region, composite_score, l1_score, l2_score, l3_score, alert_level
            FROM risk_scores
            WHERE region = :region
            ORDER BY time DESC
            LIMIT 1
        """),
        {"region": region},
    )
    row = result.mappings().first()
    return dict(row) if row else None


async def save_alert_report(data: dict, db: AsyncSession) -> int:
    result = await db.execute(
        text("""
            INSERT INTO alert_reports (time, region, alert_level, summary, recommendations, model_used)
            VALUES (NOW(), :region, :alert_level, :summary, :recommendations, :model_used)
            RETURNING id
        """),
        {
            "region": data["region"],
            "alert_level": data.get("alert_level", "GREEN"),
            "summary": data.get("summary", ""),
            "recommendations": data.get("recommendations"),
            "model_used": data.get("model_used"),
        },
    )
    await db.commit()
    row = result.first()
    return row[0] if row else -1
