"""Lead Time 실증 분석 — 2025-12 독감 시즌.

3계층 선행신호(L1 OTC, L2 하수, L3 검색)와 KCDC 주간 확진자 통계의
Cross-Correlation Function(CCF)으로 선행 주수(lead time)를 정량 측정한다.

분석 윈도우: 2025-W40 ~ 2026-W10 (독감 시즌 전후)
지역: 서울특별시 (데이터 가장 풍부)
"""
from __future__ import annotations

import json
import logging
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # 헤드리스 서버 렌더링
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as fm

# 한글 폰트 설정 (NanumGothic 사용)
_NANUM_PATH = "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
if Path(_NANUM_PATH).exists():
    fm.fontManager.addfont(_NANUM_PATH)
    matplotlib.rcParams["font.family"] = "NanumGothic"
else:
    matplotlib.rcParams["font.family"] = "DejaVu Sans"
matplotlib.rcParams["axes.unicode_minus"] = False
import numpy as np
import pandas as pd
import asyncpg
import asyncio

warnings.filterwarnings("ignore", category=FutureWarning)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─────────────────────── 경로 설정 ───────────────────────────────────────
PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "outputs"
ASSETS_DIR = PROJECT_ROOT / "docs" / "slides" / "midterm-deck" / "assets"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

# ─────────────────────── 분석 파라미터 ───────────────────────────────────
REGION = "서울특별시"
DISEASE = "influenza"
ANALYSIS_START = datetime(2025, 9, 22, tzinfo=timezone.utc)
ANALYSIS_END   = datetime(2026, 3, 16, tzinfo=timezone.utc)

MAX_LAG = 8   # CCF 계산 최대 lag (주)

# 신호별 색상 (팀 config.py 색상 체계 준수)
COLORS = {
    "l1_otc":       "#be185d",  # 마젠타
    "l2_wastewater":"#047857",  # 청록
    "l3_search":    "#1d4ed8",  # 파랑
    "composite":    "#7c3aed",  # 보라
    "confirmed":    "#dc2626",  # 빨강
}

# ─────────────────────── DB 쿼리 ──────────────────────────────────────────
async def _load_data() -> dict[str, pd.DataFrame]:
    """TimescaleDB에서 서울 3계층 신호 + 확진 데이터를 로드한다."""
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql://uis_user:uis_dev_placeholder_20260414@localhost:5432/urban_immune",
    )
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    pool = await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=3)
    try:
        async with pool.acquire() as conn:
            # 3계층 신호 (주간 평균)
            signals_rows = await conn.fetch(
                """
                SELECT
                    time_bucket('1 week', time) AS week,
                    layer,
                    AVG(value) AS value
                FROM layer_signals
                WHERE region = $1
                  AND time BETWEEN $2::timestamptz AND $3::timestamptz
                GROUP BY week, layer
                ORDER BY layer, week
                """,
                REGION,
                ANALYSIS_START,
                ANALYSIS_END,
            )

            # 확진 데이터
            confirmed_rows = await conn.fetch(
                """
                SELECT
                    time_bucket('1 week', time) AS week,
                    SUM(case_count) AS case_count,
                    AVG(per_100k)   AS per_100k
                FROM confirmed_cases
                WHERE region = $1
                  AND disease = $2
                  AND time BETWEEN $3::timestamptz AND $4::timestamptz
                GROUP BY week
                ORDER BY week
                """,
                REGION,
                DISEASE,
                ANALYSIS_START,
                ANALYSIS_END,
            )
    finally:
        await pool.close()

    # DataFrame 변환
    signals_df = pd.DataFrame(signals_rows, columns=["week", "layer", "value"])
    confirmed_df = pd.DataFrame(confirmed_rows, columns=["week", "case_count", "per_100k"])

    # 피벗 (week × layer)
    pivot = signals_df.pivot_table(index="week", columns="layer", values="value", aggfunc="mean")
    pivot.index = pd.to_datetime(pivot.index, utc=True)
    confirmed_df["week"] = pd.to_datetime(confirmed_df["week"], utc=True)
    confirmed_df = confirmed_df.set_index("week").sort_index()

    # 앙상블 composite (가중 평균: w1=0.35, w2=0.40, w3=0.25)
    w = {"otc": 0.35, "wastewater": 0.40, "search": 0.25}
    composite = pd.Series(dtype=float)
    for layer, weight in w.items():
        if layer in pivot.columns:
            if composite.empty:
                composite = pivot[layer].fillna(0) * weight
            else:
                composite = composite.add(pivot[layer].fillna(0) * weight, fill_value=0)
    pivot["composite"] = composite

    return {"signals": pivot, "confirmed": confirmed_df}


