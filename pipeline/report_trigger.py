"""risk_scores 기반 Claude LLM 경보 리포트 배치 생성기.

사용법:
    python -m pipeline.report_trigger --region 서울특별시
    python -m pipeline.report_trigger --all
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
from typing import Any

import anthropic
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ml.rag.vectordb import EpidemiologyVectorDB

load_dotenv()

logger = logging.getLogger(__name__)

# GREEN은 스킵 — 비용 절감 (YELLOW/ORANGE/RED만 생성)
ALERT_LEVELS_TO_REPORT = {"YELLOW", "ORANGE", "RED"}

# 비용 절감용 Haiku 모델 (지시에 따라 claude-haiku-4-5-20251001 고정)
_HAIKU_MODEL = "claude-haiku-4-5-20251001"

# RAG 검색용 vectordb 싱글톤 (sentence-transformers 모델 로드 비용 회피)
_RAG_TOP_K = 5
_RAG_DOC_MAX_CHARS = 350
_vdb_singleton: EpidemiologyVectorDB | None = None


def _get_vdb() -> EpidemiologyVectorDB:
    """프로세스 수명 동안 EpidemiologyVectorDB를 1회만 초기화한다."""
    global _vdb_singleton
    if _vdb_singleton is None:
        _vdb_singleton = EpidemiologyVectorDB()
    return _vdb_singleton


def _fetch_rag_context(region: str, alert_level: str) -> list[dict]:
    """Qdrant에서 가이드라인 top-k를 검색한다. 실패 시 빈 리스트."""
    try:
        vdb = _get_vdb()
        query = f"{region} {alert_level} 인플루엔자 조기경보 다중신호 교차검증"
        return vdb.search(query, top_k=_RAG_TOP_K)
    except Exception:
        logger.exception("RAG 검색 실패, 가이드라인 없이 진행")
        return []

_SYSTEM_PROMPT = """당신은 공중보건 전문가입니다.
3-Layer 감염병 조기경보 시스템(약국 OTC + 하수 바이오마커 + 검색어 트렌드)의
분석 결과를 바탕으로 간결하고 실용적인 경보 리포트를 작성합니다.
리포트는 한국어로 작성하며, 일반 시민과 보건 당국 모두가 이해할 수 있어야 합니다.
모든 내용은 역학적 판단 근거이며, 의료적 진단이나 처방을 대체하지 않습니다."""

# 전국 17개 시·도
ALL_REGIONS = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시",
    "광주광역시", "대전광역시", "울산광역시", "세종특별자치시",
    "경기도", "강원특별자치도", "충청북도", "충청남도",
    "전라북도", "전라남도", "경상북도", "경상남도", "제주특별자치도",
]


def _get_engine():
    """AsyncEngine 생성 — DATABASE_URL 환경변수 우선."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://uis_user:uis_dev_placeholder_20260414@localhost:5432/urban_immune",
    )
    return create_async_engine(db_url, echo=False)


def _build_report_prompt(
    region: str,
    signals: dict[str, Any],
    rag_docs: list[dict] | None = None,
) -> str:
    """L1/L2/L3, composite_score, alert_level + 선택적 RAG 가이드라인 주입.

    Args:
        region: 지역명
        signals: time, l1, l2, l3, composite, alert_level 포함 딕셔너리
        rag_docs: Qdrant 검색 결과 (text/metadata 포함). None 또는 빈 리스트면 가이드라인 섹션 생략.
    Returns:
        Claude 사용자 프롬프트 문자열
    """
    base = (
        f"지역: {region}\n"
        f"분석 시점: {signals.get('time', 'N/A')}\n\n"
        "## 현재 신호 요약\n"
        f"- Layer 1 (OTC 구매 트렌드): {signals.get('l1', 'N/A')} / 100\n"
        f"- Layer 2 (하수 바이오마커): {signals.get('l2', 'N/A')} / 100\n"
        f"- Layer 3 (검색어 트렌드): {signals.get('l3', 'N/A')} / 100\n"
        f"- 종합 위험도 점수: {signals.get('composite', 'N/A')} / 100\n"
        f"- 경보 레벨: {signals.get('alert_level', 'N/A')}\n"
    )

    if rag_docs:
        guideline_lines = []
        for i, d in enumerate(rag_docs, 1):
            topic = (d.get("metadata") or {}).get("topic", "guideline")
            text_excerpt = " ".join(d.get("text", "").split())[:_RAG_DOC_MAX_CHARS]
            guideline_lines.append(f"[참고 {i} · {topic}] {text_excerpt}")
        base += "\n## 관련 역학 가이드라인 (RAG 인용)\n" + "\n\n".join(guideline_lines) + "\n"

    base += (
        "\n위 데이터와 가이드라인을 바탕으로 다음 항목을 포함한 경보 리포트를 작성하세요:\n"
        "1. 현황 요약 (2~3문장)\n"
        "2. 각 Layer 신호 해석 — 가이드라인을 인용해 근거 명시\n"
        "3. 7/14/21일 전망\n"
        "4. 권고 조치 (시민 대상 / 보건 당국 대상)"
    )
    return base


