"""pipeline/collectors/kowas_loader.py 단위 테스트."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Case 1: iso_week_end_date — 2026년 W1 → 2026-01-04 (일요일)
# ---------------------------------------------------------------------------
def test_iso_week_end_date_w1() -> None:
    """2026년 1주차 일요일은 2026-01-04여야 한다."""
    from pipeline.collectors.kowas_loader import iso_week_end_date

    # ISO 2026-W01: 2025-12-29(월) ~ 2026-01-04(일)
    result = iso_week_end_date(2026, 1)
    assert result == date(2026, 1, 4)


# ---------------------------------------------------------------------------
# Case 2: iso_week_end_date — 2026년 W17 → 정확한 date 값
# ---------------------------------------------------------------------------
def test_iso_week_end_date_w17() -> None:
    """2026년 17주차 일요일을 정확히 반환해야 한다."""
    # 직접 계산: date.fromisocalendar(2026, 17, 1) + 6일
    from datetime import timedelta

    from pipeline.collectors.kowas_loader import iso_week_end_date

    expected = date.fromisocalendar(2026, 17, 1) + timedelta(days=6)
    result = iso_week_end_date(2026, 17)
    assert result == expected


# ---------------------------------------------------------------------------
# Case 3: list_local_pdfs — PDF 없음 → 빈 리스트
# ---------------------------------------------------------------------------
def test_list_local_pdfs_empty(tmp_path: Path) -> None:
    """PDF가 없는 디렉토리에서는 빈 리스트를 반환해야 한다."""
    from pipeline.collectors.kowas_loader import list_local_pdfs

    result = list_local_pdfs(tmp_path)
    assert result == []


# ---------------------------------------------------------------------------
# Case 4: list_local_pdfs — 정렬 검증 (최신순, 2026-W17 첫 번째)
# ---------------------------------------------------------------------------
def test_list_local_pdfs_sorted(tmp_path: Path) -> None:
    """PDF 파일들을 최신순(연·주 기준 내림차순)으로 반환해야 한다."""
    from pipeline.collectors.kowas_loader import list_local_pdfs

    for name in ["kowas_2026_w15.pdf", "kowas_2026_w17.pdf", "kowas_2025_w50.pdf"]:
        (tmp_path / name).write_bytes(b"%PDF")

    result = list_local_pdfs(tmp_path)

    assert len(result) == 3
    # 첫 번째 항목이 가장 최신 (2026-W17)
    assert result[0][1:] == (2026, 17)
    # 두 번째: 2026-W15
    assert result[1][1:] == (2026, 15)
    # 세 번째: 2025-W50
    assert result[2][1:] == (2025, 50)


# ---------------------------------------------------------------------------
# Case 5: insert_readings — insert_signal AsyncMock 2회 호출 확인
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_insert_readings_calls_insert_signal() -> None:
    """WeeklyReading 2개 전달 시 insert_signal이 2회 호출되어야 한다."""
    from datetime import datetime, timezone

    from pipeline.collectors.kowas_parser import WeeklyReading

    readings = [
        WeeklyReading(
            region="서울특별시",
            pathogen="influenza",
            year=2026,
            week=17,
            relative_level=65.0,
            bar_count=8,
        ),
        WeeklyReading(
            region="부산광역시",
            pathogen="influenza",
            year=2026,
            week=17,
            relative_level=40.0,
            bar_count=7,
        ),
    ]

    report_date = datetime(2026, 4, 26, tzinfo=timezone.utc)

    with patch(
        "pipeline.collectors.kowas_loader.insert_signal",
        new_callable=AsyncMock,
    ) as mock_insert:
        from pipeline.collectors.kowas_loader import insert_readings

        await insert_readings(readings, report_date)

        assert mock_insert.call_count == 2


# ---------------------------------------------------------------------------
# Case 6: list_local_pdfs — 패턴 불일치 파일은 무시 (라인 69 커버)
# ---------------------------------------------------------------------------
def test_list_local_pdfs_skips_invalid_names(tmp_path: Path) -> None:
    """파일명이 패턴에 맞지 않으면 결과에서 제외해야 한다."""
    from pipeline.collectors.kowas_loader import list_local_pdfs

    # 유효한 파일 1개 + 패턴 불일치 1개
    (tmp_path / "kowas_2026_w17.pdf").write_bytes(b"%PDF")
    (tmp_path / "kowas_report.pdf").write_bytes(b"%PDF")  # 패턴 불일치

    result = list_local_pdfs(tmp_path)

    assert len(result) == 1
    assert result[0][1:] == (2026, 17)


# ---------------------------------------------------------------------------
# Case 7: insert_readings — insert_signal 예외 시 나머지 계속 처리 (라인 96-97)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_insert_readings_exception_continues() -> None:
    """insert_signal이 예외를 던져도 나머지 readings는 처리해야 한다."""
    from pipeline.collectors.kowas_parser import WeeklyReading

    readings = [
        WeeklyReading(
            region="서울특별시",
            pathogen="influenza",
            year=2026,
            week=17,
            relative_level=65.0,
            bar_count=8,
        ),
        WeeklyReading(
            region="부산광역시",
            pathogen="influenza",
            year=2026,
            week=17,
            relative_level=40.0,
            bar_count=7,
        ),
    ]

    report_date = datetime(2026, 4, 26, tzinfo=timezone.utc)

    # 첫 번째 호출만 예외 발생, 두 번째는 정상
    mock_insert = AsyncMock(side_effect=[RuntimeError("DB 연결 실패"), None])

    with patch(
        "pipeline.collectors.kowas_loader.insert_signal",
        mock_insert,
    ):
        from pipeline.collectors.kowas_loader import insert_readings

        # 예외가 전파되지 않고 inserted=1 반환 (성공한 1건만 카운트)
        result = await insert_readings(readings, report_date)

    assert result == 1
    assert mock_insert.call_count == 2


# ---------------------------------------------------------------------------
# Case 8: insert_readings — DB_TARGET_PATHOGENS 외 병원체는 스킵 (라인 83-84)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_insert_readings_skips_unknown_pathogen() -> None:
    """DB_TARGET_PATHOGENS에 없는 병원체는 insert_signal을 호출하지 않아야 한다."""
    from pipeline.collectors.kowas_parser import WeeklyReading

    readings = [
        WeeklyReading(
            region="서울특별시",
            pathogen="influenza",  # type: ignore[arg-type]
            year=2026,
            week=17,
            relative_level=65.0,
            bar_count=8,
        ),
        WeeklyReading(
            region="경기도",
            pathogen="rsv",  # type: ignore[arg-type]  # DB_TARGET_PATHOGENS 외
            year=2026,
            week=17,
            relative_level=30.0,
            bar_count=4,
        ),
    ]

    report_date = datetime(2026, 4, 26, tzinfo=timezone.utc)

    with patch(
        "pipeline.collectors.kowas_loader.insert_signal",
        new_callable=AsyncMock,
    ) as mock_insert:
        from pipeline.collectors.kowas_loader import insert_readings

        result = await insert_readings(readings, report_date)

    # influenza만 삽입됨 (rsv는 스킵)
    assert result == 1
    assert mock_insert.call_count == 1


# ---------------------------------------------------------------------------
# Case 9: load_pdf — parse_report 결과 적재 + JSON 캐시 생성 (라인 111-125)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_load_pdf_caches_json_and_inserts(tmp_path: Path) -> None:
    """load_pdf는 JSON 캐시를 생성하고 insert_readings를 호출해야 한다."""
    from pipeline.collectors.kowas_parser import WeeklyReading

    fake_readings = [
        WeeklyReading(
            region="서울특별시",
            pathogen="influenza",
            year=2026,
            week=17,
            relative_level=70.0,
            bar_count=9,
        ),
    ]

    fake_pdf = tmp_path / "kowas_2026_w17.pdf"
    fake_pdf.write_bytes(b"%PDF")

    with (
        patch(
            "pipeline.collectors.kowas_loader.parse_report",
            return_value=fake_readings,
        ),
        patch(
            "pipeline.collectors.kowas_loader.insert_signal",
            new_callable=AsyncMock,
        ),
        patch(
            "pipeline.collectors.kowas_loader.JSON_CACHE_DIR",
            tmp_path / "parsed",
        ),
    ):
        from pipeline.collectors.kowas_loader import load_pdf

        inserted, readings = await load_pdf(fake_pdf, 2026, 17, cache_json=True)

    assert inserted == 1
    assert len(readings) == 1
    cache_file = tmp_path / "parsed" / "kowas_2026_w17.json"
    assert cache_file.exists()
    data = json.loads(cache_file.read_text(encoding="utf-8"))
    assert data[0]["region"] == "서울특별시"


# ---------------------------------------------------------------------------
# Case 10: run(skip_db=True) — parse_report만 호출하고 load_pdf 미호출 (라인 150-159)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_skip_db(tmp_path: Path) -> None:
    """skip_db=True 시 parse_report만 실행되고 DB 삽입은 발생하지 않아야 한다."""
    from pipeline.collectors.kowas_parser import WeeklyReading

    # PDF 파일 생성
    pdf_file = tmp_path / "kowas_2026_w17.pdf"
    pdf_file.write_bytes(b"%PDF")

    fake_readings = [
        WeeklyReading(
            region="서울특별시",
            pathogen="influenza",
            year=2026,
            week=17,
            relative_level=60.0,
            bar_count=7,
        ),
    ]

    with (
        patch(
            "pipeline.collectors.kowas_loader.list_local_pdfs",
            return_value=[(pdf_file, 2026, 17)],
        ),
        patch(
            "pipeline.collectors.kowas_loader.parse_report",
            return_value=fake_readings,
        ) as mock_parse,
        patch(
            "pipeline.collectors.kowas_loader.insert_signal",
            new_callable=AsyncMock,
        ) as mock_insert,
        patch(
            "pipeline.collectors.kowas_loader.JSON_CACHE_DIR",
            tmp_path / "parsed",
        ),
    ):
        from pipeline.collectors.kowas_loader import run

        await run(
            weeks_limit=None,
            download_first=False,
            download_limit=None,
            skip_db=True,
        )

    mock_parse.assert_called_once()
    mock_insert.assert_not_called()


# ---------------------------------------------------------------------------
# Case 11: run(skip_db=False) 정상 — load_pdf 호출로 DB 적재 (라인 160-161)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_with_db(tmp_path: Path) -> None:
    """skip_db=False 시 load_pdf가 호출되고 total_inserted가 집계되어야 한다."""
    from pipeline.collectors.kowas_parser import WeeklyReading

    pdf_file = tmp_path / "kowas_2026_w17.pdf"
    pdf_file.write_bytes(b"%PDF")

    fake_readings = [
        WeeklyReading(
            region="서울특별시",
            pathogen="influenza",
            year=2026,
            week=17,
            relative_level=70.0,
            bar_count=8,
        ),
    ]

    with (
        patch(
            "pipeline.collectors.kowas_loader.list_local_pdfs",
            return_value=[(pdf_file, 2026, 17)],
        ),
        patch(
            "pipeline.collectors.kowas_loader.load_pdf",
            new_callable=AsyncMock,
            return_value=(1, fake_readings),
        ) as mock_load,
    ):
        from pipeline.collectors.kowas_loader import run

        await run(
            weeks_limit=None,
            download_first=False,
            download_limit=None,
            skip_db=False,
        )

    mock_load.assert_called_once_with(pdf_file, 2026, 17)


# ---------------------------------------------------------------------------
# Case 12: run() — load_pdf 예외 시 fallback carry-forward 경로 (라인 162-212)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_fallback_on_exception(tmp_path: Path) -> None:
    """load_pdf 예외 시 _apply_wastewater_fallback이 호출되어야 한다."""
    pdf_file = tmp_path / "kowas_2026_w17.pdf"
    pdf_file.write_bytes(b"%PDF")

    # DB 커넥션 mock
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    mock_pool = MagicMock()
    mock_pool.acquire = _acquire

    mock_session = AsyncMock()

    @asynccontextmanager
    async def _make_session():
        yield mock_session

    fallback_row = {
        "ts": datetime(2026, 4, 19, tzinfo=timezone.utc),
        "value": 55.0,
        "raw_value": 7.0,
        "source": "kowas:influenza",
        "pathogen": "influenza",
    }

    with (
        patch(
            "pipeline.collectors.kowas_loader.list_local_pdfs",
            return_value=[(pdf_file, 2026, 17)],
        ),
        patch(
            "pipeline.collectors.kowas_loader.load_pdf",
            new_callable=AsyncMock,
            side_effect=RuntimeError("파싱 실패"),
        ),
        patch(
            "pipeline.collectors.kowas_loader._apply_wastewater_fallback",
            new_callable=AsyncMock,
            return_value=fallback_row,
        ) as mock_fallback,
        patch(
            "pipeline.collectors.db_writer._get_pool",
            new_callable=AsyncMock,
            return_value=mock_pool,
        ),
        patch(
            "backend.app.database.async_session",
            _make_session,
        ),
    ):
        from pipeline.collectors.kowas_loader import run

        await run(
            weeks_limit=None,
            download_first=False,
            download_limit=None,
            skip_db=False,
        )

    # SIDO_ORDER 17개 지역 각각에 대해 fallback 호출됨
    assert mock_fallback.call_count == 17
    # 각 지역마다 conn.execute 호출됨
    assert mock_conn.execute.call_count == 17


# ---------------------------------------------------------------------------
# Case 13: run() — fallback row가 None일 때 스킵 (라인 199-204)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_fallback_none_skips_insert(tmp_path: Path) -> None:
    """fallback_row가 None이면 INSERT를 스킵하고 에러 로그만 남겨야 한다."""
    pdf_file = tmp_path / "kowas_2026_w17.pdf"
    pdf_file.write_bytes(b"%PDF")

    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    mock_pool = MagicMock()
    mock_pool.acquire = _acquire

    mock_session = AsyncMock()

    @asynccontextmanager
    async def _make_session():
        yield mock_session

    with (
        patch(
            "pipeline.collectors.kowas_loader.list_local_pdfs",
            return_value=[(pdf_file, 2026, 17)],
        ),
        patch(
            "pipeline.collectors.kowas_loader.load_pdf",
            new_callable=AsyncMock,
            side_effect=RuntimeError("파싱 실패"),
        ),
        patch(
            "pipeline.collectors.kowas_loader._apply_wastewater_fallback",
            new_callable=AsyncMock,
            return_value=None,  # fallback 데이터 없음
        ),
        patch(
            "pipeline.collectors.db_writer._get_pool",
            new_callable=AsyncMock,
            return_value=mock_pool,
        ),
        patch(
            "backend.app.database.async_session",
            _make_session,
        ),
    ):
        from pipeline.collectors.kowas_loader import run

        await run(
            weeks_limit=None,
            download_first=False,
            download_limit=None,
            skip_db=False,
        )

    # fallback 없으면 conn.execute 호출 안 됨
    mock_conn.execute.assert_not_called()


# ---------------------------------------------------------------------------
# Case 14: run(weeks_limit=1) — weeks_limit 슬라이싱 검증
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_run_weeks_limit(tmp_path: Path) -> None:
    """weeks_limit=1이면 PDF 목록에서 가장 최신 1건만 처리해야 한다."""
    pdf1 = tmp_path / "kowas_2026_w17.pdf"
    pdf2 = tmp_path / "kowas_2026_w16.pdf"
    pdf1.write_bytes(b"%PDF")
    pdf2.write_bytes(b"%PDF")

    from pipeline.collectors.kowas_parser import WeeklyReading

    fake_readings: list[WeeklyReading] = []

    with (
        patch(
            "pipeline.collectors.kowas_loader.list_local_pdfs",
            return_value=[(pdf1, 2026, 17), (pdf2, 2026, 16)],
        ),
        patch(
            "pipeline.collectors.kowas_loader.load_pdf",
            new_callable=AsyncMock,
            return_value=(0, fake_readings),
        ) as mock_load,
    ):
        from pipeline.collectors.kowas_loader import run

        await run(
            weeks_limit=1,
            download_first=False,
            download_limit=None,
            skip_db=False,
        )

    # weeks_limit=1이므로 첫 번째 PDF만 처리
    assert mock_load.call_count == 1
    mock_load.assert_called_once_with(pdf1, 2026, 17)
