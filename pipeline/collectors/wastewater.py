"""Layer 2: KOWAS 하수 바이오마커 수집기 (얇은 파사드).

실제 구현은 모듈 분리:
  - kowas_downloader.py  : 게시판 크롤링 + PDF 자동 다운로드
  - kowas_parser.py      : PDF 차트 픽셀 분석 (코로나/인플루엔자/노로 17개 시·도)
  - kowas_loader.py      : 파싱 + DB 적재 통합 (CLI 진입점)

선행 시간: 임상 확진 대비 약 2~3주 (가장 빠른 선행 신호).
스케줄러에서 호출 가능한 단일 함수만 노출한다.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from pipeline.collectors.kowas_downloader import (
    DEFAULT_OUTPUT_DIR as KOWAS_DATA_DIR,
    download_all,
)
from pipeline.collectors.kowas_loader import list_local_pdfs, load_pdf

logger = logging.getLogger(__name__)


async def collect_wastewater_weekly(*, weeks: int = 1) -> int:
    """최신 KOWAS 주간보고를 다운로드 → 파싱 → DB 적재한다.

    Args:
        weeks: 적재할 최근 주차 수 (기본 1 = 이번 주)

    Returns:
        DB 적재 건수 합계
    """
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
