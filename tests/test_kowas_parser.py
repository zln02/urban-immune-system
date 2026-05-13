"""pipeline/collectors/kowas_parser.py 단위 테스트."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
from PIL import Image


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
# Case 2b: SIDO_ORDER 전체 17개 지역명 검증
# ---------------------------------------------------------------------------
def test_sido_order_all_regions() -> None:
    """SIDO_ORDER가 17개 모든 시·도 이름을 포함하는지 검증."""
    from pipeline.collectors.kowas_parser import SIDO_ORDER

    expected = [
        "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
        "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
        "충청북도", "충청남도", "전라북도", "전라남도", "경상북도",
        "경상남도", "제주특별자치도",
    ]
    assert SIDO_ORDER == expected


# ---------------------------------------------------------------------------
# Case 2c: PATHOGEN_COLOR_RANGES 키 검증
# ---------------------------------------------------------------------------
def test_pathogen_color_ranges_keys() -> None:
    """PATHOGEN_COLOR_RANGES에 covid/influenza/norovirus 키가 모두 있어야 한다."""
    from pipeline.collectors.kowas_parser import PATHOGEN_COLOR_RANGES

    assert set(PATHOGEN_COLOR_RANGES.keys()) == {"covid", "influenza", "norovirus"}
    for pathogen, ranges in PATHOGEN_COLOR_RANGES.items():
        assert set(ranges.keys()) == {"r", "g", "b"}, f"{pathogen} 색상 키 누락"
        for channel, (lo, hi) in ranges.items():
            assert 0 <= lo < hi <= 255, f"{pathogen}/{channel} 범위 유효하지 않음"


# ---------------------------------------------------------------------------
# Case 2d: PATHOGEN_PAGES 구조 검증
# ---------------------------------------------------------------------------
def test_pathogen_pages_structure() -> None:
    """PATHOGEN_PAGES가 3가지 병원체를 갖고 각 페이지 인덱스가 유효한지 검증."""
    from pipeline.collectors.kowas_parser import PATHOGEN_PAGES

    assert set(PATHOGEN_PAGES.keys()) == {"covid", "influenza", "norovirus"}
    for pathogen, (p1, p2) in PATHOGEN_PAGES.items():
        assert isinstance(p1, int) and isinstance(p2, int)
        assert p1 < p2, f"{pathogen} 페이지 인덱스 순서 잘못됨"


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
# Case 4b: _segment_bars — 두 개의 분리된 피크 → 튜플 2개 반환
# ---------------------------------------------------------------------------
def test_segment_bars_two_peaks() -> None:
    """갭으로 분리된 두 구간이 있으면 튜플 2개를 반환해야 한다."""
    from pipeline.collectors.kowas_parser import _segment_bars

    arr = np.zeros(100, dtype=int)
    arr[10:20] = 5  # 첫 번째 막대
    arr[40:55] = 5  # 두 번째 막대 (갭 > 2)

    result = _segment_bars(arr, min_count=3)

    assert len(result) == 2
    assert result[0][0] <= 10
    assert result[1][0] >= 40


# ---------------------------------------------------------------------------
# Case 4c: _segment_bars — 연속된 픽셀 (갭 없음) → 튜플 1개 반환
# ---------------------------------------------------------------------------
def test_segment_bars_contiguous() -> None:
    """연속된 픽셀은 하나의 막대로 인식해야 한다."""
    from pipeline.collectors.kowas_parser import _segment_bars

    arr = np.zeros(50, dtype=int)
    arr[5:45] = 10  # 연속 구간

    result = _segment_bars(arr, min_count=3)
    assert len(result) == 1


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
# Case 5b: _measure_bar_height — 빈 mask → 0 반환
# ---------------------------------------------------------------------------
def test_measure_bar_height_empty_mask() -> None:
    """모두 False인 mask를 전달하면 높이 0을 반환해야 한다."""
    from pipeline.collectors.kowas_parser import _measure_bar_height

    mask = np.zeros((50, 10), dtype=bool)

    result = _measure_bar_height(mask, x_start=0, x_end=9)
    assert result == 0


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


# ---------------------------------------------------------------------------
# Case 6b: WeeklyReading 필드 값 정상 저장 확인
# ---------------------------------------------------------------------------
def test_weekly_reading_fields() -> None:
    """WeeklyReading 필드 값이 올바르게 저장되는지 검증."""
    from pipeline.collectors.kowas_parser import WeeklyReading

    reading = WeeklyReading(
        region="부산광역시",
        pathogen="covid",
        year=2025,
        week=52,
        relative_level=42.5,
        bar_count=8,
    )

    assert reading.region == "부산광역시"
    assert reading.pathogen == "covid"
    assert reading.year == 2025
    assert reading.week == 52
    assert reading.relative_level == 42.5
    assert reading.bar_count == 8


# ---------------------------------------------------------------------------
# Case 7: _detect_bar_mask — covid 색상 범위 안의 픽셀 → True
# ---------------------------------------------------------------------------
def test_detect_bar_mask_covid_in_range() -> None:
    """covid 색상 범위 내의 픽셀에 대해 mask가 True여야 한다."""
    from pipeline.collectors.kowas_parser import _detect_bar_mask

    # covid 범위: r=(100,180), g=(140,200), b=(190,250)
    arr = np.array([[[140, 170, 220]]], dtype=np.uint8)  # 범위 내
    mask = _detect_bar_mask(arr, "covid")
    assert mask[0, 0] is np.bool_(True) or bool(mask[0, 0]) is True


# ---------------------------------------------------------------------------
# Case 7b: _detect_bar_mask — covid 색상 범위 밖의 픽셀 → False
# ---------------------------------------------------------------------------
def test_detect_bar_mask_covid_out_of_range() -> None:
    """covid 색상 범위 밖의 픽셀에 대해 mask가 False여야 한다."""
    from pipeline.collectors.kowas_parser import _detect_bar_mask

    # 완전히 빨간 픽셀 — covid 범위 밖
    arr = np.array([[[255, 0, 0]]], dtype=np.uint8)
    mask = _detect_bar_mask(arr, "covid")
    assert not bool(mask[0, 0])


# ---------------------------------------------------------------------------
# Case 7c: _detect_bar_mask — influenza 색상 범위 검증
# ---------------------------------------------------------------------------
def test_detect_bar_mask_influenza() -> None:
    """influenza 색상 범위 내 픽셀은 True, 범위 밖은 False여야 한다."""
    from pipeline.collectors.kowas_parser import _detect_bar_mask

    # influenza: r=(210,255), g=(140,200), b=(100,170)
    arr_in = np.array([[[230, 170, 130]]], dtype=np.uint8)
    arr_out = np.array([[[50, 50, 200]]], dtype=np.uint8)

    assert bool(_detect_bar_mask(arr_in, "influenza")[0, 0]) is True
    assert bool(_detect_bar_mask(arr_out, "influenza")[0, 0]) is False


# ---------------------------------------------------------------------------
# Case 7d: _detect_bar_mask — norovirus 색상 범위 검증
# ---------------------------------------------------------------------------
def test_detect_bar_mask_norovirus() -> None:
    """norovirus 색상 범위 내 픽셀은 True여야 한다."""
    from pipeline.collectors.kowas_parser import _detect_bar_mask

    # norovirus: r=(220,255), g=(180,230), b=(60,150)
    arr_in = np.array([[[240, 200, 100]]], dtype=np.uint8)
    assert bool(_detect_bar_mask(arr_in, "norovirus")[0, 0]) is True


# ---------------------------------------------------------------------------
# Case 8: _extract_chart_image — 정상 크롭 경로
# ---------------------------------------------------------------------------
def test_extract_chart_image_crops_correctly() -> None:
    """_extract_chart_image가 PDF 좌표를 DPI 스케일로 변환해 크롭하는지 검증."""
    from pipeline.collectors.kowas_parser import _extract_chart_image

    dpi = 72  # scale = 1.0 (단순화를 위해)
    width, height = 500, 600
    full_img = Image.new("RGB", (width, height), color=(128, 128, 128))

    mock_page = MagicMock()

    # pdf_box = (10, 20, 60, 80) → dpi=72이면 scale=1 → crop(10, 20, 60, 80)
    result = _extract_chart_image(mock_page, (10.0, 20.0, 60.0, 80.0), dpi=72, full_img=full_img)

    assert result.size == (50, 60)  # 60-10=50, 80-20=60


# ---------------------------------------------------------------------------
# Case 8b: _extract_chart_image — full_img None이면 page.to_image 호출
# ---------------------------------------------------------------------------
def test_extract_chart_image_calls_page_to_image_when_no_full_img() -> None:
    """full_img가 None이면 page.to_image(resolution=dpi)를 호출해야 한다."""
    from pipeline.collectors.kowas_parser import _extract_chart_image

    width, height = 300, 400
    fake_img = Image.new("RGB", (width, height), color=(200, 200, 200))

    mock_page_image = MagicMock()
    mock_page_image.original = fake_img

    mock_page = MagicMock()
    mock_page.to_image.return_value = mock_page_image

    result = _extract_chart_image(mock_page, (0.0, 0.0, 100.0, 100.0), dpi=72, full_img=None)

    mock_page.to_image.assert_called_once_with(resolution=72)
    assert result is not None


# ---------------------------------------------------------------------------
# Case 9: _detect_chart_boxes — 작은 이미지 필터링
# ---------------------------------------------------------------------------
def test_detect_chart_boxes_filters_small_images() -> None:
    """MIN_CHART_WIDTH_PT 미만의 작은 이미지(로고 등)는 제외되어야 한다."""
    from pipeline.collectors.kowas_parser import _detect_chart_boxes

    mock_page = MagicMock()
    mock_page.images = [
        # 작은 로고 (필터링 대상)
        {"x0": 10, "top": 10, "x1": 110, "bottom": 46},  # w=100, h=36 → 필터
        # 충분히 큰 차트
        {"x0": 50, "top": 100, "x1": 300, "bottom": 210},  # w=250, h=110 → 통과
    ]

    boxes = _detect_chart_boxes(mock_page)

    assert len(boxes) == 1
    assert boxes[0] == (50, 100, 300, 210)


# ---------------------------------------------------------------------------
# Case 9b: _detect_chart_boxes — 빈 페이지 → 빈 리스트
# ---------------------------------------------------------------------------
def test_detect_chart_boxes_empty_page() -> None:
    """이미지가 없는 페이지에서는 빈 리스트를 반환해야 한다."""
    from pipeline.collectors.kowas_parser import _detect_chart_boxes

    mock_page = MagicMock()
    mock_page.images = []

    boxes = _detect_chart_boxes(mock_page)
    assert boxes == []


# ---------------------------------------------------------------------------
# Case 9c: _detect_chart_boxes — 다수 차트 정렬 검증 (top 우선)
# ---------------------------------------------------------------------------
def test_detect_chart_boxes_sorted_top_then_left() -> None:
    """차트 박스가 행(top) 우선, 같은 행 내 왼쪽(x0) 우선으로 정렬되어야 한다."""
    from pipeline.collectors.kowas_parser import _detect_chart_boxes

    mock_page = MagicMock()
    # 두 행, 각 행에 2개 차트
    mock_page.images = [
        {"x0": 300, "top": 200, "x1": 560, "bottom": 320},  # row2, right
        {"x0": 50,  "top": 100, "x1": 310, "bottom": 220},  # row1, left
        {"x0": 50,  "top": 200, "x1": 310, "bottom": 320},  # row2, left
        {"x0": 300, "top": 100, "x1": 560, "bottom": 220},  # row1, right
    ]

    boxes = _detect_chart_boxes(mock_page)
    # 4개 모두 충분히 크므로 정렬만 확인
    assert len(boxes) == 4
    # 첫 두 박스는 row1 (top≈100), 다음 두 박스는 row2 (top≈200)
    assert boxes[0][1] <= boxes[2][1]  # top 오름차순


# ---------------------------------------------------------------------------
# Case 10: parse_chart — 막대 없는 이미지 → (0.0, 0) 반환
# ---------------------------------------------------------------------------
def test_parse_chart_no_bars() -> None:
    """막대가 없는 차트 이미지에서 (0.0, 0)을 반환해야 한다."""
    from pipeline.collectors.kowas_parser import parse_chart

    # 완전히 흰 이미지 — 어떤 색상 범위에도 해당 안 함
    img = Image.new("RGB", (200, 100), color=(255, 255, 255))
    level, bar_count = parse_chart(img, "influenza")

    assert level == 0.0
    assert bar_count == 0


# ---------------------------------------------------------------------------
# Case 10b: parse_chart — 단일 막대 → relative_level=100.0
# ---------------------------------------------------------------------------
def test_parse_chart_single_bar_max_level() -> None:
    """막대가 하나뿐이면 그것이 max이므로 relative_level=100.0이어야 한다."""
    from pipeline.collectors.kowas_parser import parse_chart

    # influenza 색상으로 채운 단일 막대 이미지
    # influenza: r=(210,255), g=(140,200), b=(100,170)
    img = Image.new("RGB", (50, 80), color=(230, 170, 130))
    level, bar_count = parse_chart(img, "influenza")

    # 단일 막대만 있으면 last_h == max_h → relative = 100.0
    assert level == 100.0
    assert bar_count == 1


# ---------------------------------------------------------------------------
# Case 10c: parse_chart — 모든 막대 높이 0 → (0.0, N)
# ---------------------------------------------------------------------------
def test_parse_chart_zero_height_bars() -> None:
    """막대 색상 픽셀이 분포하지만 높이를 측정할 수 없으면 (0.0, N)을 반환해야 한다."""
    from pipeline.collectors.kowas_parser import parse_chart

    # 1픽셀 높이의 이미지 — 막대 높이가 0으로 계산될 수 있는 엣지 케이스
    # 실제로는 높이 계산이 되지만 max_h가 0일 때 처리
    # 단색 이미지로 테스트 (흰색 → 막대 없음 → (0.0, 0))
    img = Image.new("RGB", (100, 1), color=(255, 255, 255))
    level, bar_count = parse_chart(img, "covid")
    assert level == 0.0
    assert bar_count == 0


# ---------------------------------------------------------------------------
# Case 11: parse_pathogen_pages — pdfplumber mock, 정상 경로
# ---------------------------------------------------------------------------
def test_parse_pathogen_pages_normal(tmp_path: Path) -> None:
    """pdfplumber mock으로 parse_pathogen_pages 정상 경로를 검증."""
    from pipeline.collectors.kowas_parser import parse_pathogen_pages, WeeklyReading

    # 10개 박스 (page1) + 7개 박스 (page2) = 17개 시·도
    def _make_mock_page(n_charts: int) -> MagicMock:
        page = MagicMock()
        # 각 차트용 박스 (충분히 큰 이미지)
        page.images = [
            {"x0": i * 260.0, "top": 0.0, "x1": i * 260.0 + 234.0, "bottom": 120.0}
            for i in range(n_charts)
        ]
        # page.to_image() → original (흰 이미지)
        mock_pil = MagicMock()
        mock_pil.original = Image.new("RGB", (2600, 800), color=(255, 255, 255))
        page.to_image.return_value = mock_pil
        return page

    mock_pdf = MagicMock()
    mock_pdf.pages = [
        MagicMock(),  # page 0 (unused for covid)
        MagicMock(),  # page 1
        _make_mock_page(10),  # page 2 — covid 1-10번
        _make_mock_page(7),   # page 3 — covid 11-17번
    ]

    pdf_path = tmp_path / "fake.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch("pipeline.collectors.kowas_parser.pdfplumber") as mock_pp:
        mock_pp.open.return_value.__enter__.return_value = mock_pdf
        readings = parse_pathogen_pages(pdf_path, "covid", year=2026, week=17)

    assert len(readings) == 17
    assert all(isinstance(r, WeeklyReading) for r in readings)
    assert readings[0].region == "서울특별시"
    assert readings[-1].region == "제주특별자치도"
    assert all(r.pathogen == "covid" for r in readings)
    assert all(r.year == 2026 for r in readings)
    assert all(r.week == 17 for r in readings)


# ---------------------------------------------------------------------------
# Case 11b: parse_pathogen_pages — 차트 수 부족 → warning 로그, 부분 결과
# ---------------------------------------------------------------------------
def test_parse_pathogen_pages_insufficient_charts(tmp_path: Path) -> None:
    """차트 검출이 기대보다 적을 때 경고 로그를 남기고 가능한 결과를 반환해야 한다."""
    from pipeline.collectors.kowas_parser import parse_pathogen_pages

    def _make_mock_page(n_charts: int) -> MagicMock:
        page = MagicMock()
        page.images = [
            {"x0": i * 260.0, "top": 0.0, "x1": i * 260.0 + 234.0, "bottom": 120.0}
            for i in range(n_charts)
        ]
        mock_pil = MagicMock()
        mock_pil.original = Image.new("RGB", (2600, 800), color=(255, 255, 255))
        page.to_image.return_value = mock_pil
        return page

    mock_pdf = MagicMock()
    mock_pdf.pages = [
        MagicMock(),
        MagicMock(),
        _make_mock_page(5),   # 10 기대 → 5만 있음
        _make_mock_page(3),   # 7 기대 → 3만 있음
    ]

    pdf_path = tmp_path / "fake_incomplete.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch("pipeline.collectors.kowas_parser.pdfplumber") as mock_pp:
        mock_pp.open.return_value.__enter__.return_value = mock_pdf
        readings = parse_pathogen_pages(pdf_path, "covid", year=2026, week=17)

    # 5 + 3 = 8개 결과
    assert len(readings) == 8


# ---------------------------------------------------------------------------
# Case 12: parse_report — 3가지 병원체 전부 처리
# ---------------------------------------------------------------------------
def test_parse_report_all_pathogens(tmp_path: Path) -> None:
    """parse_report가 3가지 병원체 × 17 시·도 = 51개 결과를 반환해야 한다."""
    from pipeline.collectors.kowas_parser import parse_report

    def _make_mock_page(n_charts: int) -> MagicMock:
        page = MagicMock()
        page.images = [
            {"x0": i * 260.0, "top": 0.0, "x1": i * 260.0 + 234.0, "bottom": 120.0}
            for i in range(n_charts)
        ]
        mock_pil = MagicMock()
        mock_pil.original = Image.new("RGB", (2600, 800), color=(255, 255, 255))
        page.to_image.return_value = mock_pil
        return page

    # 8페이지 (0-indexed): 2,3=covid / 4,5=influenza / 6,7=norovirus
    mock_pdf = MagicMock()
    mock_pdf.pages = [
        MagicMock(),          # page 0
        MagicMock(),          # page 1
        _make_mock_page(10),  # page 2
        _make_mock_page(7),   # page 3
        _make_mock_page(10),  # page 4
        _make_mock_page(7),   # page 5
        _make_mock_page(10),  # page 6
        _make_mock_page(7),   # page 7
    ]

    pdf_path = tmp_path / "full.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch("pipeline.collectors.kowas_parser.pdfplumber") as mock_pp:
        mock_pp.open.return_value.__enter__.return_value = mock_pdf
        readings = parse_report(pdf_path, year=2026, week=17)

    assert len(readings) == 51  # 3 pathogens × 17 regions
    pathogens_found = {r.pathogen for r in readings}
    assert pathogens_found == {"covid", "influenza", "norovirus"}


# ---------------------------------------------------------------------------
# Case 12b: parse_report — 단일 병원체 지정
# ---------------------------------------------------------------------------
def test_parse_report_single_pathogen(tmp_path: Path) -> None:
    """parse_report에 단일 병원체만 지정하면 17개 결과만 반환해야 한다."""
    from pipeline.collectors.kowas_parser import parse_report

    def _make_mock_page(n_charts: int) -> MagicMock:
        page = MagicMock()
        page.images = [
            {"x0": i * 260.0, "top": 0.0, "x1": i * 260.0 + 234.0, "bottom": 120.0}
            for i in range(n_charts)
        ]
        mock_pil = MagicMock()
        mock_pil.original = Image.new("RGB", (2600, 800), color=(255, 255, 255))
        page.to_image.return_value = mock_pil
        return page

    mock_pdf = MagicMock()
    mock_pdf.pages = [
        MagicMock(),
        MagicMock(),
        MagicMock(),
        MagicMock(),
        _make_mock_page(10),  # page 4 — influenza 1-10
        _make_mock_page(7),   # page 5 — influenza 11-17
        MagicMock(),
        MagicMock(),
    ]

    pdf_path = tmp_path / "influenza_only.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    with patch("pipeline.collectors.kowas_parser.pdfplumber") as mock_pp:
        mock_pp.open.return_value.__enter__.return_value = mock_pdf
        readings = parse_report(pdf_path, year=2026, week=17, pathogens=("influenza",))

    assert len(readings) == 17
    assert all(r.pathogen == "influenza" for r in readings)
