"""L2 게이트 임계값 sweep — sweet spot 탐색 또는 게이트 폐기 결정.

17지역 백테스트를 한 번만 실행하고, weekly_timeline 의 composite/l1/l2/l3 를
재활용해 임계값 [25, 15, 10, 5, 0] 별로 alert_level 만 재매핑 → 메트릭 계산.

산출물:
  analysis/outputs/l2_gate_sweep.json
  analysis/outputs/l2_gate_sweep.png

선정 기준 (모두 만족):
  - Recall  ≥ 0.85
  - FAR     <  0.55
  - F1      ≥ 0.66
"""
from __future__ import annotations

import asyncio
import json
import logging
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import numpy as np

_NANUM = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
if Path(_NANUM).exists():
    fm.fontManager.addfont(_NANUM)
    matplotlib.rcParams["font.family"] = "NanumGothic"
matplotlib.rcParams["axes.unicode_minus"] = False

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.backtest_2025_flu import run_backtest  # noqa: E402
from analysis.backtest_2025_flu_multi_17regions import (  # noqa: E402
    ALL_17_REGIONS,
    _compute_metrics_from_timeline,
)
from pipeline.scorer import (  # noqa: E402
    _CROSS_VALIDATION_LAYER_THRESHOLD,
    _CROSS_VALIDATION_MIN_LAYERS,
    _RED_THRESHOLD,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

OUTPUT_DIR = PROJECT_ROOT / "analysis" / "outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

THRESHOLD_CANDIDATES: tuple[float, ...] = (25.0, 15.0, 10.0, 5.0, 0.0)

YELLOW_THRESHOLD = 30.0
ORANGE_THRESHOLD = 55.0


def _classify_with_gates(
    composite: float,
    l1: float | None,
    l2: float | None,
    l3: float | None,
    l2_gate: float,
) -> str:
    """동일 게이트 로직을 임계값만 가변으로 재구현 (scorer.py 와 일치)."""
    if composite >= _RED_THRESHOLD:
        raw = "RED"
    elif composite >= ORANGE_THRESHOLD:
        raw = "ORANGE"
    elif composite >= YELLOW_THRESHOLD:
        raw = "YELLOW"
    else:
        raw = "GREEN"
    if raw == "GREEN":
        return "GREEN"

    safe_l2 = l2 if l2 is not None else 0.0
    if raw != "RED" and safe_l2 < l2_gate:
        return "GREEN"

    above = sum(
        1 for v in (l1, l2, l3)
        if v is not None and v >= _CROSS_VALIDATION_LAYER_THRESHOLD
    )
    if above < _CROSS_VALIDATION_MIN_LAYERS:
        return "GREEN"

    return raw


def _relabel_timeline(timeline: list[dict], l2_gate: float) -> list[dict]:
    out = []
    for w in timeline:
        new = dict(w)
        new["alert_sweep"] = _classify_with_gates(
            new["composite"], new.get("l1"), new.get("l2"), new.get("l3"), l2_gate
        )
        out.append(new)
    return out


async def _gather_timelines() -> dict[str, dict]:
    """17지역 run_backtest 1회 실행 + 결과 캐시."""
    cache: dict[str, dict] = {}
    for region in ALL_17_REGIONS:
        try:
            res = await run_backtest(region)
            cache[region] = res
            m = res["metrics"]
            logger.info(
                "[%s] timeline=%d주 R=%.2f F1=%.2f FAR=%.2f",
                region, len(res["weekly_timeline"]),
                m["recall"], m["f1"], m["false_alarm_rate"],
            )
        except Exception as exc:
            logger.warning("[%s] 백테스트 실패: %s", region, exc)
            cache[region] = {"status": "skipped", "reason": str(exc)}
    return cache


def _sweep(timelines: dict[str, dict]) -> dict[str, Any]:
    rows = []
    for thr in THRESHOLD_CANDIDATES:
        recalls, f1s, fars, precisions = [], [], [], []
        for region, res in timelines.items():
            if res.get("status") == "skipped":
                continue
            tl = _relabel_timeline(res["weekly_timeline"], thr)
            m = _compute_metrics_from_timeline(
                tl,
                res["confirmed_peak_count"],
                res["confirmed_peak_week"],
                alert_key="alert_sweep",
            )["metrics"]
            recalls.append(m["recall"])
            f1s.append(m["f1"])
            fars.append(m["false_alarm_rate"])
            precisions.append(m["precision"])

        rows.append({
            "threshold":  thr,
            "n_regions":  len(recalls),
            "recall":     round(float(np.mean(recalls)), 4)    if recalls    else None,
            "precision":  round(float(np.mean(precisions)), 4) if precisions else None,
            "f1":         round(float(np.mean(f1s)), 4)        if f1s        else None,
            "far":        round(float(np.mean(fars)), 4)       if fars       else None,
        })

    selected = None
    for r in rows:
        if (r["recall"] is not None and r["recall"] >= 0.85
                and r["far"] is not None and r["far"] < 0.55
                and r["f1"] is not None and r["f1"] >= 0.66):
            selected = r
            break

    return {
        "candidates": rows,
        "selection_criteria": {
            "recall_min": 0.85, "far_max": 0.55, "f1_min": 0.66,
        },
        "selected": selected,
        "decision": "ADOPT" if selected is not None else "DISCARD_GATE_A",
    }


def _plot_sweep(sweep: dict[str, Any], out_path: Path) -> None:
    rows = sweep["candidates"]
    labels = [f"L2<{r['threshold']:.0f}" for r in rows]
    x = np.arange(len(rows))
    width = 0.25

    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor("#f8fafc")
    ax.set_facecolor("#f8fafc")

    recall = [r["recall"] for r in rows]
    f1     = [r["f1"]     for r in rows]
    far    = [r["far"]    for r in rows]

    b1 = ax.bar(x - width, recall, width, label="Recall", color="#16a34a", alpha=0.85)
    b2 = ax.bar(x,         f1,     width, label="F1",     color="#7c3aed", alpha=0.85)
    b3 = ax.bar(x + width, far,    width, label="FAR",    color="#dc2626", alpha=0.85)

    for bars, vals in ((b1, recall), (b2, f1), (b3, far)):
        for bar, val in zip(bars, vals):
            if val is None:
                continue
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.012,
                    f"{val:.3f}", ha="center", va="bottom",
                    fontsize=8, fontweight="bold")

    ax.axhline(0.85, color="#16a34a", ls="--", lw=1.0, alpha=0.5)
    ax.axhline(0.55, color="#dc2626", ls="--", lw=1.0, alpha=0.5)
    ax.axhline(0.66, color="#7c3aed", ls="--", lw=1.0, alpha=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels)
    ax.set_ylim(0, 1.15)
    ax.set_ylabel("점수")
    decision = sweep["decision"]
    sel = sweep["selected"]
    sel_str = f" — 채택 임계값 L2<{sel['threshold']:.0f}" if sel else ""
    ax.set_title(
        f"L2 게이트 임계값 sweep (17지역 평균)\n결정: {decision}{sel_str}",
        fontsize=12, fontweight="bold",
    )
    ax.legend(loc="upper right")
    ax.grid(axis="y", alpha=0.3)
    ax.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    fig.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    logger.info("sweep PNG 저장: %s", out_path)


