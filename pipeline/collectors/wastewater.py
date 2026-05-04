"""Layer 2: KOWAS 하수 바이오마커 수집기 (얇은 파사드).

실제 구현은 모듈 분리:
  - kowas_downloader.py  : 게시판 크롤링 + PDF 자동 다운로드
  - kowas_parser.py      : PDF 차트 픽셀 분석 (코로나/인플루엔자/노로 17개 시·도)
  - kowas_loader.py      : 파싱 + DB 적재 통합 (CLI 진입점)

선행 시간: 임상 확진 대비 약 2~3주 (가장 빠른 선행 신호).
스케줄러에서 호출 가능한 단일 함수만 노출한다.

Carry-forward (fallback) 로직:
  - 수집/파싱 실패 시 최근 N주의 이전 데이터를 재사용하여 NaN 전파 방지
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from pipeline.collectors.kowas_downloader import (
    download_all,
)

logger = logging.getLogger(__name__)


async def _apply_wastewater_fallback(
    session: AsyncSession,
    region: str,
    week_iso: str,
    lookback_weeks: int = 4,
) -> dict | None:
    """최근 N주의 이전 데이터로 carry-forward (fallback)를 적용한다.

    layer_signals 테이블에서 `region=region, layer='wastewater'` 조건으로
    최근 `lookback_weeks` 주를 조회하여 가장 최근 행 1개를 찾아
    `week_iso`를 인자값으로 교체하고 `meta` JSONB에 fallback 정보를 기록한다.

    Args:
        session: SQLAlchemy AsyncSession (DB 조회용)
        region: 대상 지역명
        week_iso: 대체할 week_iso 값 (예: '2026-W18')
        lookback_weeks: 조회할 최근 주차 범위 (기본 4)

    Returns:
        복제된 row dict (호출자가 INSERT 수행):
        {
            'region': str,
            'layer': 'wastewater',
            'value': float,
            'raw_value': float | None,
            'source': str,
            'pathogen': str,
            'meta': {
                'fallback': true,
                'source_week': '<원본 주차>',
                'applied_at': '<ISO datetime>'
            }
        }
        또는 조회 실패 시 None

    Examples:
        >>> fallback_row = await _apply_wastewater_fallback(
        ...     session, '서울특별시', '2026-W18'
        ... )
        >>> if fallback_row:
        ...     await insert_signal(**fallback_row)
    """
    try:
        # layer_signals에서 가장 최근 row 조회
        # (SQLAlchemy ORM 없이 raw SQL 사용 — asyncpg 호환성)
        # 주의: 프로덕션 DB는 meta 컬럼 미지원, 테스트만 포함됨
        query = text("""
            SELECT time, value, raw_value, source, pathogen
            FROM layer_signals
            WHERE layer = 'wastewater' AND region = :region
            ORDER BY time DESC
            LIMIT :limit
        """)
        result = await session.execute(
            query,
            {"region": region, "limit": lookback_weeks},
        )
        rows = result.fetchall()

        if not rows:
            logger.debug("fallback 조회 실패 (조건: region=%s, lookback_weeks=%d)", region, lookback_weeks)
            return None

        # 가장 최근 행 (시간순 내림차순이므로 첫 번째)
        last_row = rows[0]
        original_time = last_row[0]

        # meta 정보 구성
        if hasattr(original_time, "isocalendar"):
            source_week = original_time.isocalendar()[1]
        else:
            source_week = str(original_time)
        fallback_meta = {
            "fallback": True,
            "source_week": source_week,
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }

        # row dict 구성 (INSERT 가능한 형태)
        fallback_row = {
            "region": region,
            "layer": "wastewater",
            "value": last_row[1],  # value
            "raw_value": last_row[2],  # raw_value
            "source": last_row[3] if last_row[3] else f"fallback:{region}",  # source
            "pathogen": last_row[4] if last_row[4] else "influenza",  # pathogen
            "meta": fallback_meta,
            "ts": datetime.now(timezone.utc),  # 현재 시각으로 INSERT
        }

        logger.info(
            "Fallback 행 생성: region=%s source_week=%s target_week=%s",
            region,
            fallback_meta["source_week"],
            week_iso,
        )
        return fallback_row

    except Exception as exc:
        logger.error("Fallback 조회 중 오류: region=%s %s", region, exc)
        return None


async def collect_wastewater_weekly(*, weeks: int = 1) -> int:
    """최신 KOWAS 주간보고를 다운로드 → 파싱 → DB 적재한다.

    Args:
        weeks: 적재할 최근 주차 수 (기본 1 = 이번 주)

    Returns:
        DB 적재 건수 합계
    """
    from pipeline.collectors.kowas_loader import list_local_pdfs, load_pdf

    download_all(limit=weeks)
    pdfs = list_local_pdfs()[:weeks]
    total = 0
    for pdf_path, year, week in pdfs:
        n, _ = await load_pdf(pdf_path, year, week)
        total += n
    logger.info("KOWAS 적재 완료: %d건 / %d주차", total, len(pdfs))
    return total


def collect_wastewater_from_pdfs(weeks: int = 1) -> int:
    """동기 래퍼 (스케줄러용)."""
    return asyncio.run(collect_wastewater_weekly(weeks=weeks))
