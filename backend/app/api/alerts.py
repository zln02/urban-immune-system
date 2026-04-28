"""경보 리포트 API — SSE 스트리밍 + DB 앙상블."""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..services.alert_service import get_latest_alert, get_latest_risk_score
from ..services.report_pdf import build_alert_pdf
from ..tasks import generate_report_task

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)

# CLAUDE.md 앙상블 가중치
W1, W2, W3 = 0.35, 0.40, 0.25

_SYSTEM_PROMPT = (
    "당신은 공중보건 전문가입니다. "
    "3-Layer 감염병 조기경보 시스템(약국 OTC + 하수 바이오마커 + 검색어 트렌드)의 "
    "분석 결과를 바탕으로 간결하고 실용적인 경보 리포트를 작성합니다. "
    "리포트는 한국어로 작성하며, 일반 시민과 보건 당국 모두가 이해할 수 있어야 합니다."
)


def _compute_alert_level(score: float) -> str:
    if score < 30:
        return "GREEN"
    elif score < 55:
        return "YELLOW"
    elif score < 75:
        return "ORANGE"
    return "RED"


def _reverify_alert(
    composite: float, l1: float, l2: float, l3: float, stored: str | None,
) -> str:
    """risk_scores row 저장값이 교차검증 규칙과 일치하는지 재검증.

    과거 스키마·수동 INSERT로 오염된 row가 있어도 최종 응답은 항상 규칙에 맞게 강제.
    규칙: composite 기반 raw_level + (GREEN 외 등급은 2개 이상 계층이 30 이상이어야 발령)
    """
    raw = _compute_alert_level(composite)
    n_above = sum(1 for v in (l1, l2, l3) if v is not None and v >= 30)
    final = raw if (raw == "GREEN" or n_above >= 2) else "GREEN"
    if stored and stored != final:
        logger.warning(
            "risk_scores 저장 라벨(%s)이 교차검증 결과(%s)와 다름 — 재검증 값으로 대체 "
            "(composite=%.2f, l1=%.1f l2=%.1f l3=%.1f, layers_above_30=%d)",
            stored, final, composite, l1, l2, l3, n_above,
        )
    return final


