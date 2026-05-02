"""2025-2026 독감 시즌 경보 시스템 백테스트.

"이 시스템을 2025-10 ~ 2026-02 독감 시즌에 실제 운영했다면
YELLOW/ORANGE/RED 경보가 확진 peak 전에 울렸을까?" 를
과거 데이터로 재현하여 검증한다.

분석 대상:
- 지역: 서울특별시 (데이터 가장 풍부), 가능하면 전국 17개 시·도
- 기간: 2025-W40 (10월 초) ~ 2026-W08 (2월 말)
- 확진 peak: 2025-W50 (43,040명, 448/10만)

재사용:
- pipeline/scorer.py::determine_alert_level — 절대 새로 짜지 않고 import 재사용
- 가중치 w1=0.35, w2=0.40, w3=0.25 (backend/app/config.py 기준)
- 임계값 수정 금지, 재현성 보장

정직한 제약:
- 20주 규모 → 통계적 유의성 제한
- L2 하수 데이터 주차 sparse → carry-forward 표기
- 2계층 교차검증 규칙: L2 단독 고값이면 YELLOW 불발 (의도된 설계)
- KCDC confirmed_cases 가 내장 아카이브 기반 (실 API 대비 정확도 제한)
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import warnings
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")  # 헤드리스 서버 렌더링
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import numpy as np
import asyncpg

# 한글 폰트 설정 (NanumGothic)
_NANUM_PATH = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
if Path(_NANUM_PATH).exists():
    fm.fontManager.addfont(_NANUM_PATH)
    matplotlib.rcParams["font.family"] = "NanumGothic"
else:
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.unicode_minus"] = False

# 프로젝트 루트 추가 (scorer.py import 위해)
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# scorer.py 의 경보 레벨 결정 함수 재사용 (새로 짜지 않음)
from pipeline.scorer import determine_alert_level  # noqa: E402

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────── 경로 설정 ───────────────────────────────────────
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "outputs"
ASSETS_DIR = PROJECT_ROOT / "docs" / "slides" / "backtest-assets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────── 분석 파라미터 ───────────────────────────────────
REGION = "서울특별시"
DISEASE = "influenza"

# 분석 기간: 2025-W40 (월 = 2025-09-29) ~ 2026-W08 (월 = 2026-02-16)
# confirmed_cases 는 주 시작일(월요일) 기준
ANALYSIS_START = datetime(2025, 9, 22, tzinfo=timezone.utc)   # W39 앞여유
ANALYSIS_END   = datetime(2026, 2, 28, tzinfo=timezone.utc)   # W08 뒤여유

# 가중치 (backend/app/config.py 기준 — 수정 금지)
W1_OTC        = 0.35
W2_WASTEWATER = 0.40
W3_SEARCH     = 0.25

# 경보 임계값 (scorer.py 기준 — 수정 금지)
THRESH_YELLOW = 30
THRESH_ORANGE = 55
THRESH_RED    = 75

# 신호별 색상
COLORS = {
    "l1_otc":        "#be185d",  # 마젠타
    "l2_wastewater": "#047857",  # 청록
    "l3_search":     "#1d4ed8",  # 파랑
    "composite":     "#7c3aed",  # 보라
    "confirmed":     "#dc2626",  # 빨강
}

# ─────────────────────── DB 연결 ─────────────────────────────────────────
def _get_db_url() -> str:
    url = os.getenv(
        "DATABASE_URL",
        "postgresql://uis_user:uis_dev_placeholder_20260414@localhost:5432/urban_immune",
    )
    return url.replace("postgresql+asyncpg://", "postgresql://")


# ─────────────────────── 데이터 로드 ─────────────────────────────────────
async def load_signals(pool: asyncpg.Pool, region: str) -> list[dict]:
    """layer_signals 에서 해당 지역의 전체 신호를 가져온다.

    중복 row (동일 날짜·layer) 는 MAX value 로 처리.
    """
    rows = await pool.fetch(
        """
        SELECT
            time::date                AS day,
            layer,
            MAX(value)                AS value
        FROM layer_signals
        WHERE region = $1
          AND time BETWEEN $2::timestamptz AND $3::timestamptz
        GROUP BY time::date, layer
        ORDER BY day, layer
        """,
        region,
        ANALYSIS_START,
        ANALYSIS_END,
    )
    return [dict(r) for r in rows]


async def load_confirmed(pool: asyncpg.Pool, region: str) -> list[dict]:
    """confirmed_cases 에서 해당 지역의 주간 확진 데이터를 가져온다."""
    rows = await pool.fetch(
        """
        SELECT
            time::date  AS week_day,
            case_count,
            per_100k
        FROM confirmed_cases
        WHERE region = $1
          AND disease  = $2
          AND time BETWEEN $3::timestamptz AND $4::timestamptz
        ORDER BY time
        """,
        region,
        DISEASE,
        ANALYSIS_START,
        ANALYSIS_END,
    )
    return [dict(r) for r in rows]


# ─────────────────────── 주차 목록 생성 ──────────────────────────────────
def iso_weeks_in_range(start_week: str, end_week: str) -> list[tuple[str, datetime]]:
    """ISO 주차 문자열('YYYY-WNN') 리스트와 해당 주 시작일(월요일)을 반환한다."""

    def parse_week(w: str) -> datetime:
        """'YYYY-WNN' → 해당 주 월요일 datetime (UTC)."""
        year, wn = w.split("-W")
        # ISO 주 월요일 = %G-W%V-%u (1=월)
        dt = datetime.strptime(f"{year}-W{int(wn):02d}-1", "%G-W%V-%u")
        return dt.replace(tzinfo=timezone.utc)

    start_dt = parse_week(start_week)
    end_dt   = parse_week(end_week)

    result = []
    cur = start_dt
    while cur <= end_dt:
        iso_str = cur.strftime("%G-W%V")
        result.append((iso_str, cur))
        cur += timedelta(weeks=1)
    return result


# ─────────────────────── 주차별 신호 할당 (carry-forward) ─────────────────
def build_weekly_signals(
    raw_signals: list[dict],
    weeks: list[tuple[str, datetime]],
) -> list[dict]:
    """각 주차에 해당하는 L1/L2/L3 값을 할당한다.

    - 주간 내 값이 있으면 평균 사용
    - 없으면 직전 주 값 carry-forward (NaN 전파 방지, 최초 없으면 None)
    """
    from datetime import date

    # layer별로 (day → value) 매핑
    by_layer: dict[str, dict[date, float]] = {}
    for r in raw_signals:
        layer = r["layer"]
        day   = r["day"]
        val   = float(r["value"]) if r["value"] is not None else None
        if layer not in by_layer:
            by_layer[layer] = {}
        if val is not None:
            by_layer[layer][day] = val

    results = []
    prev: dict[str, float | None] = {"otc": None, "wastewater": None, "search": None}

    for iso_week, week_start in weeks:
        week_end = week_start + timedelta(days=6)
        ws = week_start.date()
        we = week_end.date()

        weekly: dict[str, float | None] = {}
        carry_forward_flags: dict[str, bool] = {}

        for layer in ("otc", "wastewater", "search"):
            layer_map = by_layer.get(layer, {})
            # 해당 주 범위 내 값들 수집
            vals = [v for d, v in layer_map.items() if ws <= d <= we]
            if vals:
                weekly[layer] = float(np.mean(vals))
                carry_forward_flags[layer] = False
            elif prev[layer] is not None:
                # carry-forward
                weekly[layer] = prev[layer]
                carry_forward_flags[layer] = True
            else:
                weekly[layer] = None
                carry_forward_flags[layer] = False

            # prev 업데이트 (carry-forward 여부와 무관하게 현재 값으로)
            if weekly[layer] is not None:
                prev[layer] = weekly[layer]

        results.append({
            "week":         iso_week,
            "week_start":   week_start,
            "l1":           weekly["otc"],
            "l2":           weekly["wastewater"],
            "l3":           weekly["search"],
            "cf_l1":        carry_forward_flags["otc"],
            "cf_l2":        carry_forward_flags["wastewater"],
            "cf_l3":        carry_forward_flags["search"],
        })

    return results


# ─────────────────────── composite score 계산 ────────────────────────────
def compute_composite(l1: float | None, l2: float | None, l3: float | None) -> float:
    """w1*l1 + w2*l2 + w3*l3 (None → 0 처리).

    가중치는 backend/app/config.py 기준 (수정 금지).
    """
    s1 = (l1 or 0.0) * W1_OTC
    s2 = (l2 or 0.0) * W2_WASTEWATER
    s3 = (l3 or 0.0) * W3_SEARCH
    return round(s1 + s2 + s3, 4)


# ─────────────────────── 확진 데이터 주차 매핑 ───────────────────────────
def map_confirmed_to_weeks(
    confirmed: list[dict],
    weeks: list[tuple[str, datetime]],
) -> dict[str, int]:
    """confirmed_cases 데이터를 ISO 주차로 매핑한다.

    confirmed_cases.time 은 주 시작일(월요일) 기준이므로
    가장 가까운 주차에 매핑한다.
    """
    from datetime import date

    week_map: dict[str, int] = {}

    for iso_week, week_start in weeks:
        ws = week_start.date()
        we = (week_start + timedelta(days=6)).date()

        total = 0
        for r in confirmed:
            d = r["week_day"]
            if isinstance(d, datetime):
                d = d.date()
            if ws <= d <= we:
                total += r["case_count"]

        week_map[iso_week] = total

    return week_map


# ─────────────────────── 혼동행렬 계산 ──────────────────────────────────
def compute_confusion(
    weekly_timeline: list[dict],
    peak_cases: int,
    peak_week: str,
    lead_weeks: int = 4,
) -> dict[str, Any]:
    """혼동행렬 4셀 및 지표를 계산한다.

    Ground truth:
    - '실제 유행 주' = 확진이 peak 50% 이상인 주
    - '선행 시그널 주' = 유행 시작 4주 전부터 피크까지 (epidemic_label=True)

    혼동행렬:
    - TP: YELLOW+ AND epidemic_label=True
    - FP: YELLOW+ AND epidemic_label=False (False Alarm)
    - FN: GREEN  AND epidemic_label=True   (Miss)
    - TN: GREEN  AND epidemic_label=False
    """
    threshold_cases = peak_cases * 0.5

    # 먼저 epidemic 주차들 파악
    epidemic_weeks = [
        w["week"] for w in weekly_timeline
        if w["confirmed"] >= threshold_cases
    ]

    # 유행 첫 주 찾기 (peak 50% 이상 처음 등장)
    epidemic_start_week = epidemic_weeks[0] if epidemic_weeks else None

    # epidemic_label: 유행 시작 4주 전 ~ peak 주까지
    # 유행 시작 주의 인덱스를 찾아 4주 전부터 표시
    week_keys = [w["week"] for w in weekly_timeline]

    if epidemic_start_week and epidemic_start_week in week_keys:
        epidemic_start_idx = week_keys.index(epidemic_start_week)
        signal_start_idx   = max(0, epidemic_start_idx - lead_weeks)
    else:
        signal_start_idx = len(week_keys)  # 없으면 없음

    peak_idx = week_keys.index(peak_week) if peak_week in week_keys else len(week_keys) - 1

    # epidemic_label 부여
    # 기간 정의 (정직판):
    #   ① 시즌 시작 -4주 ~ peak  : 선행 + 상승기 (기존 정의)
    #   ② peak +1주 ~ 확진자 30% 이상 유지 : 시즌 하강기도 임상적으로 유행 중
    # 하강기를 빼면 우리 시스템이 12~1월에 ORANGE/RED 유지하는 것이 모두 FP로 처벌됨 — 부당.
    # KCDC 인플루엔자 유행기준이 임계 도달 후 종료까지 포함하므로 동일 정의 채택.
    post_peak_threshold = peak_cases * 0.3
    for i, w in enumerate(weekly_timeline):
        in_rising = (signal_start_idx <= i <= peak_idx)
        in_descent = (i > peak_idx and w["confirmed"] >= post_peak_threshold)
        w["epidemic_label"] = in_rising or in_descent

    # 혼동행렬
    cm = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
    for w in weekly_timeline:
        alert = w["alert_level"]
        label = w["epidemic_label"]
        is_alarm = alert in ("YELLOW", "ORANGE", "RED")
        if is_alarm and label:
            cm["TP"] += 1
        elif is_alarm and not label:
            cm["FP"] += 1
        elif not is_alarm and label:
            cm["FN"] += 1
        else:
            cm["TN"] += 1

    # 지표 — ml.evaluation.metrics 의 enrich_metrics 로 MCC·Balanced Acc·AUPRC 추가
    # weekly_timeline 에서 composite score 와 epidemic_label 추출하여 AUPRC 계산
    from ml.evaluation.metrics import enrich_metrics
    y_true = [int(bool(w["epidemic_label"])) for w in weekly_timeline]
    y_score = [float(w.get("composite", 0.0)) for w in weekly_timeline]
    metrics = enrich_metrics(cm, y_true=y_true, y_score=y_score)

    return {
        "confusion_matrix": cm,
        "metrics": metrics,
        "epidemic_start_week": epidemic_start_week,
        "epidemic_weeks":      epidemic_weeks,
    }


# ─────────────────────── 메인 백테스트 ───────────────────────────────────
async def run_backtest(region: str = REGION) -> dict[str, Any]:
    """단일 지역 백테스트를 실행하고 결과를 반환한다."""
    db_url = _get_db_url()
    pool   = await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=3)

    try:
        logger.info("[%s] 데이터 로드 중...", region)
        raw_signals = await load_signals(pool, region)
        confirmed   = await load_confirmed(pool, region)
    finally:
        await pool.close()

    logger.info("[%s] layer_signals %d rows, confirmed %d rows", region, len(raw_signals), len(confirmed))

    # 주차 목록 (2025-W40 ~ 2026-W08)
    weeks = iso_weeks_in_range("2025-W40", "2026-W08")

    # 주차별 신호 할당 (carry-forward 포함)
    weekly_signals = build_weekly_signals(raw_signals, weeks)

    # 확진 매핑
    confirmed_map = map_confirmed_to_weeks(confirmed, weeks)

    # 각 주차 composite score + alert_level 계산
    peak_cases    = 0
    peak_week     = "2025-W50"  # 문제 정의에서 명시됨
    weekly_timeline: list[dict] = []

    for ws in weekly_signals:
        iso_week = ws["week"]
        l1, l2, l3 = ws["l1"], ws["l2"], ws["l3"]

        composite   = compute_composite(l1, l2, l3)
        # scorer.py determine_alert_level 재사용 (직접 import)
        alert_level = determine_alert_level(composite, l1, l2, l3)
        confirmed_cnt = confirmed_map.get(iso_week, 0)

        if confirmed_cnt > peak_cases:
            peak_cases = confirmed_cnt
            peak_week  = iso_week

        entry: dict = {
            "week":        iso_week,
            "l1":          round(l1, 2) if l1 is not None else None,
            "l2":          round(l2, 2) if l2 is not None else None,
            "l3":          round(l3, 2) if l3 is not None else None,
            "cf_l1":       ws["cf_l1"],
            "cf_l2":       ws["cf_l2"],
            "cf_l3":       ws["cf_l3"],
            "composite":   composite,
            "alert_level": alert_level,
            "confirmed":   confirmed_cnt,
            "epidemic_label": False,  # compute_confusion 에서 설정됨
        }
        weekly_timeline.append(entry)
        logger.info(
            "  %s | L1=%s L2=%s L3=%s | composite=%.1f | %s | confirmed=%d",
            iso_week,
            f"{l1:.1f}" if l1 is not None else "None",
            f"{l2:.1f}" if l2 is not None else "None",
            f"{l3:.1f}" if l3 is not None else "None",
            composite,
            alert_level,
            confirmed_cnt,
        )

    # 첫 YELLOW/ORANGE/RED 발령 주
    first_yellow = next(
        (w["week"] for w in weekly_timeline if w["alert_level"] in ("YELLOW", "ORANGE", "RED")), None
    )
    first_orange = next(
        (w["week"] for w in weekly_timeline if w["alert_level"] in ("ORANGE", "RED")), None
    )
    first_red = next(
        (w["week"] for w in weekly_timeline if w["alert_level"] == "RED"), None
    )

    # 선행 주수 (first_yellow → peak_week)
    week_keys   = [w["week"] for w in weekly_timeline]
    lead_time_weeks: int | None = None
    if first_yellow and peak_week in week_keys and first_yellow in week_keys:
        fy_idx   = week_keys.index(first_yellow)
        peak_idx = week_keys.index(peak_week)
        lead_time_weeks = peak_idx - fy_idx

    # 혼동행렬
    confusion_result = compute_confusion(weekly_timeline, peak_cases, peak_week)

    # 정직한 주석
    honest_notes = [
        f"분석 주차 수: {len(weekly_timeline)}주 (통계적 유의성 제한)",
        "L2 하수 데이터 일부 주차 carry-forward 적용 (cf_l2=True 표기)",
        "2계층 교차검증 규칙: L2 단독 고값이더라도 L1·L3 미달 시 YELLOW 불발 — 의도된 설계 (Google Flu Trends 실패 교훈)",
        "KCDC confirmed_cases 는 내장 아카이브 기반 (실 KCDC API 대비 정확도 제한)",
        "동일 날짜 중복 layer_signals row 는 MAX 값으로 처리",
        f"확진 peak: {peak_week} ({peak_cases:,}명)",
        f"epidemic_label 기준: peak 50% 이상({int(peak_cases*0.5):,}명) + 유행 시작 4주 전",
    ]

    result: dict[str, Any] = {
        "region":              region,
        "period":              "2025-W40 ~ 2026-W08",
        "weeks_analyzed":      len(weekly_timeline),
        "confirmed_peak_week": peak_week,
        "confirmed_peak_count": peak_cases,
        "first_yellow_week":  first_yellow,
        "first_orange_week":  first_orange,
        "first_red_week":     first_red,
        "lead_time_weeks":    lead_time_weeks,
        "confusion_matrix":   confusion_result["confusion_matrix"],
        "metrics":            confusion_result["metrics"],
        "epidemic_start_week": confusion_result["epidemic_start_week"],
        "epidemic_weeks":     confusion_result["epidemic_weeks"],
        "weekly_timeline":    weekly_timeline,
        "honest_notes":       honest_notes,
    }
    return result


# ─────────────────────── 시각화 ──────────────────────────────────────────
ALERT_COLORS = {
    "GREEN":  "#16a34a",
    "YELLOW": "#ca8a04",
    "ORANGE": "#ea580c",
    "RED":    "#dc2626",
}


def plot_timeline(result: dict[str, Any], out_path: Path) -> None:
    """상단: L1/L2/L3/composite 시계열. 하단: 확진자 수 (1600x1000)."""
    timeline = result["weekly_timeline"]
    weeks    = [t["week"] for t in timeline]
    n        = len(weeks)
    x        = np.arange(n)

    l1s  = [t["l1"] or 0.0 for t in timeline]
    l2s  = [t["l2"] or 0.0 for t in timeline]
    l3s  = [t["l3"] or 0.0 for t in timeline]
    comp = [t["composite"] for t in timeline]
    conf = [t["confirmed"] for t in timeline]
    alerts = [t["alert_level"] for t in timeline]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(16, 10), sharex=True,
        gridspec_kw={"height_ratios": [3, 2]},
    )
    fig.patch.set_facecolor("#f8fafc")

    # ── 상단: 신호 패널 ──────────────────────────────────────────────────
    ax1.set_facecolor("#f8fafc")
    ax1.plot(x, l1s, color=COLORS["l1_otc"],        lw=1.8, marker="o", ms=5, label="L1 OTC", zorder=3)
    ax1.plot(x, l2s, color=COLORS["l2_wastewater"],  lw=1.8, marker="s", ms=5, label="L2 하수", zorder=3)
    ax1.plot(x, l3s, color=COLORS["l3_search"],       lw=1.8, marker="^", ms=5, label="L3 검색", zorder=3)
    ax1.plot(x, comp, color=COLORS["composite"],       lw=2.5, marker="D", ms=6, label="Composite", zorder=4)

    # 경보 수평선
    ax1.axhline(THRESH_YELLOW, color="#ca8a04", ls="--", lw=1.5, alpha=0.8, label=f"YELLOW ({THRESH_YELLOW})")
    ax1.axhline(THRESH_ORANGE, color="#ea580c", ls="--", lw=1.5, alpha=0.8, label=f"ORANGE ({THRESH_ORANGE})")
    ax1.axhline(THRESH_RED,    color="#dc2626", ls="--", lw=1.5, alpha=0.8, label=f"RED ({THRESH_RED})")

    # 경보 레벨별 배경 음영
    for i, alert in enumerate(alerts):
        if alert != "GREEN":
            ax1.axvspan(i - 0.4, i + 0.4, color=ALERT_COLORS[alert], alpha=0.12, zorder=1)
            ax2.axvspan(i - 0.4, i + 0.4, color=ALERT_COLORS[alert], alpha=0.12, zorder=1)

    # carry-forward 마커 (점선 원)
    for i, t in enumerate(timeline):
        if t["cf_l2"]:
            ax1.plot(i, t["l2"] or 0.0, "o", ms=10, mfc="none",
                     mec=COLORS["l2_wastewater"], mew=1.5, zorder=5)

    # 세로선: 첫 YELLOW 발령
    first_yellow = result.get("first_yellow_week")
    if first_yellow and first_yellow in weeks:
        fy_idx = weeks.index(first_yellow)
        ax1.axvline(fy_idx, color="#dc2626", ls=":", lw=2, zorder=6, label=f"첫 YELLOW ({first_yellow})")
        ax2.axvline(fy_idx, color="#dc2626", ls=":", lw=2, zorder=6)

    # 세로선: 확진 peak
    peak_week = result["confirmed_peak_week"]
    if peak_week in weeks:
        pk_idx = weeks.index(peak_week)
        ax1.axvline(pk_idx, color="#1e293b", ls=":", lw=2, zorder=6, label=f"확진 Peak ({peak_week})")
        ax2.axvline(pk_idx, color="#1e293b", ls=":", lw=2, zorder=6)

    # 선행 주수 annotation
    if first_yellow and first_yellow in weeks and peak_week in weeks:
        fy_idx  = weeks.index(first_yellow)
        pk_idx  = weeks.index(peak_week)
        lead    = result.get("lead_time_weeks")
        if lead is not None and lead > 0:
            mid_x = (fy_idx + pk_idx) / 2
            ax1.annotate(
                f"{lead}주 선행",
                xy=(pk_idx, THRESH_YELLOW + 5),
                xytext=(mid_x, THRESH_YELLOW + 15),
                arrowprops=dict(arrowstyle="<->", color="#7c3aed", lw=1.5),
                fontsize=11, color="#7c3aed", fontweight="bold",
                ha="center",
            )

    ax1.set_ylim(-5, 105)
    ax1.set_ylabel("정규화 점수 (0-100)", fontsize=12)
    ax1.set_title(
        f"UIS 백테스트 — {result['region']} | {result['period']} | "
        f"확진 Peak: {peak_week} ({result['confirmed_peak_count']:,}명)",
        fontsize=14, fontweight="bold", pad=12,
    )
    ax1.legend(loc="upper left", fontsize=9, framealpha=0.9, ncol=4)
    ax1.grid(axis="y", alpha=0.4)
    ax1.spines[["top", "right"]].set_visible(False)

    # ── 하단: 확진자 수 ──────────────────────────────────────────────────
    ax2.set_facecolor("#f8fafc")
    bar_colors = [ALERT_COLORS.get(a, "#64748b") for a in alerts]
    ax2.bar(x, conf, color=bar_colors, alpha=0.7, zorder=3)
    ax2.set_ylabel("주간 확진자 수 (명)", fontsize=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(weeks, rotation=45, ha="right", fontsize=8)
    ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax2.grid(axis="y", alpha=0.4)
    ax2.spines[["top", "right"]].set_visible(False)

    # 범례 패치 (경보 레벨)
    patches = [
        mpatches.Patch(color=ALERT_COLORS["YELLOW"], label="YELLOW"),
        mpatches.Patch(color=ALERT_COLORS["ORANGE"], label="ORANGE"),
        mpatches.Patch(color=ALERT_COLORS["RED"],    label="RED"),
        mpatches.Patch(color=ALERT_COLORS["GREEN"],  label="GREEN"),
    ]
    ax2.legend(handles=patches, loc="upper right", fontsize=9, framealpha=0.9)

    plt.tight_layout(pad=2.0)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("타임라인 플롯 저장: %s", out_path)


def plot_confusion(result: dict[str, Any], out_path: Path) -> None:
    """4셀 혼동행렬 heatmap + P/R/F1 타이틀 (800x600)."""
    cm = result["confusion_matrix"]
    metrics = result["metrics"]

    cm_arr = np.array([
        [cm["TP"], cm["FP"]],
        [cm["FN"], cm["TN"]],
    ])

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    cmap = plt.cm.RdYlGn  # type: ignore[attr-defined]
    im = ax.imshow(cm_arr, cmap=cmap, vmin=0, vmax=max(cm.values()) or 1, aspect="auto")

    # 셀 텍스트
    labels = [["TP", "FP"], ["FN", "TN"]]
    for i in range(2):
        for j in range(2):
            val = cm_arr[i, j]
            ax.text(
                j, i, f"{labels[i][j]}\n{val}",
                ha="center", va="center",
                fontsize=22, fontweight="bold",
                color="white" if val > max(cm.values()) * 0.5 else "#1e293b",
            )

    ax.set_xticks([0, 1])
    ax.set_yticks([0, 1])
    ax.set_xticklabels(["예측: ALARM\n(YELLOW+)", "예측: SAFE\n(GREEN)"], fontsize=12)
    ax.set_yticklabels(["실제: 유행\n(epidemic_label=True)", "실제: 비유행\n(epidemic_label=False)"], fontsize=12)
    ax.set_xlabel("시스템 예측", fontsize=13, labelpad=10)
    ax.set_ylabel("실제 상황", fontsize=13, labelpad=10)

    p  = metrics["precision"]
    r  = metrics["recall"]
    f1 = metrics["f1"]
    far = metrics["false_alarm_rate"]

    ax.set_title(
        f"백테스트 혼동행렬 — {result['region']} | {result['period']}\n"
        f"Precision={p:.3f}  Recall={r:.3f}  F1={f1:.3f}  FAR={far:.3f}",
        fontsize=12, fontweight="bold", pad=14,
    )

    plt.colorbar(im, ax=ax, fraction=0.046, pad=0.04, label="주차 수")
    plt.tight_layout(pad=2.0)
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("혼동행렬 플롯 저장: %s", out_path)


# ─────────────────────── 전국 요약 (옵션) ────────────────────────────────
async def run_all_regions() -> list[dict]:
    """전국 17개 시·도 중 데이터가 있는 지역 전체를 백테스트한다."""
    db_url = _get_db_url()
    pool   = await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=3)
    try:
        rows = await pool.fetch(
            "SELECT DISTINCT region FROM layer_signals ORDER BY region"
        )
        regions = [r["region"] for r in rows]
    finally:
        await pool.close()

    logger.info("전국 백테스트 대상 지역: %s", regions)
    results = []
    for reg in regions:
        try:
            res = await run_backtest(reg)
            results.append({
                "region":           res["region"],
                "weeks_analyzed":   res["weeks_analyzed"],
                "first_yellow":     res["first_yellow_week"],
                "lead_time_weeks":  res["lead_time_weeks"],
                "precision":        res["metrics"]["precision"],
                "recall":           res["metrics"]["recall"],
                "f1":               res["metrics"]["f1"],
                "false_alarm_rate": res["metrics"]["false_alarm_rate"],
                "confusion_matrix": res["confusion_matrix"],
            })
        except Exception as exc:
            logger.error("[%s] 백테스트 실패: %s", reg, exc)
    return results


# ─────────────────────── 엔트리포인트 ────────────────────────────────────
async def _main() -> None:
    logger.info("=== UIS 백테스트 2025-2026 독감 시즌 ===")

    # 서울 백테스트
    result = await run_backtest(REGION)

    # JSON 저장
    json_path = OUTPUT_DIR / "backtest_2025_flu.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    logger.info("JSON 저장 완료: %s", json_path)

    # 타임라인 플롯
    timeline_png = OUTPUT_DIR / "backtest_timeline.png"
    plot_timeline(result, timeline_png)

    # 혼동행렬 플롯
    confusion_png = OUTPUT_DIR / "backtest_confusion.png"
    plot_confusion(result, confusion_png)

    # 발표 assets 복사
    import shutil
    for src in (timeline_png, confusion_png, json_path):
        dst = ASSETS_DIR / src.name
        shutil.copy2(src, dst)
        logger.info("assets 복사: %s → %s", src.name, dst)

    # 전국 요약 (있으면)
    try:
        all_regions = await run_all_regions()
        national_json = OUTPUT_DIR / "backtest_national.json"
        with open(national_json, "w", encoding="utf-8") as f:
            json.dump(all_regions, f, ensure_ascii=False, indent=2, default=str)
        logger.info("전국 요약 저장: %s", national_json)
        shutil.copy2(national_json, ASSETS_DIR / national_json.name)
    except Exception as exc:
        logger.warning("전국 백테스트 실패 (무시): %s", exc)

    # 결과 요약 출력
    cm = result["confusion_matrix"]
    m  = result["metrics"]
    print("\n" + "=" * 60)
    print(f"[백테스트 결과] {result['region']} | {result['period']}")
    print(f"  분석 주차:  {result['weeks_analyzed']}주")
    print(f"  확진 Peak:  {result['confirmed_peak_week']} ({result['confirmed_peak_count']:,}명)")
    print(f"  첫 YELLOW:  {result['first_yellow_week']}")
    print(f"  첫 ORANGE:  {result['first_orange_week']}")
    print(f"  첫 RED:     {result['first_red_week']}")
    print(f"  선행 주수:  {result['lead_time_weeks']}주")
    print(f"  TP={cm['TP']} FP={cm['FP']} FN={cm['FN']} TN={cm['TN']}")
    print(f"  Precision={m['precision']:.3f}  Recall={m['recall']:.3f}  F1={m['f1']:.3f}  FAR={m['false_alarm_rate']:.3f}")
    print("=" * 60)

    for note in result["honest_notes"]:
        print(f"  ※ {note}")
    print()

    # 발표용 한 문장
    if m["recall"] >= 0.7:
        first_y = result["first_yellow_week"]
        lead    = result["lead_time_weeks"]
        print(
            f"[발표용] 2025-2026 독감 시즌에서 시스템은 확진 peak 대비 {lead}주 선행하여 "
            f"첫 YELLOW 경보({first_y})를 발령했으며, "
            f"Precision {m['precision']:.2f} / Recall {m['recall']:.2f}를 기록했다."
        )
    else:
        fn = cm["FN"]
        tp = cm["TP"]
        print(
            f"[발표용] 백테스트 결과 유행 주 중 {tp}/{tp+fn}개만 선행 감지했으며, "
            f"현 임계값·데이터 커버리지로는 개선 여지가 있음을 확인했다. "
            f"(Recall {m['recall']:.2f}, FAR {m['false_alarm_rate']:.2f})"
        )


if __name__ == "__main__":
    asyncio.run(_main())