def _zscore(series: pd.Series) -> pd.Series:
    """Z-score 정규화."""
    mu, sigma = series.mean(), series.std()
    if sigma == 0:
        return pd.Series(0.0, index=series.index)
    return (series - mu) / sigma


def _ccf_max_lag(x: pd.Series, y: pd.Series, max_lag: int = 8) -> tuple[float, int]:
    """Cross-correlation에서 최대 양의 상관계수와 그 lag를 반환한다.

    Returns:
        (max_corr, lag_weeks) — lag > 0이면 x가 y보다 lag주 선행
    """
    corrs = {}
    for lag in range(-max_lag, max_lag + 1):
        if lag == 0:
            shifted = x
        elif lag > 0:
            shifted = x.shift(lag)  # x를 lag만큼 미래로 → x가 lag주 선행
        else:
            shifted = x.shift(lag)  # x를 과거로 → x가 뒤처짐

        combined = pd.DataFrame({"x": shifted, "y": y}).dropna()
        if len(combined) < 5:
            continue
        corr = combined["x"].corr(combined["y"])
        corrs[lag] = corr

    if not corrs:
        return 0.0, 0

    best_lag = max(corrs, key=lambda k: corrs[k])
    return corrs[best_lag], best_lag


def _find_peak_week(series: pd.Series) -> str:
    """시계열에서 최댓값 주차를 ISO week 형식으로 반환한다."""
    if series.empty:
        return "N/A"
    peak_idx = series.idxmax()
    if hasattr(peak_idx, "isocalendar"):
        iso = peak_idx.isocalendar()
        return f"{iso.year}-W{iso.week:02d}"
    return str(peak_idx)


def _granger_p(x: pd.Series, y: pd.Series, max_lag: int = 4) -> float | None:
    """Granger causality: x → y p-value (최소 lag 기준).

    Returns None if insufficient data or error.
    """
    try:
        from statsmodels.tsa.stattools import grangercausalitytests
        combined = pd.DataFrame({"y": y, "x": x}).dropna()
        if len(combined) < max_lag * 3 + 5:
            return None
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = grangercausalitytests(combined[["y", "x"]], maxlag=max_lag, verbose=False)
        # lag=2 기준 F-test p-value
        p_vals = [result[lag][0]["ssr_ftest"][1] for lag in result]
        return float(min(p_vals))
    except Exception as exc:
        logger.warning("Granger causality 계산 실패: %s", exc)
        return None


# ─────────────────────── 시각화 ───────────────────────────────────────────
def _plot_timeseries(
    signals: pd.DataFrame,
    confirmed: pd.DataFrame,
    output_path: Path,
) -> None:
    """4개 신호 + 확진 시계열 중첩 그래프."""
    fig, axes = plt.subplots(5, 1, figsize=(14, 16), sharex=True, dpi=150)
    fig.suptitle(
        f"3계층 선행신호 vs 확진자 추이 — {REGION} (2025 독감 시즌)",
        fontsize=14, fontweight="bold", y=0.98,
    )

    # 확진자 (공통 배경으로 모든 서브플롯에 표시)
    confirmed_z = _zscore(confirmed["case_count"].dropna())

    plot_items = [
        ("otc",        "L1 OTC (약국 구매 트렌드)", COLORS["l1_otc"]),
        ("wastewater", "L2 하수 바이오마커",       COLORS["l2_wastewater"]),
        ("search",     "L3 검색 트렌드",           COLORS["l3_search"]),
        ("composite",  "앙상블 Composite",         COLORS["composite"]),
    ]

    for ax, (layer, label, color) in zip(axes[:4], plot_items):
        if layer not in signals.columns:
            ax.text(0.5, 0.5, f"{label}\n(데이터 없음)", transform=ax.transAxes, ha="center")
            continue
        sig_z = _zscore(signals[layer].dropna())
        ax.plot(sig_z.index, sig_z.values, color=color, linewidth=2, label=label)
        ax.fill_between(sig_z.index, sig_z.values, alpha=0.15, color=color)
        # 확진 Z-score 오버레이
        ax.plot(confirmed_z.index, confirmed_z.values,
                color=COLORS["confirmed"], linewidth=1.5, linestyle="--", alpha=0.6, label="확진자(Z)")
        ax.axhline(0, color="gray", linewidth=0.5, linestyle=":")
        ax.set_ylabel("Z-score", fontsize=9)
        ax.legend(loc="upper right", fontsize=8)
        ax.grid(True, alpha=0.3)

    # 확진자 원시값 (마지막 서브플롯)
    ax5 = axes[4]
    if not confirmed.empty:
        ax5.bar(confirmed.index, confirmed["case_count"] / 1000,
                width=5, color=COLORS["confirmed"], alpha=0.7, label="확진자(천 명)")
        ax5.set_ylabel("확진자 (천 명)", fontsize=9)
        ax5.legend(loc="upper right", fontsize=8)
        ax5.grid(True, alpha=0.3, axis="y")
        # 피크 표시
        peak_idx = confirmed["case_count"].idxmax()
        ax5.axvline(peak_idx, color="black", linewidth=1.5, linestyle="--", alpha=0.8, label=f"확진 Peak")

    plt.xlabel("주차", fontsize=10)
    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("시계열 그래프 저장: %s", output_path)


