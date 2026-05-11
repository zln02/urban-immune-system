"""pipeline/collectors/kowas_parser.py 단위 테스트."""
from __future__ import annotations

import numpy as np
import pytest


# ---------------------------------------------------------------------------
# Case 1: SIDO_ORDER 길이 검증
# ---------------------------------------------------------------------------
def test_sido_order_length() -> None:
    """SIDO_ORDER는 17개 시·도를 포함해야 한다."""
    from pipeline.collectors.kowas_parser import SIDO_ORDER

    assert len(SIDO_ORDER) == 17


# ---------------------------------------------------------------------------
# Case 2: SIDO_ORDER에 서울특별시 포함 확인
# ---------------------------------------------------------------------------
def test_sido_order_contains_seoul() -> None:
    """SIDO_ORDER에 '서울특별시'가 포함되어야 한다."""
    from pipeline.collectors.kowas_parser import SIDO_ORDER

    assert "서울특별시" in SIDO_ORDER


# ---------------------------------------------------------------------------
# Case 3: _segment_bars — 픽셀 없음 → 빈 리스트
# ---------------------------------------------------------------------------
def test_segment_bars_empty() -> None:
    """모두 0인 배열을 전달하면 빈 리스트를 반환해야 한다."""
    from pipeline.collectors.kowas_parser import _segment_bars

    arr = np.zeros(100, dtype=int)
    result = _segment_bars(arr)
    assert result == []


# ---------------------------------------------------------------------------
# Case 4: _segment_bars — 단일 피크 구간 → 튜플 1개 반환
# ---------------------------------------------------------------------------
def test_segment_bars_single_peak() -> None:
    """중간 구간에 픽셀이 있으면 (start, end) 튜플 1개를 반환해야 한다."""
    from pipeline.collectors.kowas_parser import _segment_bars

    arr = np.zeros(100, dtype=int)
    arr[30:60] = 10  # 30~59 구간에 픽셀

    result = _segment_bars(arr, min_count=3)

    assert len(result) == 1
    start, end = result[0]
    assert start <= 30
    assert end >= 59


# ---------------------------------------------------------------------------
# Case 5: _measure_bar_height — 하단 N행이 True인 mask → N 반환
# ---------------------------------------------------------------------------
def test_measure_bar_height() -> None:
    """하단 N행이 True인 mask를 전달하면 높이 N을 반환해야 한다."""
    from pipeline.collectors.kowas_parser import _measure_bar_height

    height = 20  # 검출할 막대 높이
    rows = 50
    cols = 10

    mask = np.zeros((rows, cols), dtype=bool)
    # 하단 height 행을 True로 설정
    mask[rows - height :, :] = True

    result = _measure_bar_height(mask, x_start=0, x_end=cols - 1)
    assert result == height


# ---------------------------------------------------------------------------
# Case 6: WeeklyReading frozen=True — 필드 수정 시 FrozenInstanceError
# ---------------------------------------------------------------------------
def test_weekly_reading_frozen() -> None:
    """WeeklyReading은 frozen dataclass여서 필드 수정 시 FrozenInstanceError가 발생해야 한다."""
    from dataclasses import FrozenInstanceError

    from pipeline.collectors.kowas_parser import WeeklyReading

    reading = WeeklyReading(
        region="서울특별시",
        pathogen="influenza",
        year=2026,
        week=17,
        relative_level=65.4,
        bar_count=10,
    )

    with pytest.raises(FrozenInstanceError):
        reading.relative_level = 99.9  # type: ignore[misc]