async def _main() -> None:
    logger.info("=== L2 게이트 임계값 sweep 시작 (17지역 1회 백테스트 + 메모리 sweep) ===")
    timelines = await _gather_timelines()
    sweep = _sweep(timelines)

    json_path = OUTPUT_DIR / "l2_gate_sweep.json"
    json_path.write_text(json.dumps(sweep, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("JSON 저장: %s", json_path)

    png_path = OUTPUT_DIR / "l2_gate_sweep.png"
    _plot_sweep(sweep, png_path)

    print("\n" + "=" * 64)
    print(f"{'임계값':<8} {'Recall':>8} {'Precision':>10} {'F1':>8} {'FAR':>8}")
    print("-" * 64)
    for r in sweep["candidates"]:
        print(
            f"L2<{r['threshold']:>4.0f}  "
            f"{r['recall']:>8.4f}  "
            f"{r['precision']:>10.4f}  "
            f"{r['f1']:>8.4f}  "
            f"{r['far']:>8.4f}"
        )
    print("=" * 64)
    print(f"\n결정: {sweep['decision']}")
    if sweep["selected"]:
        s = sweep["selected"]
        print(f"  선정 임계값 L2<{s['threshold']:.0f} — Recall={s['recall']} F1={s['f1']} FAR={s['far']}")
    else:
        print("  → 게이트 A 폐기 권장")
        print("  (어느 임계값도 Recall≥0.85 & FAR<0.55 & F1≥0.66 조건 만족 못함)")
    print()


if __name__ == "__main__":
    asyncio.run(_main())