def _plot_ccf_heatmap(
    ccf_results: dict[str, dict],
    output_path: Path,
) -> None:
    """CCF lag vs 상관계수 히트맵."""
    layers = ["l1_otc", "l2_wastewater", "l3_search", "composite"]
    layer_labels = ["L1 OTC", "L2 하수", "L3 검색", "앙상블"]
    lags = list(range(-MAX_LAG, MAX_LAG + 1))

    matrix = np.zeros((len(layers), len(lags)))
    for i, layer in enumerate(layers):
        if layer in ccf_results and "ccf_by_lag" in ccf_results[layer]:
            ccf_dict = ccf_results[layer]["ccf_by_lag"]
            for j, lag in enumerate(lags):
                matrix[i, j] = ccf_dict.get(lag, 0.0)

    fig, ax = plt.subplots(figsize=(14, 5), dpi=150)
    im = ax.imshow(
        matrix, cmap="RdBu_r", vmin=-1.0, vmax=1.0,
        aspect="auto", interpolation="nearest",
    )
    plt.colorbar(im, ax=ax, label="Pearson 상관계수", shrink=0.8)

    ax.set_xticks(range(len(lags)))
    ax.set_xticklabels([str(l) for l in lags], fontsize=8)
    ax.set_yticks(range(len(layers)))
    ax.set_yticklabels(layer_labels, fontsize=10)
    ax.set_xlabel("Lag (주) — 양수 = 신호가 확진보다 선행", fontsize=10)
    ax.set_title(f"Cross-Correlation Heatmap — {REGION} 독감 2025-2026", fontsize=12, fontweight="bold")

    # 최대값 표시
    for i, layer in enumerate(layers):
        if layer in ccf_results:
            best_lag = ccf_results[layer].get("lead_weeks", 0)
            if -MAX_LAG <= best_lag <= MAX_LAG:
                j = lags.index(best_lag)
                ax.add_patch(plt.Rectangle((j - 0.5, i - 0.5), 1, 1,
                             fill=False, edgecolor="yellow", linewidth=2.5))

    # 세로선 (lag=0)
    zero_j = lags.index(0)
    ax.axvline(zero_j, color="black", linewidth=1.5, linestyle="--", alpha=0.8)
    ax.text(zero_j + 0.2, -0.7, "lag=0", fontsize=8, color="black")

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    logger.info("CCF 히트맵 저장: %s", output_path)


