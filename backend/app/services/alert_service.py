"""alert_reports 및 risk_scores DB 조회/저장 서비스."""
from __future__ import annotations

import json

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def get_latest_alert(region: str, db: AsyncSession) -> dict | None:
    result = await db.execute(
        text("""
            SELECT region, alert_level, summary, recommendations, model_used, created_at,
                   triggered_by, trigger_source, feature_values, rag_sources, model_metadata
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
    """alert_reports 테이블에 리포트 저장.

    감사로그(triggered_by, trigger_source) 및 XAI 메타데이터(feature_values, rag_sources,
    model_metadata) 컬럼을 포함하여 INSERT한다. 미전달 시 NULL 허용.
    """
    feature_values = data.get("feature_values")
    rag_sources = data.get("rag_sources")
    model_metadata = data.get("model_metadata")

    result = await db.execute(
        text("""
            INSERT INTO alert_reports (
                time, region, alert_level, summary, recommendations, model_used,
                triggered_by, trigger_source,
                feature_values, rag_sources, model_metadata
            )
            VALUES (
                NOW(), :region, :alert_level, :summary, :recommendations, :model_used,
                :triggered_by, :trigger_source,
                :feature_values::jsonb, :rag_sources::jsonb, :model_metadata::jsonb
            )
            RETURNING id
        """),
        {
            "region": data["region"],
            "alert_level": data.get("alert_level", "GREEN"),
            "summary": data.get("summary", ""),
            "recommendations": data.get("recommendations"),
            "model_used": data.get("model_used"),
            "triggered_by": data.get("triggered_by", "system_scheduler"),
            "trigger_source": data.get("trigger_source"),
            "feature_values": (
                json.dumps(feature_values, ensure_ascii=False) if feature_values is not None else None
            ),
            "rag_sources": (
                json.dumps(rag_sources, ensure_ascii=False) if rag_sources is not None else None
            ),
            "model_metadata": (
                json.dumps(model_metadata, ensure_ascii=False) if model_metadata is not None else None
            ),
        },
    )
    await db.commit()
    row = result.first()
    return row[0] if row else -1
