"""KDCA 표본감시 (4급) CSV 파서 — dportal.kdca.go.kr 차트 데이터 export 형식.

대상: `pipeline/data/kdca/인플루엔자 선택됨.csv` 같은 dportal 차트 다운로드 산출물.
- 절기당 1행: `[절기명], [주1 ILI], [주2 ILI], ..., [주N ILI], [집계 중]`
- 인코딩: EUC-KR (Windows 한글)
- KDCA 절기 정의: 매년 W36 ~ 다음년 W35 (39주, 진행 절기는 누적 주차)

이 파서가 만드는 라벨:
- ILI(인플루엔자 의사환자분율, per 1000 외래환자) ≥ 임계 → 유행(=양성 라벨, 1)
- 미만 → 미유행(=음성, 0)
- 기본 임계 5.8/1000 = KDCA 2024-2025절기 유행 임계 (절기마다 갱신)

backtest 외부 ground truth 로 사용:
- 기존 `analysis/backtest_xgboost_multipath.py` 의 self-target proxy 라벨을 대체
- per-region 분리는 본 데이터셋에 없음 (전국 단일) — 17 region broadcast 정책 따름

한계 (정직):
- 1 절기당 1 파일 — 다년 backtest 위해 절기별 다운로드 필요
- 진행 중인 절기는 끝 컬럼이 `집계 중` 문자열 → 파싱시 제외
"""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

# KDCA 인플루엔자 유행 임계 — 2024-2025절기 기준 (매 절기 5월 발표)
# 갱신 출처: https://www.kdca.go.kr/contents.es?mid=a20301050000
ILI_EPIDEMIC_THRESHOLD = 5.8

# 절기 시작 주차 (ISO week) — KDCA 정의: 매년 36주차 (대략 9월 첫째 주)
SEASON_START_WEEK = 36

# 절기 종료 토큰 (집계중 행 식별)
INCOMPLETE_TOKEN = "집계 중"


@dataclass(frozen=True)
class IliRecord:
    """주별 ILI 측정값 한 줄."""

    season: str          # 예: "2025-2026절기"
    season_year: int     # 예: 2025 (절기 시작 연도)
    week_no: int         # 1~39 (절기 내 누적 주 번호)
    iso_year: int        # 예: 2025 또는 2026 (W36-W52 는 시작연도, W1-W35 는 종료연도)
    iso_week: int        # 1-53 (ISO 주차)
    period_start: date   # 해당 ISO 주의 월요일
    ili_per_1000: float  # 의사환자분율


def _read_csv_euckr(path: Path) -> list[list[str]]:
    """EUC-KR 인코딩 CSV 를 raw 행 리스트로 읽기.

    dportal 차트 export 는 UTF-8 BOM 없이 EUC-KR. UTF-8 로 읽으면 한글 깨짐.
    """
    with path.open("r", encoding="euc-kr", newline="") as f:
        reader = csv.reader(f)
        return [row for row in reader if row]


def _season_year_from_name(season_name: str) -> int:
    """`2025-2026절기` → 2025 (시작 연도). 형식 깨지면 ValueError.

    가드: 단순 `2023` (절기 표시 없음) 같은 형태는 거부 — 기생충/풍토병 등 다른 차트 데이터
    파일이 ILI 파서로 잘못 흘러들어가는 사고 방지.
    """
    if "절기" not in season_name:
        raise ValueError(f"절기명 형식 아님 (절기 토큰 없음): {season_name!r}")
    head = season_name.split("-", 1)[0].strip()
    return int(head)


def _iso_week_for_season_offset(season_start_year: int, offset: int) -> tuple[int, int, date]:
    """절기 시작 주(W36 of start year)부터 offset 주 뒤의 (iso_year, iso_week, monday) 반환.

    Args:
        season_start_year: 절기 시작 연도 (예: 2025)
        offset: 0 = 시작주(W36), 1 = 다음주, ...
    """
    # 시작주 월요일: ISO calendar 의 (year, week, day=1)
    monday = date.fromisocalendar(season_start_year, SEASON_START_WEEK, 1) + timedelta(weeks=offset)
    iso_year, iso_week, _ = monday.isocalendar()
    return iso_year, iso_week, monday