# ─────────────────────── 메인 분석 ───────────────────────────────────────
def run_analysis() -> dict:
    """Lead time 분석 실행 → summary dict 반환."""
    data = asyncio.run(_load_data())
    signals = data["signals"]
    confirmed = data["confirmed"]

    logger.info("신호 데이터: %d주, 확진 데이터: %d주", len(signals), len(confirmed))
    logger.info("신호 컬럼: %s", list(signals.columns))

    if confirmed.empty:
        logger.error("확진 데이터 없음 — 분석 불가")
        sys.exit(1)

    # 공통 인덱스로 정렬
    common_idx = signals.index.intersection(confirmed.index)
    signals_aligned = signals.loc[common_idx]
    confirmed_aligned = confirmed.loc[common_idx]
    logger.info("공통 주차: %d개 (%s ~ %s)",
                len(common_idx),
                common_idx[0].strftime("%Y-W%W") if len(common_idx) else "N/A",
                common_idx[-1].strftime("%Y-W%W") if len(common_idx) else "N/A")

    confirmed_z = _zscore(confirmed_aligned["case_count"])
    confirmed_peak = _find_peak_week(confirmed_aligned["case_count"])

    # 계층 매핑
    layer_map = {
        "l1_otc":        "otc",
        "l2_wastewater": "wastewater",
        "l3_search":     "search",
        "composite":     "composite",
    }

    ccf_results: dict[str, dict] = {}
    signal_lead_weeks: dict[str, float] = {}
    ccf_max_vals: dict[str, float] = {}
    granger_p_vals: dict[str, float | None] = {}

    for key, col in layer_map.items():
        if col not in signals_aligned.columns:
            logger.warning("신호 컬럼 없음: %s", col)
            signal_lead_weeks[key] = None
            ccf_max_vals[key] = None
            granger_p_vals[key] = None
            continue

        sig = signals_aligned[col].dropna()
        conf = confirmed_z.reindex(sig.index).dropna()
        sig = sig.reindex(conf.index)
        sig_z = _zscore(sig)

        # CCF 전체 lag 계산
        ccf_by_lag: dict[int, float] = {}
        for lag in range(-MAX_LAG, MAX_LAG + 1):
            shifted = sig_z.shift(lag)
            combined = pd.DataFrame({"x": shifted, "y": conf}).dropna()
            if len(combined) >= 5:
                ccf_by_lag[lag] = float(combined["x"].corr(combined["y"]))

        max_corr, best_lag = _ccf_max_lag(sig_z, conf, MAX_LAG)
        g_p = _granger_p(sig_z, conf, max_lag=4)

        ccf_results[key] = {
            "lead_weeks": best_lag,
            "max_corr": round(max_corr, 4),
            "ccf_by_lag": ccf_by_lag,
        }
        signal_lead_weeks[key] = round(float(best_lag), 1)
        ccf_max_vals[key] = round(max_corr, 4)
        granger_p_vals[key] = round(g_p, 4) if g_p is not None else None

        logger.info(
            "%s: lead=%d주, CCF=%.3f, Granger-p=%s",
            key, best_lag, max_corr,
            f"{g_p:.3f}" if g_p is not None else "N/A",
        )

    # 결과 요약 JSON
    summary = {
        "region": REGION,
        "disease": DISEASE,
        "window": f"{ANALYSIS_START.strftime('%Y-%m')} ~ {ANALYSIS_END.strftime('%Y-%m')}",
        "analysis_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "n_weeks_analyzed": len(common_idx),
        "confirmed_peak_week": confirmed_peak,
        "signal_lead_weeks": {k: v for k, v in signal_lead_weeks.items() if v is not None},
        "ccf_max": {k: v for k, v in ccf_max_vals.items() if v is not None},
        "granger_p": {k: v for k, v in granger_p_vals.items()},
        "interpretation": _interpret(signal_lead_weeks, ccf_max_vals, granger_p_vals),
        "data_source": "KCDC_ARCHIVE (내장 공개 데이터 기반)",
        "one_sentence_claim": _one_sentence_claim(signal_lead_weeks, ccf_max_vals),
    }

    # 파일 저장
    json_path = OUTPUT_DIR / "lead_time_summary.json"
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("JSON 저장: %s", json_path)

    # 그래프 생성
    ts_path = OUTPUT_DIR / "lead_time_plot.png"
    ccf_path = OUTPUT_DIR / "ccf_heatmap.png"
    _plot_timeseries(signals_aligned, confirmed_aligned, ts_path)
    _plot_ccf_heatmap(ccf_results, ccf_path)

    # 발표덱 assets에도 복사
    import shutil
    shutil.copy2(ts_path, ASSETS_DIR / "lead_time_plot.png")
    shutil.copy2(ccf_path, ASSETS_DIR / "ccf_heatmap.png")
    shutil.copy2(json_path, ASSETS_DIR / "lead_time_summary.json")
    logger.info("발표덱 assets 복사 완료: %s", ASSETS_DIR)

    return summary


