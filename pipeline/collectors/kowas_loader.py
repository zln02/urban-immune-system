"""KOWAS PDF → TimescaleDB 일괄 적재 파이프라인.

다운로더 + 파서 + DB 적재를 통합한다.

적재 정책:
  - layer="wastewater", source="kowas:influenza"  → DB 적재 (시스템 가중치 산정에 사용)
  - 코로나·노로는 JSON 캐시(pipeline/data/kowas/parsed/)에만 보존
    (alerts.py의 DISTINCT ON (layer) 쿼리 충돌 방지 — 대시보드 별도 표시 용도)
  - time = 보고 주차의 마지막 일요일 (KOWAS 정의: 월~일 7일 누적)

CLI 예시:
  python -m pipeline.collectors.kowas_loader --download-only --limit 10
  python -m pipeline.collectors.kowas_loader --reparse-existing
  python -m pipeline.collectors.kowas_loader --weeks 52   # 최근 52주차만 적재
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from pipeline.collectors.db_writer import insert_signal
from pipeline.collectors.kowas_downloader import (
    DEFAULT_OUTPUT_DIR as PDF_DIR,
    download_all,
)
from pipeline.collectors.kowas_parser import (
    Pathogen,
    WeeklyReading,
    parse_report,
)

logger = logging.getLogger(__name__)

WASTEWATER_LAYER = "wastewater"
# DB 적재 대상 병원체 — 3종 모두 적재 (인플루엔자만 점수 계산에 사용,
# 코로나·노로는 신호 수집만. scorer.py 가 pathogen='influenza' 로 필터)
DB_TARGET_PATHOGENS: tuple[Pathogen, ...] = ("influenza", "covid", "norovirus")
JSON_CACHE_DIR = PDF_DIR / "parsed"

# 파일명에서 연·주 추출: kowas_2026_w15.pdf
PDF_NAME_RE = re.compile(r"kowas_(\d{4})_w(\d{1,2})\.pdf$")


def iso_week_end_date(year: int, week: int) -> date:
    """ISO 주의 일요일을 반환한다 (KOWAS 보고 주차 정의: 월~일 누적)."""
    monday = date.fromisocalendar(year, week, 1)
    return monday + timedelta(days=6)


def list_local_pdfs(pdf_dir: Path = PDF_DIR) -> list[tuple[Path, int, int]]:
    """다운로드된 PDF 파일을 (path, year, week) 튜플로 반환 (최신순)."""
    items: list[tuple[Path, int, int]] = []
    for p in pdf_dir.glob("kowas_*.pdf"):
        m = PDF_NAME_RE.search(p.name)
        if not m:
            continue
        items.append((p, int(m.group(1)), int(m.group(2))))
    items.sort(key=lambda t: (t[1], t[2]), reverse=True)
    return items


async def insert_readings(readings: list[WeeklyReading], report_date: datetime) -> int:
    """파서 결과를 layer_signals 테이블에 적재.

    DB_TARGET_PATHOGENS 에 속하는 병원체만 적재. pathogen 컬럼으로 분리되므로
    scorer.py 의 pathogen 필터로 인플루엔자만 점수 계산되고 나머지는 신호로만 보존.
    """
    inserted = 0
    for r in readings:
        if r.pathogen not in DB_TARGET_PATHOGENS:
            continue
        try:
            await insert_signal(
                region=r.region,
                layer=WASTEWATER_LAYER,
                value=r.relative_level,
                raw_value=float(r.bar_count),
                source=f"kowas:{r.pathogen}",
                ts=report_date,
                pathogen=r.pathogen,
            )
            inserted += 1
        except Exception as exc:
            logger.error(
                "INSERT 실패 %s/%s/w%d: %s", r.region, r.pathogen, r.week, exc,
            )
    return inserted


async def load_pdf(
    pdf_path: Path,
    year: int,
    week: int,
    pathogens: tuple[Pathogen, ...] = ("covid", "influenza", "norovirus"),
    cache_json: bool = True,
) -> tuple[int, list[WeeklyReading]]:
    """단일 PDF 파싱 + DB 적재. (적재 건수, readings) 반환."""
    readings = parse_report(pdf_path, year, week, pathogens)
    if cache_json:
        JSON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path = JSON_CACHE_DIR / f"kowas_{year}_w{week:02d}.json"
        cache_path.write_text(
            json.dumps([asdict(r) for r in readings], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    report_dt = datetime.combine(
        iso_week_end_date(year, week), datetime.min.time(), tzinfo=timezone.utc,
    )
    inserted = await insert_readings(readings, report_dt)
    logger.info("PDF %s → 추출 %d건 / 적재 %d건", pdf_path.name, len(readings), inserted)
    return inserted, readings


async def run(
    weeks_limit: int | None,
    download_first: bool,
    download_limit: int | None,
    skip_db: bool,
) -> None:
    if download_first:
        logger.info("PDF 다운로드 시작 (limit=%s)", download_limit)
        download_all(limit=download_limit)

    pdfs = list_local_pdfs()
    if weeks_limit is not None:
        pdfs = pdfs[:weeks_limit]
    logger.info("적재 대상 PDF: %d건", len(pdfs))

    total_inserted = 0
    for pdf, year, week in pdfs:
        try:
            if skip_db:
                # 파싱만 (캐시 JSON 갱신용)
                from pipeline.collectors.kowas_parser import parse_report
                readings = parse_report(pdf, year, week)
                JSON_CACHE_DIR.mkdir(parents=True, exist_ok=True)
                (JSON_CACHE_DIR / f"kowas_{year}_w{week:02d}.json").write_text(
                    json.dumps([asdict(r) for r in readings], ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
                logger.info("PDF %s → 파싱만 %d건", pdf.name, len(readings))
                continue
            n, _ = await load_pdf(pdf, year, week)
            total_inserted += n
        except Exception as exc:
            logger.exception("PDF 적재 실패 %s: %s", pdf.name, exc)

    logger.info("총 적재 %d건", total_inserted)


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    p = argparse.ArgumentParser(description="KOWAS PDF 일괄 적재")
    p.add_argument("--download", action="store_true", help="실행 전 PDF 다운로드")
    p.add_argument("--download-limit", type=int, default=None, help="다운로드 최대 건수")
    p.add_argument("--weeks", type=int, default=None, help="적재할 최근 주차 수")
    p.add_argument("--no-db", action="store_true", help="파싱 + JSON만, DB 적재 스킵")
    args = p.parse_args()

    asyncio.run(run(
        weeks_limit=args.weeks,
        download_first=args.download,
        download_limit=args.download_limit,
        skip_db=args.no_db,
    ))