def parse_ili_csv(path: str | Path) -> list[IliRecord]:
    """dportal 인플루엔자 표본감시 차트 export CSV 파싱.

    예상 입력 한 행:
        2025-2026절기, 6.6, 6.7, 8.0, ..., 5.8, 4.3, 4.4, 집계 중

    Returns:
        주별 IliRecord 리스트. 빈 입력/형식 오류 시 빈 리스트 + WARNING 로그.
    """
    path = Path(path)
    if not path.exists():
        logger.warning("KDCA sentinel CSV 없음: %s", path)
        return []

    rows = _read_csv_euckr(path)
    if not rows:
        return []

    records: list[IliRecord] = []
    for row in rows:
        if not row or not row[0].strip():
            continue
        season = row[0].strip()
        try:
            sy = _season_year_from_name(season)
        except ValueError:
            logger.warning("절기명 파싱 실패: %r — skip", season)
            continue

        for idx, raw in enumerate(row[1:]):
            cell = raw.strip()
            if not cell or cell == INCOMPLETE_TOKEN:
                # 진행 중 절기의 미집계 주 — skip (silent fail 아님: 명시적 토큰)
                continue
            try:
                ili = float(cell)
            except ValueError:
                # 빈 셀이나 비숫자(트레일링 ',' 등) — skip
                continue
            iso_year, iso_week, monday = _iso_week_for_season_offset(sy, idx)
            records.append(
                IliRecord(
                    season=season, season_year=sy,
                    week_no=idx + 1,
                    iso_year=iso_year, iso_week=iso_week,
                    period_start=monday, ili_per_1000=ili,
                )
            )

    logger.info("ILI 파싱 성공: %d 주차 (파일=%s)", len(records), path.name)
    return records


def to_epidemic_label(
    records: list[IliRecord],
    threshold: float = ILI_EPIDEMIC_THRESHOLD,
) -> list[dict[str, object]]:
    """IliRecord → backtest 용 라벨 dict.

    Returns:
        [{period_start, iso_year, iso_week, ili, label, source}, ...]
        label = 1 if ili >= threshold else 0
    """
    out: list[dict[str, object]] = []
    for r in records:
        out.append({
            "period_start": r.period_start.isoformat(),
            "iso_year": r.iso_year,
            "iso_week": r.iso_week,
            "ili_per_1000": r.ili_per_1000,
            "label": 1 if r.ili_per_1000 >= threshold else 0,
            "source": "KDCA_SENTINEL_ILI",
            "disease": "influenza",
        })
    return out


def parse_all_seasons(data_dir: str | Path, glob: str = "인플루엔자*.csv") -> list[IliRecord]:
    """`pipeline/data/kdca/` 의 절기별 CSV 여러 개를 한 번에 파싱 (B 안의 다년 라벨용)."""
    data_dir = Path(data_dir)
    if not data_dir.exists():
        logger.warning("디렉토리 없음: %s", data_dir)
        return []

    files = sorted(data_dir.glob(glob))
    aggregated: list[IliRecord] = []
    for f in files:
        aggregated.extend(parse_ili_csv(f))
    # 같은 (iso_year, iso_week) 중복 시 마지막 파일 우선 (덮어쓰기)
    seen: dict[tuple[int, int], IliRecord] = {}
    for r in aggregated:
        seen[(r.iso_year, r.iso_week)] = r
    return sorted(seen.values(), key=lambda r: r.period_start)


# ─────────────────────── CLI (smoke test) ─────────────────────────────────
def main() -> None:
    import argparse

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    p = argparse.ArgumentParser(description="KDCA 인플루엔자 표본감시 CSV → 라벨")
    p.add_argument("--data-dir", default="pipeline/data/kdca",
                   help="절기별 CSV 디렉토리")
    p.add_argument("--threshold", type=float, default=ILI_EPIDEMIC_THRESHOLD,
                   help="유행 임계 (per 1000)")
    p.add_argument("--single", help="단일 파일 경로 (디렉토리 무시)")
    args = p.parse_args()

    if args.single:
        recs = parse_ili_csv(args.single)
    else:
        recs = parse_all_seasons(args.data_dir)

    labels = to_epidemic_label(recs, threshold=args.threshold)
    pos = sum(1 for row in labels if row["label"] == 1)
    logger.info("총 %d 주차 — 양성 %d (%.1f%%)", len(labels), pos,
                100 * pos / max(1, len(labels)))
    for row in labels[:5]:
        logger.info("  sample: %s", row)


if __name__ == "__main__":
    main()
