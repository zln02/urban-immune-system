"""pipeline/collectors/kowas_loader.py 단위 테스트."""
from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import AsyncMock, patch

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
    from pipeline.collectors.kowas_loader import iso_week_end_date

    # 직접 계산: date.fromisocalendar(2026, 17, 1) + 6일
    from datetime import timedelta

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