@router.get("/current")
async def get_current_alert(
    region: str = Query("서울특별시", min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """현재 경보 레벨: risk_scores 최신 row 기준 + DB 리포트 조회.

    risk_scores에 해당 region row가 있으면 최신 row의 점수·레벨을 그대로 사용.
    row가 없으면 layer_signals 28일 평균 앙상블로 fallback.
    summary/recommendations는 alert_reports 최신 row에서 조회.
    """
    # 1차: risk_scores 최신 row 조회
    risk = await get_latest_risk_score(region, db)

    if risk is not None:
        # risk_scores row 기반 — 단 저장된 alert_level이 규칙과 다를 수 있으므로 재검증
        l1 = float(risk.get("l1_score") or 0.0)
        l2 = float(risk.get("l2_score") or 0.0)
        l3 = float(risk.get("l3_score") or 0.0)
        composite = round(float(risk.get("composite_score") or 0.0), 2)
        stored_level = str(risk.get("alert_level") or "GREEN")
        alert_level = _reverify_alert(composite, l1, l2, l3, stored_level)
        logger.info(
            "risk_scores 기반 (재검증 적용): region=%s composite=%.2f level=%s",
            region, composite, alert_level,
        )
    else:
        # fallback: layer_signals 28일 평균 앙상블
        logger.info("risk_scores 없음 → layer_signals 28일 평균 fallback: region=%s", region)
        query = text("""
            SELECT layer, AVG(value) AS value
            FROM layer_signals
            WHERE region = :region
              AND layer IN ('otc', 'wastewater', 'search')
              AND time >= NOW() - INTERVAL '28 days'
              AND value > 0
            GROUP BY layer
        """)
        result = await db.execute(query, {"region": region})
        rows = {r["layer"]: float(r["value"]) for r in result.mappings().all()}

        l1 = rows.get("otc", 0.0)
        l2 = rows.get("wastewater", 0.0)
        l3 = rows.get("search", 0.0)
        composite = round(W1 * l1 + W2 * l2 + W3 * l3, 2)
        alert_level = _compute_alert_level(composite)

        # 교차검증: YELLOW 이상은 2개 이상 계층 30 이상 필수
        layers_above_30 = sum(1 for v in [l1, l2, l3] if v >= 30)
        if alert_level != "GREEN" and layers_above_30 < 2:
            alert_level = "GREEN"
            logger.info("교차검증 미충족 (%d개 계층) → GREEN 유지", layers_above_30)

    # 최신 리포트 조회 (alert_reports — 기존 로직 유지)
    alert = await get_latest_alert(region, db)
    return {
        "region": region,
        "alert_level": alert_level,
        "composite_score": composite,
        "l1_score": l1,
        "l2_score": l2,
        "l3_score": l3,
        "summary": alert["summary"] if alert else None,
        "recommendations": alert["recommendations"] if alert else None,
        "generated_at": str(alert["created_at"]) if alert else None,
    }


@router.get("/regions")
async def list_region_alerts(
    db: AsyncSession = Depends(get_db),
    days: int = Query(28, ge=7, le=365),
) -> dict:
    """전국 17개 시·도 동시 경보 — risk_scores 최신 row 기반 + fallback layer_signals.

    각 region의 최신 risk_scores row를 먼저 조회.
    risk_scores에 해당 region이 없으면 layer_signals 28일 평균으로 fallback.
    Frontend AlertTable 1회 호출로 전국 현황 표시 (region별 17번 호출 회피).
    """
    # 1차: risk_scores에서 모든 지역의 최신 row 조회 (DISTINCT ON)
    risk_query = text("""
        SELECT DISTINCT ON (region) region, l1_score, l2_score, l3_score,
               composite_score, alert_level, time
        FROM risk_scores
        ORDER BY region, time DESC
    """)
    risk_result = await db.execute(risk_query)
    risk_rows = {
        r["region"]: {
            "l1": float(r["l1_score"] or 0.0),
            "l2": float(r["l2_score"] or 0.0),
            "l3": float(r["l3_score"] or 0.0),
            "composite": float(r["composite_score"] or 0.0),
            "alert_level": str(r["alert_level"] or "GREEN"),
            "latest": r["time"],
        }
        for r in risk_result.mappings().all()
    }

    # 2차: layer_signals fallback (risk_scores에 없는 region만)
    fallback_query = text(f"""
        SELECT region, layer, AVG(value) AS value, MAX(time) AS latest
        FROM layer_signals
        WHERE layer IN ('otc', 'wastewater', 'search')
          AND time >= NOW() - INTERVAL '{int(days)} days'
          AND value > 0
        GROUP BY region, layer
    """)
    fallback_result = await db.execute(fallback_query)
    pivot: dict[str, dict] = {}
    for r in fallback_result.mappings().all():
        rg = r["region"]
        # risk_scores에 있으면 skip (fallback 불필요)
        if rg in risk_rows:
            continue
        pivot.setdefault(rg, {"region": rg, "l1": 0.0, "l2": 0.0, "l3": 0.0, "latest": None})
        layer = r["layer"]
        if layer == "otc":
            pivot[rg]["l1"] = float(r["value"])
        elif layer == "wastewater":
            pivot[rg]["l2"] = float(r["value"])
        elif layer == "search":
            pivot[rg]["l3"] = float(r["value"])
        latest = r["latest"]
        if latest and (pivot[rg]["latest"] is None or latest > pivot[rg]["latest"]):
            pivot[rg]["latest"] = latest

    rows: list[dict] = []

    # risk_scores 기반 경보 — 저장 라벨 재검증 (과거 스키마 오염 방어)
    for rg, v in risk_rows.items():
        final_level = _reverify_alert(
            v["composite"], v["l1"], v["l2"], v["l3"], v["alert_level"],
        )
        logger.info(
            "risk_scores 기반 (재검증): region=%s composite=%.2f level=%s",
            rg, v["composite"], final_level,
        )
        rows.append({
            "region": rg,
            "composite": round(v["composite"], 2),
            "alert_level": final_level,
            "l1": round(v["l1"], 2),
            "l2": round(v["l2"], 2),
            "l3": round(v["l3"], 2),
            "layers_above_30": sum(1 for x in (v["l1"], v["l2"], v["l3"]) if x >= 30),
            "latest_time": str(v["latest"]) if v["latest"] else None,
        })

    # layer_signals fallback (risk_scores 없는 region)
    for rg, v in pivot.items():
        composite = round(W1 * v["l1"] + W2 * v["l2"] + W3 * v["l3"], 2)
        raw_level = _compute_alert_level(composite)
        n_above = sum(1 for x in (v["l1"], v["l2"], v["l3"]) if x >= 30)
        # 교차검증: GREEN 외 등급은 2개 이상 30 이상 필수
        final_level = raw_level if (raw_level == "GREEN" or n_above >= 2) else "GREEN"
        logger.info(
            "layer_signals fallback: region=%s composite=%.2f level=%s",
            rg, composite, final_level,
        )
        rows.append({
            "region": rg,
            "composite": composite,
            "alert_level": final_level,
            "l1": round(v["l1"], 2),
            "l2": round(v["l2"], 2),
            "l3": round(v["l3"], 2),
            "layers_above_30": n_above,
            "latest_time": str(v["latest"]) if v["latest"] else None,
        })
    rows.sort(key=lambda x: x["composite"], reverse=True)
    return {"window_days": days, "count": len(rows), "alerts": rows}


@router.post("/generate")
async def generate_alert_report(
    region: str = Query("서울특별시", min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """RAG-LLM 경보 리포트 비동기 생성 (Taskiq → Kafka → ML 서비스)."""
    risk = await get_latest_risk_score(region, db)
    if risk is None:
        raise HTTPException(status_code=404, detail=f"{region} 리스크 점수 데이터 없음")

    signals = {
        "time": str(risk["time"]),
        "l1": risk.get("l1_score"),
        "l2": risk.get("l2_score"),
        "l3": risk.get("l3_score"),
        "composite": risk.get("composite_score"),
        "alert_level": risk.get("alert_level", "GREEN"),
    }
    await generate_report_task.kiq(region, signals)
    return {"status": "queued", "region": region, "alert_level": signals["alert_level"]}


@router.get("/stream")
async def stream_alert_report(
    region: str = Query("서울특별시", min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """Claude SSE 스트리밍 경보 리포트 — Qdrant 역학 가이드 RAG 컨텍스트 첨부."""
    risk = await get_latest_risk_score(region, db)
    signals: dict = risk or {
        "l1": "N/A", "l2": "N/A", "l3": "N/A",
        "composite": "N/A", "alert_level": "GREEN", "time": "N/A",
    }
    return StreamingResponse(
        _sse_generator(region, signals),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


async def _sse_generator(region: str, signals: dict) -> AsyncIterator[str]:
    rag_context, citations = _retrieve_rag_context(region, signals)
    prompt = _build_prompt(region, signals, rag_context)
    try:
        # 출처 목록을 메타 이벤트로 먼저 전송 (UI에서 인용 패널 렌더용)
        if citations:
            yield f"data: {json.dumps({'citations': citations}, ensure_ascii=False)}\n\n"
        async for chunk in _stream_claude(prompt):
            yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
    except Exception:
        logger.exception("SSE 스트리밍 오류: region=%s", region)
        yield f"data: {json.dumps({'error': '리포트 생성 중 오류 발생'}, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"


# RAG 벡터DB 싱글톤 — 모듈 첫 로드 시 한 번만 초기화 (SentenceTransformer 100MB 모델 캐싱)
_VDB = None


def _get_vdb():
    global _VDB
    if _VDB is None:
        try:
            from ml.rag.vectordb import EpidemiologyVectorDB
            _VDB = EpidemiologyVectorDB()
        except Exception as exc:
            logger.warning("RAG 벡터DB 초기화 실패 (이후 호출도 빈 컨텍스트 반환): %s", exc)
            _VDB = False  # 명시적 실패 sentinel — 매번 재시도 방지
    return _VDB if _VDB is not False else None


def _retrieve_rag_context(region: str, signals: dict) -> tuple[str, list[dict]]:
    """현재 신호 상황에 맞는 역학 가이드 top-3을 Qdrant에서 검색.

    실패 시 (Qdrant·임베딩 모델 미가동, 컬렉션 비어있음) 빈 컨텍스트 반환 — 호출 측 안전.
    """
    vdb = _get_vdb()
    if vdb is None:
        return "", []
    query = (
        f"{region} 인플루엔자 조기경보 경보레벨={signals.get('alert_level','GREEN')} "
        f"L1={signals.get('l1')} L2={signals.get('l2')} L3={signals.get('l3')}"
    )
    try:
        hits = vdb.search(query, top_k=3) or []
    except Exception as exc:
        logger.warning("RAG 검색 스킵: %s", exc)
        return "", []

    if not hits:
        return "", []

    lines = ["## 참고 역학 가이드 (Qdrant 검색 결과)"]
    citations: list[dict] = []
    for i, h in enumerate(hits, 1):
        src = h["metadata"].get("source", "출처 미상")
        topic = h["metadata"].get("topic", "")
        lines.append(f"[{i}] ({topic}) {h['text']}\n— 출처: {src}")
        citations.append({
            "rank": i,
            "topic": topic,
            "source": src,
            "url": h["metadata"].get("url"),
            "score": round(h["score"], 3),
        })
    return "\n\n".join(lines), citations


def _build_prompt(region: str, signals: dict, rag_context: str = "") -> str:
    rag_block = (
        f"\n{rag_context}\n\n"
        "위 가이드의 정의·임계값·과거 사례를 인용 번호([1], [2], [3])로 명시해 활용하세요.\n"
        if rag_context else ""
    )
    return (
        f"지역: {region}\n"
        f"분석 시점: {signals.get('time', 'N/A')}\n\n"
        "## 현재 신호 요약\n"
        f"- Layer 1 (OTC 구매 트렌드): {signals.get('l1', 'N/A')} / 100\n"
        f"- Layer 2 (하수 바이오마커): {signals.get('l2', 'N/A')} / 100\n"
        f"- Layer 3 (검색어 트렌드): {signals.get('l3', 'N/A')} / 100\n"
        f"- 종합 위험도 점수: {signals.get('composite', 'N/A')} / 100\n"
        f"- 경보 레벨: {signals.get('alert_level', 'N/A')}\n"
        f"{rag_block}"
        "\n위 데이터를 바탕으로 다음 항목을 포함한 경보 리포트를 작성하세요:\n"
        "1. 현황 요약 (2~3문장)\n"
        "2. 각 Layer 신호 해석\n"
        "3. 7/14/21일 전망\n"
        "4. 권고 조치 (시민 대상 / 보건 당국 대상)"
    )


async def _stream_claude(prompt: str) -> AsyncIterator[str]:
    import anthropic
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    async with client.messages.stream(
        model=settings.llm_model,
        max_tokens=1500,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    ) as stream:
        async for text in stream.text_stream:
            yield text


@router.get("/explain/{report_id}")
async def explain_alert_report(
    report_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """특정 경보 리포트의 XAI 설명 반환.

    alert_reports 테이블의 feature_values, rag_sources, model_metadata,
    triggered_by, trigger_source 컬럼을 그대로 펼쳐 응답한다.
    JSONB 컬럼이 NULL 이면 빈 객체/빈 배열을 반환한다 (404 아님).
    """
    result = await db.execute(
        text("""
            SELECT id, region, alert_level, summary,
                   triggered_by, trigger_source, created_at,
                   feature_values, rag_sources, model_metadata
            FROM alert_reports
            WHERE id = :report_id
            LIMIT 1
        """),
        {"report_id": report_id},
    )
    row = result.mappings().first()
    if row is None:
        raise HTTPException(status_code=404, detail=f"report_id={report_id} 를 찾을 수 없습니다.")

    # JSONB 컬럼: DB에서 이미 dict/list로 deserialize 되거나 문자열로 올 수 있음
    def _jsonb(val: object, default: object) -> object:
        if val is None:
            return default
        if isinstance(val, (dict, list)):
            return val
        try:
            return json.loads(str(val))
        except Exception:
            return default

    raw_fv = _jsonb(row.get("feature_values"), {})
    decision_factors: dict = {}
    if isinstance(raw_fv, dict):
        decision_factors = {
            k: v for k, v in raw_fv.items()
            if k in ("l1_otc", "l2_wastewater", "l3_search", "composite")
        }

    rag_raw = _jsonb(row.get("rag_sources"), [])
    rag_citations: list = rag_raw if isinstance(rag_raw, list) else []

    return {
        "report_id": report_id,
        "region": row.get("region"),
        "alert_level": row.get("alert_level"),
        "summary": row.get("summary"),
        "decision_factors": decision_factors,
        "feature_values": raw_fv,
        "rag_citations": rag_citations,
        "model_metadata": _jsonb(row.get("model_metadata"), {}),
        "audit": {
            "triggered_by": row.get("triggered_by"),
            "trigger_source": row.get("trigger_source"),
            "created_at": str(row.get("created_at")) if row.get("created_at") else None,
        },
    }


@router.get("/report-pdf")
async def export_alert_pdf(
    region: str = Query("서울특별시", min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """4페이지 PDF 리포트 다운로드 — 표지 + 3계층 시계열 + 분석 + AI 본문."""
    from urllib.parse import quote
    pdf_bytes = await build_alert_pdf(region, db)
    fname = f"UIS_alert_{region}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M')}.pdf"
    return StreamingResponse(
        iter([pdf_bytes]),
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f"attachment; filename=\"UIS_alert.pdf\"; filename*=UTF-8''{quote(fname)}"
            ),
        },
    )
