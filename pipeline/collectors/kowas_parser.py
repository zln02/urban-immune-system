"""KOWAS 주간보고 PDF 파서.

PDF 차트 페이지에서 시·도별 바이러스 농도 막대를 픽셀 분석으로 추출한다.

핵심 아이디어:
  KDCA가 차트에 텍스트로 raw copies/mL 값을 노출하지 않고 그래프로만 표시하므로,
  차트 내 막대 높이 비율로 "누적 max 대비 이번 주 상대 수준"을 계산한다.
  이는 PDF 일러두기의 정의("각 시·도 바이러스 누적 수치 대비 이번 주 상대적 수준")와 일치하며
  L2 정규화 점수(0-100)로 그대로 사용 가능하다.

페이지 레이아웃 (2026-04 기준, 변경 시 LAYOUT 상수 수정):
  page 3-4: 코로나19 1-10, 11-17 시·도
  page 5-6: 인플루엔자
  page 7-8: 노로바이러스
  각 페이지: 2열 5행 차트 격자 (마지막 페이지는 17번까지만)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import pdfplumber
from PIL import Image

logger = logging.getLogger(__name__)

Pathogen = Literal["covid", "influenza", "norovirus"]

# 17개 시·도 순서 (PDF 차트 게재 순서 — 2026-04 기준 고정)
SIDO_ORDER = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전라북도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도",
]

# 병원체 → (1-10번 페이지 idx, 11-17번 페이지 idx) (0-based)
PATHOGEN_PAGES: dict[Pathogen, tuple[int, int]] = {
    "covid": (2, 3),
    "influenza": (4, 5),
    "norovirus": (6, 7),
}

# 페이지 내 차트 이미지 검출 임계값 — KDCA 로고(100x36)와 차트(234x105+) 구분
MIN_CHART_WIDTH_PT = 150  # PDF pt 단위, 차트 최소 너비
MIN_CHART_HEIGHT_PT = 60

# KDCA 차트 막대 색상 (병원체별로 다름, 2026-04 PDF 분석 결과)
#   covid       파랑   RGB ≈ (140, 170, 220)  → B 우세
#   influenza   주황   RGB ≈ (240, 170, 130)  → R>G>B
#   norovirus   노랑   RGB ≈ (250, 210, 100)  → R≈G, B 낮음
PATHOGEN_COLOR_RANGES: dict[Pathogen, dict[str, tuple[int, int]]] = {
    "covid":     {"r": (100, 180), "g": (140, 200), "b": (190, 250)},
    "influenza": {"r": (210, 255), "g": (140, 200), "b": (100, 170)},
    "norovirus": {"r": (220, 255), "g": (180, 230), "b":  (60, 150)},
}

DEFAULT_DPI = 300


@dataclass(frozen=True)
class WeeklyReading:
    """단일 시·도·병원체·주차 측정값."""

    region: str
    pathogen: Pathogen
    year: int
    week: int               # 보고된 주차 (= 이번 주, X축 마지막 막대)
    relative_level: float   # 0-100, 차트 내 누적 max 대비 비율
    bar_count: int          # 차트에서 검출된 총 막대 수 (품질 지표)


def _detect_bar_mask(arr: np.ndarray, pathogen: Pathogen) -> np.ndarray:
    """병원체별 막대 색상 mask를 반환한다 (H, W) bool."""
    rng = PATHOGEN_COLOR_RANGES[pathogen]
    r, g, b = arr[..., 0], arr[..., 1], arr[..., 2]
    return (
        (r >= rng["r"][0]) & (r <= rng["r"][1])
        & (g >= rng["g"][0]) & (g <= rng["g"][1])
        & (b >= rng["b"][0]) & (b <= rng["b"][1])
    )


def _segment_bars(col_orange_count: np.ndarray, min_count: int = 3) -> list[tuple[int, int]]:
    """컬럼별 주황 픽셀 수 시계열에서 막대 그룹들을 (start, end) 리스트로 분할."""
    cols = np.where(col_orange_count >= min_count)[0]
    if len(cols) == 0:
        return []

    bars: list[tuple[int, int]] = []
    grp_start = cols[0]
    prev = cols[0]
    for c in cols[1:]:
        if c - prev > 2:  # 갭 발견
            bars.append((grp_start, prev))
            grp_start = c
        prev = c
    bars.append((grp_start, prev))
    return bars


def _measure_bar_height(mask: np.ndarray, x_start: int, x_end: int) -> int:
    """주어진 컬럼 구간에서 막대 픽셀 높이(top~bottom)를 반환."""
    band = mask[:, x_start:x_end + 1]
    rows = band.any(axis=1)
    if not rows.any():
        return 0
    top = int(np.argmax(rows))
    bottom = len(rows) - 1 - int(np.argmax(rows[::-1]))
    return bottom - top + 1


def _extract_chart_image(
    page: pdfplumber.page.Page,
    pdf_box: tuple[float, float, float, float],
    dpi: int,
    full_img: Image.Image | None = None,
) -> Image.Image:
    """페이지 전체를 dpi로 렌더한 뒤 PDF 좌표에 해당하는 영역을 잘라낸다."""
    if full_img is None:
        full_img = page.to_image(resolution=dpi).original
    scale = dpi / 72
    x0, y0, x1, y1 = pdf_box
    box = (int(x0 * scale), int(y0 * scale), int(x1 * scale), int(y1 * scale))
    return full_img.crop(box)


def _detect_chart_boxes(page: pdfplumber.page.Page) -> list[tuple[float, float, float, float]]:
    """페이지 내 차트 이미지 bbox 리스트를 위→아래, 왼→오 순으로 반환.

    KDCA 로고 등 작은 이미지는 자동 제외 (MIN_CHART_WIDTH_PT 기준).
    """
    candidates: list[tuple[float, float, float, float]] = []
    for img in page.images:
        w = img["x1"] - img["x0"]
        h = img["bottom"] - img["top"]
        if w >= MIN_CHART_WIDTH_PT and h >= MIN_CHART_HEIGHT_PT:
            candidates.append((img["x0"], img["top"], img["x1"], img["bottom"]))
    # 행(top) 우선, 같은 행 내 왼쪽(x0) 우선 정렬 (행 그룹은 ±20pt 오차)
    candidates.sort(key=lambda b: (round(b[1] / 20), b[0]))
    return candidates


def parse_chart(chart_img: Image.Image, pathogen: Pathogen) -> tuple[float, int]:
    """단일 차트 이미지에서 '마지막 막대 / 누적 max 막대' 비율(0-100)을 계산한다.

    Returns:
        (relative_level, bar_count)
    """
    arr = np.array(chart_img.convert("RGB"))
    mask = _detect_bar_mask(arr, pathogen)
    col_count = mask.sum(axis=0)
    bars = _segment_bars(col_count)

    if not bars:
        return 0.0, 0

    heights = [_measure_bar_height(mask, s, e) for s, e in bars]
    max_h = max(heights)
    if max_h == 0:
        return 0.0, len(bars)

    last_h = heights[-1]
    relative = (last_h / max_h) * 100.0
    return round(relative, 2), len(bars)


def parse_pathogen_pages(
    pdf_path: Path,
    pathogen: Pathogen,
    year: int,
    week: int,
    dpi: int = DEFAULT_DPI,
) -> list[WeeklyReading]:
    """단일 PDF에서 한 병원체의 17개 시·도 측정값을 모두 추출."""
    page_idx_1, page_idx_2 = PATHOGEN_PAGES[pathogen]
    readings: list[WeeklyReading] = []

    def _process_page(page_idx: int, sido_offset: int, expected_count: int) -> None:
        page = pdf.pages[page_idx]
        full_img = page.to_image(resolution=dpi).original
        boxes = _detect_chart_boxes(page)
        if len(boxes) < expected_count:
            logger.warning(
                "p.%d 차트 검출 부족: %d개 (기대 %d) — 시·도 매핑 어긋날 수 있음",
                page_idx + 1, len(boxes), expected_count,
            )
        for i, box in enumerate(boxes[:expected_count]):
            sido_idx = sido_offset + i
            if sido_idx >= len(SIDO_ORDER):
                break
            chart = _extract_chart_image(page, box, dpi, full_img=full_img)
            level, bar_n = parse_chart(chart, pathogen)
            readings.append(WeeklyReading(
                region=SIDO_ORDER[sido_idx],
                pathogen=pathogen,
                year=year,
                week=week,
                relative_level=level,
                bar_count=bar_n,
            ))

    with pdfplumber.open(pdf_path) as pdf:
        _process_page(page_idx_1, sido_offset=0, expected_count=10)   # 1-10번
        _process_page(page_idx_2, sido_offset=10, expected_count=7)   # 11-17번

    return readings


def parse_report(
    pdf_path: Path,
    year: int,
    week: int,
    pathogens: tuple[Pathogen, ...] = ("covid", "influenza", "norovirus"),
) -> list[WeeklyReading]:
    """단일 KOWAS PDF에서 모든 병원체×시·도 측정값을 추출."""
    all_readings: list[WeeklyReading] = []
    for p in pathogens:
        all_readings.extend(parse_pathogen_pages(pdf_path, p, year, week))
    return all_readings


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    parser = argparse.ArgumentParser(description="KOWAS PDF 단일 파서")
    parser.add_argument("pdf", type=Path)
    parser.add_argument("--year", type=int, required=True)
    parser.add_argument("--week", type=int, required=True)
    parser.add_argument("--pathogen", choices=["covid", "influenza", "norovirus", "all"], default="all")
    args = parser.parse_args()

    pathogens = ("covid", "influenza", "norovirus") if args.pathogen == "all" else (args.pathogen,)
    results = parse_report(args.pdf, args.year, args.week, pathogens)

    print(f"\n=== {args.pdf.name} → {len(results)} readings ===")
    print(f"{'region':<14} {'pathogen':<11} {'week':>5} {'level':>7} {'bars':>5}")
    for r in results:
        print(f"{r.region:<14} {r.pathogen:<11} {r.week:>5} {r.relative_level:>7.2f} {r.bar_count:>5}")
