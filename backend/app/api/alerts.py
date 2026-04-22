"""경보 리포트 API."""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..services.alert_service import get_latest_alert, get_latest_risk_score, save_alert_report
from ..tasks import generate_report_task

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "당신은 공중보건 전문가입니다. "
    "3-Layer 감염병 조기경보 시스템(약국 OTC + 하수 바이오마커 + 검색어 트렌드)의 "
    "분석 결과를 바탕으로 간결하고 실용적인 경보 리포트를 작성합니다. "
    "리포트는 한국어로 작성하며, 일반 시민과 보건 당국 모두가 이해할 수 있어야 합니다."
)


@router.get("/current")
async def get_current_alert(
    region: str = Query("서울특별시"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """현재 경보 레벨 및 최신 LLM 리포트 반환."""
    alert = await get_latest_alert(region, db)
    if alert is None:
        return {
            "region": region,
            "alert_level": "GREEN",
            "composite_score": None,
            "summary": None,
            "recommendations": None,
            "generated_at": None,
        }
    return {
        "region": alert["region"],
        "alert_level": alert["alert_level"],
        "summary": alert["summary"],
        "recommendations": alert["recommendations"],
        "generated_at": str(alert["created_at"]),
    }


@router.post("/generate")
async def generate_alert_report(
    region: str = Query("서울특별시"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """RAG-LLM 경보 리포트 비동기 생성 요청 (Taskiq → Kafka → ML 서비스)."""
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
    region: str = Query("서울특별시"),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    """LLM 경보 리포트를 SSE로 스트리밍한다 (RAG 없는 즉시 응답용)."""
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
    prompt = _build_prompt(region, signals)
    try:
        if settings.llm_model.startswith("claude"):
            gen = _stream_claude(prompt)
        else:
            gen = _stream_openai(prompt)

        async for chunk in gen:
            yield f"data: {json.dumps({'text': chunk}, ensure_ascii=False)}\n\n"
    except Exception:
        logger.exception("SSE 스트리밍 오류: region=%s", region)
        yield f"data: {json.dumps({'error': '리포트 생성 중 오류 발생'}, ensure_ascii=False)}\n\n"
    finally:
        yield "data: [DONE]\n\n"


def _build_prompt(region: str, signals: dict) -> str:
    return (
        f"지역: {region}\n"
        f"분석 시점: {signals.get('time', 'N/A')}\n\n"
        "## 현재 신호 요약\n"
        f"- Layer 1 (OTC 구매 트렌드): {signals.get('l1', 'N/A')} / 100\n"
        f"- Layer 2 (하수 바이오마커): {signals.get('l2', 'N/A')} / 100\n"
        f"- Layer 3 (검색어 트렌드): {signals.get('l3', 'N/A')} / 100\n"
        f"- 종합 위험도 점수: {signals.get('composite', 'N/A')} / 100\n"
        f"- 경보 레벨: {signals.get('alert_level', 'N/A')}\n\n"
        "위 데이터를 바탕으로 다음 항목을 포함한 경보 리포트를 작성하세요:\n"
        "1. 현황 요약 (2~3문장)\n"
        "2. 각 Layer 신호 해석\n"
        "3. 7/14/21일 전망\n"
        "4. 권고 조치 (시민 대상 / 보건 당국 대상)"
    )


async def _stream_openai(prompt: str) -> AsyncIterator[str]:
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=settings.openai_api_key)
    stream = await client.chat.completions.create(
        model=settings.llm_model,
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        max_tokens=1500,
        temperature=0.3,
        stream=True,
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        if delta:
            yield delta


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