async def _call_claude_haiku(prompt: str) -> str:
    """Claude Haiku 모델로 경보 리포트 텍스트를 생성한다.

    Args:
        prompt: 사용자 프롬프트 (신호 데이터 포함)
    Returns:
        생성된 리포트 텍스트
    Raises:
        RuntimeError: ANTHROPIC_API_KEY 미설정 시
        anthropic.APIError: API 호출 실패 시
    """
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")

    client = anthropic.AsyncAnthropic(api_key=api_key)
    resp = await client.messages.create(
        model=_HAIKU_MODEL,
        max_tokens=1200,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text if resp.content else ""


async def _fetch_latest_risk_score(region: str, session: AsyncSession) -> dict[str, Any] | None:
    """region의 가장 최신 risk_score 행을 조회한다.

    Args:
        region: 지역명
        session: 비동기 DB 세션
    Returns:
        risk_score 딕셔너리 또는 None (데이터 없음)
    """
    result = await session.execute(
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


async def _insert_alert_report(
    region: str,
    alert_level: str,
    summary: str,
    session: AsyncSession,
) -> int:
    """alert_reports 테이블에 리포트 행을 INSERT한다.

    Args:
        region: 지역명
        alert_level: 경보 레벨 (YELLOW/ORANGE/RED)
        summary: Claude 생성 리포트 텍스트
        session: 비동기 DB 세션
    Returns:
        삽입된 행의 id
    """
    result = await session.execute(
        text("""
            INSERT INTO alert_reports (time, region, alert_level, summary, model_used)
            VALUES (NOW(), :region, :alert_level, :summary, :model_used)
            RETURNING id
        """),
        {
            "region": region,
            "alert_level": alert_level,
            "summary": summary,
            "model_used": _HAIKU_MODEL,
        },
    )
    await session.commit()
    row = result.first()
    return row[0] if row else -1


async def generate_latest_alert_report(region: str) -> dict[str, Any] | None:
    """region의 최신 risk_score를 읽어 Claude 리포트를 생성하고 DB에 저장한다.

    GREEN 경보는 비용 절감을 위해 스킵한다.

    Args:
        region: 지역명 (예: "서울특별시")
    Returns:
        생성된 alert_report 딕셔너리 또는 None (GREEN 스킵 / 데이터 없음)
    Raises:
        RuntimeError: ANTHROPIC_API_KEY 미설정 시
    """
    engine = _get_engine()
    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    try:
        async with session_factory() as session:
            risk = await _fetch_latest_risk_score(region, session)

        if risk is None:
            logger.warning("risk_scores 데이터 없음: region=%s", region)
            return None

        alert_level = risk.get("alert_level") or "GREEN"
        if alert_level not in ALERT_LEVELS_TO_REPORT:
            logger.info("GREEN 경보 스킵 (비용 절감): region=%s, level=%s", region, alert_level)
            return None

        signals = {
            "time": str(risk["time"]),
            "l1": risk.get("l1_score"),
            "l2": risk.get("l2_score"),
            "l3": risk.get("l3_score"),
            "composite": risk.get("composite_score"),
            "alert_level": alert_level,
        }

        rag_docs = _fetch_rag_context(region, alert_level)
        logger.info(
            "RAG 검색 결과: region=%s, docs=%d (top topic=%s)",
            region,
            len(rag_docs),
            (rag_docs[0].get("metadata") or {}).get("topic") if rag_docs else "n/a",
        )

        prompt = _build_report_prompt(region, signals, rag_docs=rag_docs)
        logger.info("Claude Haiku 호출 시작: region=%s, level=%s", region, alert_level)
        report_text = await _call_claude_haiku(prompt)

        async with session_factory() as session:
            report_id = await _insert_alert_report(region, alert_level, report_text, session)

        logger.info("alert_reports INSERT 완료: id=%d, region=%s", report_id, region)
        return {
            "id": report_id,
            "region": region,
            "alert_level": alert_level,
            "summary": report_text,
            "model_used": _HAIKU_MODEL,
        }
    finally:
        await engine.dispose()


async def run_nightly_reports() -> int:
    """전국 17개 시·도 순회하며 YELLOW/ORANGE/RED 경보 리포트를 생성한다.

    Returns:
        실제 생성·저장된 리포트 건수
    """
    generated = 0
    for region in ALL_REGIONS:
        try:
            result = await generate_latest_alert_report(region)
            if result is not None:
                generated += 1
                logger.info("리포트 생성 완료: region=%s, id=%d", region, result["id"])
        except Exception:
            logger.exception("리포트 생성 실패, 다음 지역으로 계속: region=%s", region)
    logger.info("야간 배치 완료: %d건 생성", generated)
    return generated


def _cli() -> None:
    """argparse CLI — python -m pipeline.report_trigger --region 서울특별시."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    parser = argparse.ArgumentParser(description="risk_scores → Claude 리포트 배치 생성기")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--region", type=str, help="단건 지역 (예: 서울특별시)")
    group.add_argument("--all", action="store_true", help="전국 17개 시·도 일괄 실행")
    args = parser.parse_args()

    if args.all:
        count = asyncio.run(run_nightly_reports())
        print(f"[완료] 총 {count}건 생성")
    else:
        result = asyncio.run(generate_latest_alert_report(args.region))
        if result is None:
            print(f"[스킵] {args.region}: risk_scores 없음 또는 GREEN 경보")
        else:
            print(f"[완료] id={result['id']}, level={result['alert_level']}")
            print(f"[summary 앞 300자]\n{result['summary'][:300]}")


if __name__ == "__main__":
    _cli()