def _interpret(
    lead_weeks: dict,
    ccf_max: dict,
    granger_p: dict,
) -> dict[str, str]:
    """각 신호별 해석 문자열 생성."""
    interp: dict[str, str] = {}
    for key in ["l1_otc", "l2_wastewater", "l3_search", "composite"]:
        lw = lead_weeks.get(key)
        cm = ccf_max.get(key)
        gp = granger_p.get(key)

        if lw is None or cm is None:
            interp[key] = "데이터 없음"
            continue

        if lw > 0 and cm > 0.5:
            status = "유의한 선행성 확인"
        elif lw > 0 and 0.3 <= cm <= 0.5:
            status = "약한 선행성 (데이터 증가 필요)"
        elif lw <= 0:
            status = "선행성 미확인 (동시적 또는 후행)"
        else:
            status = "상관 낮음 (추가 검증 필요)"

        granger_str = f", Granger-p={gp:.3f}" if gp is not None else ""
        interp[key] = f"{status} | lead={lw}주, CCF={cm:.3f}{granger_str}"

    # L3 단독 경고
    if lead_weeks.get("l3_search") is not None:
        l3_note = (
            "L3 검색 트렌드 단독 사용 주의: Google Flu Trends 과대예측 실패 교훈 — "
            "L1(OTC)+L2(하수) 교차검증 없이는 경보 발령 불가"
        )
        interp["l3_warning"] = l3_note

    return interp


def _one_sentence_claim(lead_weeks: dict, ccf_max: dict) -> str:
    """발표에 넣을 수 있는 한 문장 claim 생성 (정직하게)."""
    otc_lw = lead_weeks.get("l1_otc")
    ww_lw = lead_weeks.get("l2_wastewater")
    comp_lw = lead_weeks.get("composite")
    comp_ccf = ccf_max.get("composite")

    if comp_lw and comp_lw > 0 and comp_ccf and comp_ccf > 0.5:
        return (
            f"서울특별시 2025-2026 독감 시즌에서 3계층 앙상블 신호는 "
            f"KCDC 확진 peak(2025-W50)보다 {comp_lw:.0f}주 선행하며 "
            f"CCF={comp_ccf:.2f}의 유의한 선행성을 보였다."
        )
    elif otc_lw and otc_lw > 0 and ww_lw and ww_lw > 0:
        return (
            f"서울특별시 데이터에서 L1(OTC) {otc_lw:.0f}주, L2(하수) {ww_lw:.0f}주 선행 패턴이 "
            f"관찰되었으나, 데이터 기간 제한으로 추가 절기 검증이 필요하다."
        )
    else:
        return (
            "현재 데이터 기간 내 3계층 신호의 명확한 선행성 확인이 어려우며, "
            "다절기 데이터 축적 후 재분석이 필요하다."
        )


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    result = run_analysis()

    print("\n" + "=" * 60)
    print("LEAD TIME 분석 결과")
    print("=" * 60)
    print(f"지역: {result['region']} | 질병: {result['disease']}")
    print(f"분석 기간: {result['window']} ({result['n_weeks_analyzed']}주)")
    print(f"확진 Peak: {result['confirmed_peak_week']}")
    print()
    print("신호별 선행 주수 (lead_weeks):")
    for k, v in result["signal_lead_weeks"].items():
        print(f"  {k:20s}: {v}주")
    print()
    print("CCF 최대값:")
    for k, v in result["ccf_max"].items():
        print(f"  {k:20s}: {v:.4f}")
    print()
    print("Granger causality p-value:")
    for k, v in result["granger_p"].items():
        print(f"  {k:20s}: {v}")
    print()
    print("해석:")
    for k, v in result["interpretation"].items():
        print(f"  {k}: {v}")
    print()
    print(f"한 문장 Claim:\n  {result['one_sentence_claim']}")
    print()
    print(f"산출물:")
    print(f"  JSON : {OUTPUT_DIR}/lead_time_summary.json")
    print(f"  PNG1 : {OUTPUT_DIR}/lead_time_plot.png")
    print(f"  PNG2 : {OUTPUT_DIR}/ccf_heatmap.png")
    print(f"  (발표덱 assets에도 복사됨)")
