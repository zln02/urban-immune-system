"""17개 시·도 전체 멀티-리전 백테스트.

기존 backtest_2025_flu_multi.py 의 4지역을 17개 시·도 전체로 확장.
게이트 B(2계층 교차검증) 만 적용. 게이트 A(L2 미달 차단)는 sweep 결과 폐기.

산출물:
  analysis/outputs/backtest_17regions.json
  analysis/outputs/backtest_17regions_metrics.png
  analysis/outputs/backtest_17regions_timeline.png

정직한 제약:
  - 확진 ground truth: 17개 지역 모두 confirmed_cases 보유
  - L2(하수) 데이터 일부 지역 carry-forward 적용
  - scorer 가중치·임계값 변경 없음 (L1=0.35, L2=0.40, L3=0.25)
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm
import numpy as np

# ─────────────────────── 한글 폰트 ──────────────────────────────────────────
_NANUM_PATH = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
if Path(_NANUM_PATH).exists():
    fm.fontManager.addfont(_NANUM_PATH)
    matplotlib.rcParams["font.family"] = "NanumGothic"
else:
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.unicode_minus"] = False

# ─────────────────────── 프로젝트 경로 ──────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.backtest_2025_flu import run_backtest  # noqa: E402
from pipeline.scorer import (  # noqa: E402
    _CROSS_VALIDATION_MIN_LAYERS,
    _CROSS_VALIDATION_LAYER_THRESHOLD,
    _RED_THRESHOLD,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────── 17개 시·도 대상 지역 ────────────────────────────────
ALL_17_REGIONS = [
    "서울특별시",
    "경기도",
    "부산광역시",
    "인천광역시",
    "대구광역시",
    "대전광역시",
    "광주광역시",
    "울산광역시",
    "세종특별자치시",
    "강원특별자치도",
    "충청북도",
    "충청남도",
    "전라북도",
    "전라남도",
    "경상북도",
    "경상남도",
    "제주특별자치도",
]

OUTPUT_DIR = PROJECT_ROOT / "analysis" / "outputs"
ASSETS_DIR = PROJECT_ROOT / "docs" / "slides" / "midterm-deck" / "assets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────── 시각화 상수 ────────────────────────────────────────
ALERT_COLORS = {
    "GREEN":  "#16a34a",
    "YELLOW": "#ca8a04",
    "ORANGE": "#ea580c",
    "RED":    "#dc2626",
}

THRESH_YELLOW = 30
THRESH_ORANGE = 55
THRESH_RED    = 75


# ─────────────────────── 게이트 미적용 경보 레벨 계산 (비교용) ────────────────
def _determine_alert_level_no_gate(
    composite: float,
    l1: float | None,
    l2: float | None,
    l3: float | None,
) -> str:
    """게이트 A 없이 게이트 B 만 적용하는 경보 레벨 — 비교 기준선용.

    기존 4지역 백테스트 기준: 2계층 교차검증만 적용 (게이트 A 없음).
    """
    if composite >= 75:
        raw_level = "RED"
    elif composite >= 55:
        raw_level = "ORANGE"
    elif composite >= 30:
        raw_level = "YELLOW"
    else:
        raw_level = "GREEN"

    if raw_level == "GREEN":
        return "GREEN"

    above_threshold = sum(
        1 for v in (l1, l2, l3)
        if v is not None and v >= 30.0
    )
    if above_threshold < 2:
        return "GREEN"

    return raw_level


def _compute_metrics_from_timeline(
    weekly_timeline: list[dict],
    peak_cases: int,
    peak_week: str,
    alert_key: str = "alert_level",
    lead_weeks_for_label: int = 4,
) -> dict:
    """주어진 alert_key 컬럼 기준으로 혼동행렬·메트릭을 계산한다."""
    threshold_cases = peak_cases * 0.5
    epidemic_weeks = [
        w["week"] for w in weekly_timeline
        if w["confirmed"] >= threshold_cases
    ]
    epidemic_start_week = epidemic_weeks[0] if epidemic_weeks else None
    week_keys = [w["week"] for w in weekly_timeline]

    if epidemic_start_week and epidemic_start_week in week_keys:
        epidemic_start_idx = week_keys.index(epidemic_start_week)
        signal_start_idx   = max(0, epidemic_start_idx - lead_weeks_for_label)
    else:
        signal_start_idx = len(week_keys)

    peak_idx = week_keys.index(peak_week) if peak_week in week_keys else len(week_keys) - 1

    cm: dict[str, int] = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
    for i, w in enumerate(weekly_timeline):
        label = signal_start_idx <= i <= peak_idx
        is_alarm = w[alert_key] in ("YELLOW", "ORANGE", "RED")
        if is_alarm and label:
            cm["TP"] += 1
        elif is_alarm and not label:
            cm["FP"] += 1
        elif not is_alarm and label:
            cm["FN"] += 1
        else:
            cm["TN"] += 1

    tp, fp, fn, tn = cm["TP"], cm["FP"], cm["FN"], cm["TN"]
    precision        = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall           = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1               = (2 * precision * recall / (precision + recall)
                        if (precision + recall) > 0 else 0.0)
    false_alarm_rate = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    return {
        "confusion_matrix": cm,
        "metrics": {
            "precision":        round(precision, 4),
            "recall":           round(recall, 4),
            "f1":               round(f1, 4),
            "false_alarm_rate": round(false_alarm_rate, 4),
        },
    }


# ─────────────────────── 17지역 타임라인 플롯 (6행×3열) ─────────────────────
def plot_17regions_timeline(results: dict[str, dict], out_path: Path) -> None:
    """17개 지역 subplot — composite 시계열 + 경보 음영 (5행×4열, 마지막 셀 요약)."""
    n_regions = len(results)
    n_cols = 4
    n_rows = (n_regions + n_cols - 1) // n_cols  # ceil

    fig, axes_grid = plt.subplots(
        n_rows, n_cols,
        figsize=(20, n_rows * 4.5),
        gridspec_kw={"hspace": 0.65, "wspace": 0.4},
    )
    fig.patch.set_facecolor("#f8fafc")
    fig.suptitle(
        "UIS 17개 시·도 백테스트 — composite 시계열 (2025-W40 ~ 2026-W08)\n"
        f"게이트 B (2계층 교차검증): {_CROSS_VALIDATION_MIN_LAYERS}계층이상{_CROSS_VALIDATION_LAYER_THRESHOLD:.0f}+",
        fontsize=13, fontweight="bold", y=0.99,
    )

    axes_flat = axes_grid.flatten()
    region_list = list(results.keys())

    for idx, region in enumerate(region_list):
        ax = axes_flat[idx]
        ax.set_facecolor("#f8fafc")
        result = results[region]

        if result.get("status") == "skipped":
            ax.text(0.5, 0.5, f"{region}\n(데이터 없음)", ha="center", va="center",
                    transform=ax.transAxes, fontsize=10, color="#94a3b8")
            ax.set_xticks([])
            ax.set_yticks([])
            continue

        timeline = result["weekly_timeline"]
        weeks   = [t["week"] for t in timeline]
        n       = len(weeks)
        x       = np.arange(n)
        comp    = [t["composite"] for t in timeline]
        alerts  = [t["alert_level"] for t in timeline]
        l2s     = [t["l2"] or 0.0 for t in timeline]

        ax.plot(x, comp, color="#7c3aed", lw=1.8, marker="D", ms=3, label="Composite")
        ax.plot(x, l2s, color="#047857", lw=1.0, alpha=0.55, label="L2 하수")
        ax.axhline(THRESH_YELLOW, color="#ca8a04", ls="--", lw=1.0, alpha=0.7)
        ax.axhline(THRESH_RED,    color="#dc2626", ls="--", lw=1.0, alpha=0.7)

        for i, alert in enumerate(alerts):
            if alert != "GREEN":
                ax.axvspan(i - 0.4, i + 0.4, color=ALERT_COLORS[alert], alpha=0.2, zorder=1)

        m = result["metrics"]
        ax.set_title(
            f"{region}\nR={m['recall']:.2f} F1={m['f1']:.2f} FAR={m['false_alarm_rate']:.2f}",
            fontsize=8.5, fontweight="bold", pad=4,
        )
        ax.set_ylim(-5, 105)
        ax.set_xticks(x[::4])
        ax.set_xticklabels(weeks[::4], rotation=45, ha="right", fontsize=5.5)
        ax.grid(axis="y", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)

    # 남는 subplot 숨기기
    for idx in range(len(region_list), len(axes_flat)):
        axes_flat[idx].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(out_path, dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("17지역 타임라인 플롯 저장: %s", out_path)


# ─────────────────────── 17지역 메트릭 bar chart ─────────────────────────────
def plot_17regions_metrics(results: dict[str, dict], out_path: Path) -> None:
    """17개 지역 FAR / Recall / F1 bar chart."""
    valid = {r: v for r, v in results.items() if v.get("status") != "skipped"}
    regions   = list(valid.keys())
    recall    = [valid[r]["metrics"]["recall"]            for r in regions]
    f1        = [valid[r]["metrics"]["f1"]                for r in regions]
    far       = [valid[r]["metrics"]["false_alarm_rate"]  for r in regions]

    x     = np.arange(len(regions))
    width = 0.25

    fig, ax = plt.subplots(figsize=(18, 7))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    b1 = ax.bar(x - width, recall, width, label="Recall",    color="#16a34a", alpha=0.85, zorder=3)
    b2 = ax.bar(x,         f1,     width, label="F1",        color="#7c3aed", alpha=0.85, zorder=3)
    b3 = ax.bar(x + width, far,    width, label="FAR",       color="#dc2626", alpha=0.85, zorder=3)

    for bars, vals in ((b1, recall), (b2, f1), (b3, far)):
        for bar, val in zip(bars, vals):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.015,
                f"{val:.2f}",
                ha="center", va="bottom", fontsize=7, fontweight="bold",
            )

    mean_recall = np.mean(recall)
    mean_f1     = np.mean(f1)
    mean_far    = np.mean(far)

    ax.axhline(mean_recall, color="#16a34a", ls=":", lw=1.3, alpha=0.7, label=f"평균 Recall={mean_recall:.3f}")
    ax.axhline(mean_far,    color="#dc2626", ls=":", lw=1.3, alpha=0.7, label=f"평균 FAR={mean_far:.3f}")
    ax.axhline(0.3,         color="#f97316", ls="--", lw=1.5, alpha=0.8, label="FAR 목표 < 0.3")

    ax.set_xticks(x)
    ax.set_xticklabels(regions, rotation=40, ha="right", fontsize=9)
    ax.set_ylim(0, 1.3)
    ax.set_ylabel("점수", fontsize=12)
    ax.set_title(
        f"UIS 17개 시·도 백테스트 — Recall / F1 / FAR\n"
        f"평균: Recall={mean_recall:.3f}  F1={mean_f1:.3f}  FAR={mean_far:.3f}",
        fontsize=13, fontweight="bold",
    )
    ax.legend(fontsize=9, loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("17지역 메트릭 플롯 저장: %s", out_path)


# ─────────────────────── FAR 비교 차트 (게이트 전·후) ───────────────────────
def plot_far_comparison(
    results_with_gate: dict[str, dict],
    results_no_gate: dict[str, dict],
    out_path: Path,
) -> None:
    """게이트 적용 전·후 FAR 비교 bar chart."""
    valid_with = {r: v for r, v in results_with_gate.items() if v.get("status") != "skipped"}
    regions = list(valid_with.keys())

    far_before = [results_no_gate.get(r, {}).get("metrics", {}).get("false_alarm_rate", 0.0) for r in regions]
    far_after  = [valid_with[r]["metrics"]["false_alarm_rate"] for r in regions]
    recall_before = [results_no_gate.get(r, {}).get("metrics", {}).get("recall", 0.0) for r in regions]
    recall_after  = [valid_with[r]["metrics"]["recall"] for r in regions]

    x     = np.arange(len(regions))
    width = 0.35

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))
    fig.patch.set_facecolor("#f8fafc")
    fig.suptitle(
        "게이트 B (2계층 교차검증) 적용 전·후 비교\n"
        f"게이트 B: {_CROSS_VALIDATION_MIN_LAYERS}계층이상{_CROSS_VALIDATION_LAYER_THRESHOLD:.0f}+",
        fontsize=13, fontweight="bold",
    )

    # ── FAR 비교 ──────────────────────────────────────────────────────────
    ax1.set_facecolor("#f8fafc")
    b1 = ax1.bar(x - width / 2, far_before, width, label="게이트 미적용", color="#94a3b8", alpha=0.85, zorder=3)
    b2 = ax1.bar(x + width / 2, far_after,  width, label="게이트 적용",  color="#dc2626", alpha=0.85, zorder=3)

    for bar, val in zip(b1, far_before):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=7.5, color="#475569")
    for bar, val in zip(b2, far_after):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#991b1b")

    mean_before = np.mean(far_before)
    mean_after  = np.mean(far_after)
    ax1.axhline(0.3, color="#f97316", ls="--", lw=1.5, label="목표 FAR < 0.3")
    ax1.axhline(0.5, color="#fbbf24", ls="--", lw=1.3, label="수용 FAR < 0.5")
    ax1.set_xticks(x)
    ax1.set_xticklabels(regions, rotation=40, ha="right", fontsize=9)
    ax1.set_ylim(0, 1.2)
    ax1.set_ylabel("False Alarm Rate", fontsize=11)
    ax1.set_title(
        f"FAR 비교\n미적용 평균={mean_before:.3f} → 적용 평균={mean_after:.3f}",
        fontsize=11, fontweight="bold",
    )
    ax1.legend(fontsize=9)
    ax1.grid(axis="y", alpha=0.3)
    ax1.spines[["top", "right"]].set_visible(False)

    # ── Recall 비교 ───────────────────────────────────────────────────────
    ax2.set_facecolor("#f8fafc")
    b3 = ax2.bar(x - width / 2, recall_before, width, label="게이트 미적용", color="#94a3b8", alpha=0.85, zorder=3)
    b4 = ax2.bar(x + width / 2, recall_after,  width, label="게이트 적용",  color="#16a34a", alpha=0.85, zorder=3)

    for bar, val in zip(b3, recall_before):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=7.5, color="#475569")
    for bar, val in zip(b4, recall_after):
        ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                 f"{val:.2f}", ha="center", va="bottom", fontsize=7.5, fontweight="bold", color="#166534")

    mean_r_before = np.mean(recall_before)
    mean_r_after  = np.mean(recall_after)
    ax2.axhline(0.85, color="#16a34a", ls="--", lw=1.5, label="목표 Recall ≥ 0.85")
    ax2.set_xticks(x)
    ax2.set_xticklabels(regions, rotation=40, ha="right", fontsize=9)
    ax2.set_ylim(0, 1.25)
    ax2.set_ylabel("Recall", fontsize=11)
    ax2.set_title(
        f"Recall 비교\n미적용 평균={mean_r_before:.3f} → 적용 평균={mean_r_after:.3f}",
        fontsize=11, fontweight="bold",
    )
    ax2.legend(fontsize=9)
    ax2.grid(axis="y", alpha=0.3)
    ax2.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.94])
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("FAR 비교 플롯 저장: %s", out_path)


# ─────────────────────── 17지역 JSON 생성 ────────────────────────────────────
def build_17regions_json(
    results: dict[str, dict],
    results_no_gate: dict[str, dict],
) -> dict:
    """17개 지역 결과를 요약 JSON 으로 변환한다."""
    regions_out = {}

    for region, res in results.items():
        if res.get("status") == "skipped":
            regions_out[region] = {"status": "skipped", "reason": res.get("reason", "ground_truth_missing")}
            continue

        m  = res["metrics"]
        cm = res["confusion_matrix"]
        m0 = results_no_gate.get(region, {}).get("metrics", {})

        regions_out[region] = {
            "status":              "ok",
            "first_yellow_week":   res.get("first_yellow_week"),
            "confirmed_peak_week": res.get("confirmed_peak_week"),
            "confirmed_peak_count": res.get("confirmed_peak_count"),
            "lead_weeks":          res.get("lead_time_weeks"),
            # 게이트 적용 후
            "precision":           m["precision"],
            "recall":              m["recall"],
            "f1":                  m["f1"],
            "false_alarm_rate":    m["false_alarm_rate"],
            "confusion_matrix":    cm,
            # 게이트 미적용 (비교용)
            "far_no_gate":         m0.get("false_alarm_rate"),
            "recall_no_gate":      m0.get("recall"),
            "f1_no_gate":          m0.get("f1"),
            "weeks_analyzed":      res.get("weeks_analyzed"),
        }

    valid = [v for v in regions_out.values() if v.get("status") == "ok"]
    skipped_regions = [r for r, v in regions_out.items() if v.get("status") == "skipped"]
    ok_regions = [r for r, v in regions_out.items() if v.get("status") == "ok"]

    mean_recall = round(float(np.mean([v["recall"]            for v in valid])), 3) if valid else None
    mean_prec   = round(float(np.mean([v["precision"]         for v in valid])), 3) if valid else None
    mean_f1     = round(float(np.mean([v["f1"]                for v in valid])), 3) if valid else None
    mean_far    = round(float(np.mean([v["false_alarm_rate"]   for v in valid])), 3) if valid else None
    mean_far_no = round(float(np.mean([v["far_no_gate"] for v in valid if v["far_no_gate"] is not None])), 3) if valid else None

    validation_ok = (
        mean_far is not None and mean_far < 0.5
        and mean_recall is not None and mean_recall >= 0.85
        and len(ok_regions) >= 4
    )

    return {
        "description": "UIS 17개 시·도 백테스트 (2025-W40 ~ 2026-W08)",
        "gate_config": {
            "cross_validation_min_layers":    _CROSS_VALIDATION_MIN_LAYERS,
            "cross_validation_layer_threshold": _CROSS_VALIDATION_LAYER_THRESHOLD,
            "red_threshold":                  _RED_THRESHOLD,
            "gate_a_status":                  "discarded (sweep 결과 sweet spot 없음)",
        },
        "regions": regions_out,
        "summary": {
            "total_regions":       len(ALL_17_REGIONS),
            "ok_regions":          len(ok_regions),
            "skipped_regions":     skipped_regions,
            "mean_recall":         mean_recall,
            "mean_precision":      mean_prec,
            "mean_f1":             mean_f1,
            "mean_far_with_gate":  mean_far,
            "mean_far_no_gate":    mean_far_no,
            "far_delta":           round(mean_far - mean_far_no, 3) if (mean_far and mean_far_no) else None,
        },
        "validation": {
            "mean_far_lt_0.5":     mean_far < 0.5 if mean_far is not None else False,
            "mean_far_lt_0.3":     mean_far < 0.3 if mean_far is not None else False,
            "mean_recall_gte_0.85": mean_recall >= 0.85 if mean_recall is not None else False,
            "ok_regions_gte_4":    len(ok_regions) >= 4,
            "all_pass":            validation_ok,
        },
    }


# ─────────────────────── 게이트 미적용 백테스트 재계산 ────────────────────────
def recompute_no_gate(results_with_gate: dict[str, dict]) -> dict[str, dict]:
    """게이트 미적용(기존 2계층 교차검증만) 메트릭을 재계산한다."""
    no_gate: dict[str, dict] = {}

    for region, res in results_with_gate.items():
        if res.get("status") == "skipped":
            no_gate[region] = res
            continue

        timeline = res["weekly_timeline"]
        peak_cases = res["confirmed_peak_count"]
        peak_week  = res["confirmed_peak_week"]

        # 게이트 미적용 경보 레벨 재계산
        for w in timeline:
            l1, l2, l3 = w.get("l1"), w.get("l2"), w.get("l3")
            c = w["composite"]
            w["alert_level_no_gate"] = _determine_alert_level_no_gate(c, l1, l2, l3)

        metrics_no_gate = _compute_metrics_from_timeline(
            timeline, peak_cases, peak_week, alert_key="alert_level_no_gate"
        )
        no_gate[region] = {
            "metrics": metrics_no_gate["metrics"],
        }

    return no_gate


# ─────────────────────── 엔트리포인트 ────────────────────────────────────────
async def _main() -> None:
    logger.info("=== UIS 17개 시·도 백테스트 시작 ===")
    logger.info("게이트 B: %d계층 이상 %.1f+ 필요 (게이트 A 폐기됨)",
                _CROSS_VALIDATION_MIN_LAYERS, _CROSS_VALIDATION_LAYER_THRESHOLD)

    results: dict[str, dict] = {}

    for region in ALL_17_REGIONS:
        logger.info("[%s] 백테스트 실행 중...", region)
        try:
            res = await run_backtest(region)
            results[region] = res
            m = res["metrics"]
            logger.info(
                "[%s] 완료 — Recall=%.3f F1=%.3f FAR=%.3f",
                region, m["recall"], m["f1"], m["false_alarm_rate"],
            )
        except Exception as exc:
            logger.error("[%s] 백테스트 실패: %s", region, exc)
            results[region] = {
                "status": "skipped",
                "reason": str(exc),
                "region": region,
            }

    # 게이트 미적용 메트릭 재계산 (비교용)
    results_no_gate = recompute_no_gate(results)

    # ── JSON 저장 ────────────────────────────────────────────────────────
    combined_json = build_17regions_json(results, results_no_gate)
    json_path = OUTPUT_DIR / "backtest_17regions.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(combined_json, f, ensure_ascii=False, indent=2, default=str)
    logger.info("JSON 저장: %s", json_path)

    # ── 타임라인 플롯 ────────────────────────────────────────────────────
    timeline_png = OUTPUT_DIR / "backtest_17regions_timeline.png"
    valid_results = {r: v for r, v in results.items() if v.get("status") != "skipped"}
    plot_17regions_timeline(valid_results, timeline_png)

    # ── 메트릭 bar chart ─────────────────────────────────────────────────
    metrics_png = OUTPUT_DIR / "backtest_17regions_metrics.png"
    plot_17regions_metrics(valid_results, metrics_png)

    # ── FAR 비교 차트 ─────────────────────────────────────────────────────
    far_png = OUTPUT_DIR / "far_comparison.png"
    plot_far_comparison(valid_results, results_no_gate, far_png)

    # ── assets 복사 ──────────────────────────────────────────────────────
    import shutil
    for src in (json_path, timeline_png, metrics_png, far_png):
        dst = ASSETS_DIR / src.name
        shutil.copy2(src, dst)
        logger.info("assets 복사: %s → %s", src.name, dst)

    # ── 콘솔 요약 출력 ───────────────────────────────────────────────────
    s = combined_json["summary"]
    v = combined_json["validation"]

    print("\n" + "=" * 80)
    print("[UIS 17개 시·도 백테스트 결과] (게이트 적용 후)")
    print(f"{'지역':<10}  첫YELLOW   Peak       선행  Prec  Rec   F1    FAR   FAR(전)")
    print("-" * 80)

    for region in ALL_17_REGIONS:
        rv = combined_json["regions"][region]
        if rv.get("status") == "skipped":
            print(f"{region:<10}  {'SKIPPED':>55}")
            continue
        print(
            f"{region:<10}  "
            f"{rv['first_yellow_week'] or 'N/A':<10} "
            f"{rv['confirmed_peak_week'] or 'N/A':<10} "
            f"{rv['lead_weeks'] or 0:>4}주  "
            f"{rv['precision']:.3f}  "
            f"{rv['recall']:.3f}  "
            f"{rv['f1']:.3f}  "
            f"{rv['false_alarm_rate']:.3f}  "
            f"{rv['far_no_gate']:.3f}"
        )

    print("-" * 80)
    print(
        f"{'평균(OK)':<10}  {'':10} {'':10} "
        f"{'':>5}  "
        f"{s['mean_precision']:.3f}  "
        f"{s['mean_recall']:.3f}  "
        f"{s['mean_f1']:.3f}  "
        f"{s['mean_far_with_gate']:.3f}  "
        f"{s['mean_far_no_gate']:.3f}"
    )
    print("=" * 80)
    print(f"\n  OK 지역 수: {s['ok_regions']} / {s['total_regions']}")
    print(f"  SKIPPED: {s['skipped_regions']}")
    print(f"  FAR 개선: {s['mean_far_no_gate']:.3f} → {s['mean_far_with_gate']:.3f} (Δ{s['far_delta']:+.3f})")
    print()
    print("[검증 기준]")
    print(f"  평균 FAR < 0.5 (수용):  {'✓ PASS' if v['mean_far_lt_0.5'] else '✗ FAIL'}")
    print(f"  평균 FAR < 0.3 (목표):  {'✓ PASS' if v['mean_far_lt_0.3'] else '✗ FAIL'}")
    print(f"  평균 Recall ≥ 0.85:    {'✓ PASS' if v['mean_recall_gte_0.85'] else '✗ FAIL'}")
    print(f"  OK 지역 ≥ 4개:         {'✓ PASS' if v['ok_regions_gte_4'] else '✗ FAIL'}")
    print(f"  전체 Pass:              {'✓ ALL PASS' if v['all_pass'] else '✗ SOME FAIL'}")
    print()
    print(f"  산출 파일:")
    print(f"    {json_path}")
    print(f"    {timeline_png}")
    print(f"    {metrics_png}")
    print(f"    {far_png}")
    print()


if __name__ == "__main__":
    asyncio.run(_main())
