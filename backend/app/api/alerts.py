"""경보 리포트 API."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

# Ensemble weights from CLAUDE.md
W1, W2, W3 = 0.35, 0.40, 0.25


def _compute_alert_level(score: float) -> str:
    """앙상블 점수 → 경보 레벨."""
    if score < 30:
        return "GREEN"
    elif score < 55:
        return "YELLOW"
    elif score < 75:
        return "ORANGE"
    return "RED"


@router.get("/current")
async def get_current_alert(
    region: str = Query("서울특별시", min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """현재 경보 레벨: 최신 3계층 신호로 앙상블 점수 계산."""
    # Get latest signal per layer
    query = text("""
        SELECT DISTINCT ON (layer) layer, value, time
        FROM layer_signals
        WHERE region = :region AND layer IN ('L1', 'L2', 'L3')
        ORDER BY layer, time DESC
    """)
    result = await db.execute(query, {"region": region})
    rows = {r["layer"]: r["value"] for r in result.mappings().all()}

    l1 = rows.get("L1", 0.0)
    l2 = rows.get("L2", 0.0)
    l3 = rows.get("L3", 0.0)
    composite = round(W1 * l1 + W2 * l2 + W3 * l3, 2)
    alert_level = _compute_alert_level(composite)

    # Cross-validation rule: YELLOW+ requires 2+ layers above 30
    layers_above_30 = sum(1 for v in [l1, l2, l3] if v >= 30)
    if alert_level != "GREEN" and layers_above_30 < 2:
        alert_level = "GREEN"
        logger.info("교차검증 미충족 (30 이상 계층 %d개) → GREEN 유지", layers_above_30)

    # Get latest alert report if exists
    report_query = text("""
        SELECT summary, recommendations, model_used, created_at
        FROM alert_reports
        WHERE region = :region
        ORDER BY time DESC
        LIMIT 1
    """)
    report_result = await db.execute(report_query, {"region": region})
    report = report_result.mappings().first()

    return {
        "region": region,
        "alert_level": alert_level,
        "composite_score": composite,
        "l1_score": l1,
        "l2_score": l2,
        "l3_score": l3,
        "summary": report["summary"] if report else None,
        "recommendations": report["recommendations"] if report else None,
        "generated_at": str(report["created_at"]) if report else None,
    }


@router.post("/generate")
async def generate_alert_report(
    region: str = Query("서울특별시", min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """경보 리포트 생성 (DB에서 신호 기반 간단 리포트 저장)."""
    # Get current signals
    query = text("""
        SELECT DISTINCT ON (layer) layer, value, time
        FROM layer_signals
        WHERE region = :region AND layer IN ('L1', 'L2', 'L3')
        ORDER BY layer, time DESC
    """)
    result = await db.execute(query, {"region": region})
    rows = {r["layer"]: r["value"] for r in result.mappings().all()}

    l1 = rows.get("L1", 0.0)
    l2 = rows.get("L2", 0.0)
    l3 = rows.get("L3", 0.0)
    composite = round(W1 * l1 + W2 * l2 + W3 * l3, 2)
    alert_level = _compute_alert_level(composite)

    # Generate simple rule-based summary (RAG-LLM integration is future work)
    summary = (
        f"{region} 감염병 위험도 분석 결과: "
        f"약국OTC({l1:.1f}), 하수도({l2:.1f}), 검색트렌드({l3:.1f}). "
        f"종합점수 {composite:.1f}점, 경보단계 {alert_level}."
    )
    recommendations = "지속 모니터링 필요." if alert_level == "GREEN" else "교차검증 강화 및 추가 데이터 확인 권장."

    # Insert report
    insert_query = text("""
        INSERT INTO alert_reports (time, region, alert_level, summary, recommendations, model_used)
        VALUES (:time, :region, :alert_level, :summary, :recommendations, :model_used)
        RETURNING id
    """)
    insert_result = await db.execute(insert_query, {
        "time": datetime.now(timezone.utc),
        "region": region,
        "alert_level": alert_level,
        "summary": summary,
        "recommendations": recommendations,
        "model_used": "rule_based_v1",
    })
    await db.commit()
    report_id = insert_result.scalar()

    return {"status": "created", "report_id": report_id, "region": region, "alert_level": alert_level}
