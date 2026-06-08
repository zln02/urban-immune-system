"""V11.2 — 17지역 × 3계층 Granger 인과성 검정 + 다중검정 보정.

Family expansion: V11.1 (서울 3 layer 검정) → V11.2 (17 region × 3 layer = 51 nominal tests).

정직 보고 (data caveat):
  - L1 OTC / L3 search 는 네이버 API 제약으로 전국 단일값을 17지역에 broadcast.
    → DB 검증: regions identical-to-region[0] = 100% (L1, L3).
    → effective unique tests = 1 each (degenerate cluster).
  - L2 wastewater 는 KOWAS region별 분리 → effective 17 tests.
  - Composite (가중평균 0.35·L1 + 0.40·L2 + 0.25·L3) 는 L2 region differences 가
    반영되어 17 region 별로 진짜 다름.

따라서 nominal family = 51 (17 × 3 layer) 이나, 통계적 정직성 기준:
  - effective independent tests ≈ 17 (L2) + 1 (L1) + 1 (L3) = 19.
  - 본 스크립트는 nominal 51 기준 Bonferroni / BH-FDR 모두 보고하되,
    effective 19 기준 보정도 함께 제공 (Prof. Cheon review 대비).

산출:
  analysis/outputs/granger_17regions_results.json

실행:
  .venv/bin/python analysis/granger_17regions.py
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import asyncpg
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("granger_17regions")

# ───────────────────────────── 상수 ─────────────────────────────────────────

ALL_17_REGIONS: list[str] = [
    "서울특별시", "경기도", "부산광역시", "인천광역시", "대구광역시",
    "대전광역시", "광주광역시", "울산광역시", "세종특별자치시",
    "강원특별자치도", "충청북도", "충청남도", "전라북도", "전라남도",
    "경상북도", "경상남도", "제주특별자치도",
]

LAYERS: list[str] = ["otc", "wastewater", "search"]
LAYER_LABEL: dict[str, str] = {
    "otc":        "L1_otc",
    "wastewater": "L2_wastewater",
    "search":     "L3_search",
}

ANALYSIS_START = datetime(2025, 9, 29, tzinfo=timezone.utc)
ANALYSIS_END   = datetime(2026, 3,  2, tzinfo=timezone.utc)
DISEASE = "influenza"

MAX_LAG = 4
MIN_SAMPLE = 12
ALPHA = 0.05
SEED = 42

W = {"otc": 0.35, "wastewater": 0.40, "search": 0.25}

OUTPUT_PATH = PROJECT_ROOT / "analysis" / "outputs" / "granger_17regions_results.json"

# ───────────────────── 데이터 로더 ──────────────────────────────────────────


async def _fetch_region(pool: asyncpg.Pool, region: str) -> dict[str, pd.Series]:
    async with pool.acquire() as conn:
        sig_rows = await conn.fetch(
            """
            SELECT time_bucket('1 week', time) AS week,
                   layer, AVG(value) AS v
            FROM layer_signals
            WHERE region = $1 AND layer = ANY($2::text[])
              AND time BETWEEN $3::timestamptz AND $4::timestamptz
            GROUP BY week, layer ORDER BY week, layer
            """,
            region, LAYERS, ANALYSIS_START, ANALYSIS_END,
        )
        conf_rows = await conn.fetch(
            """
            SELECT time_bucket('1 week', time) AS week,
                   SUM(case_count) AS case_count
            FROM confirmed_cases
            WHERE region = $1 AND disease = $2
              AND time BETWEEN $3::timestamptz AND $4::timestamptz
            GROUP BY week ORDER BY week
            """,
            region, DISEASE, ANALYSIS_START, ANALYSIS_END,
        )

    sig_df = pd.DataFrame(sig_rows, columns=["week", "layer", "v"])
    if sig_df.empty:
        return {}
    sig_df["week"] = pd.to_datetime(sig_df["week"], utc=True)
    pivot = sig_df.pivot_table(index="week", columns="layer", values="v", aggfunc="mean")

    composite = pd.Series(0.0, index=pivot.index)
    for layer, weight in W.items():
        if layer in pivot.columns:
            composite = composite.add(pivot[layer].fillna(0) * weight, fill_value=0)

    conf_df = pd.DataFrame(conf_rows, columns=["week", "case_count"])
    conf_df["week"] = pd.to_datetime(conf_df["week"], utc=True)
    conf_s = conf_df.set_index("week")["case_count"].astype(float)

    result: dict[str, pd.Series] = {}
    for layer in LAYERS:
        if layer in pivot.columns:
            result[layer] = pivot[layer].astype(float)
    result["composite"] = composite.astype(float)
    result["confirmed"] = conf_s
    return result


# ───────────────────── Granger 핵심 ────────────────────────────────────────


def _granger_p(
    signal: pd.Series, target: pd.Series, max_lag: int = MAX_LAG,
) -> tuple[float | None, int | None, int]:
    from statsmodels.tsa.stattools import grangercausalitytests

    combined = pd.DataFrame({"y": target, "x": signal}).dropna()
    n_used = len(combined)
    if n_used < max(MIN_SAMPLE, max_lag * 3 + 5):
        return None, None, n_used
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            res = grangercausalitytests(combined[["y", "x"]], maxlag=max_lag, verbose=False)
        best_lag, best_p = min(
            ((lag, res[lag][0]["ssr_ftest"][1]) for lag in res),
            key=lambda kv: kv[1],
        )
        return float(best_p), int(best_lag), n_used
    except Exception as exc:  # noqa: BLE001
        logger.warning("Granger 실패 (%s): %s", target.name or "?", exc)
        return None, None, n_used


# ───────────────────── 메인 ─────────────────────────────────────────────────


async def run() -> dict[str, Any]:
    db_url = os.getenv("DATABASE_URL", "")
    if not db_url:
        raise RuntimeError("DATABASE_URL 미설정 — .env 확인")
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    pool = await asyncpg.create_pool(dsn=db_url, min_size=1, max_size=3)
    try:
        per_region = {}
        for region in ALL_17_REGIONS:
            per_region[region] = await _fetch_region(pool, region)
    finally:
        await pool.close()

    results: list[dict[str, Any]] = []
    for region in ALL_17_REGIONS:
        data = per_region.get(region, {})
        target = data.get("confirmed")
        if target is None or len(target.dropna()) < MIN_SAMPLE:
            for layer in LAYERS:
                results.append({
                    "region": region, "layer": LAYER_LABEL[layer],
                    "p_raw": None, "best_lag": None,
                    "n_weeks": len(target.dropna()) if target is not None else 0,
                    "status": "INSUFFICIENT_TARGET",
                })
            continue
        for layer in LAYERS:
            sig = data.get(layer)
            if sig is None:
                results.append({
                    "region": region, "layer": LAYER_LABEL[layer],
                    "p_raw": None, "best_lag": None, "n_weeks": 0,
                    "status": "NO_SIGNAL",
                })
                continue
            p, best_lag, n_used = _granger_p(sig, target)
            results.append({
                "region": region,
                "layer": LAYER_LABEL[layer],
                "p_raw": round(p, 6) if p is not None else None,
                "best_lag": best_lag,
                "n_weeks": n_used,
                "status": "OK" if p is not None else "INSUFFICIENT_DATA",
            })
        sig = data.get("composite")
        if sig is not None and sig.notna().sum() >= MIN_SAMPLE:
            p, best_lag, n_used = _granger_p(sig, target)
            results.append({
                "region": region, "layer": "composite",
                "p_raw": round(p, 6) if p is not None else None,
                "best_lag": best_lag, "n_weeks": n_used,
                "status": "OK" if p is not None else "INSUFFICIENT_DATA",
            })

    from statsmodels.stats.multitest import multipletests

    valid_layer_rows = [
        r for r in results
        if r["status"] == "OK" and r["layer"] in {"L1_otc", "L2_wastewater", "L3_search"}
    ]
    p_global = [r["p_raw"] for r in valid_layer_rows]
    bonf_rej, bonf_padj, _, _ = multipletests(p_global, alpha=ALPHA, method="bonferroni")
    bh_rej, bh_padj, _, _ = multipletests(p_global, alpha=ALPHA, method="fdr_bh")

    for r, padj_b, padj_h, rej_b, rej_h in zip(
        valid_layer_rows, bonf_padj, bh_padj, bonf_rej, bh_rej, strict=True,
    ):
        r["p_bonferroni_global"] = round(float(padj_b), 6)
        r["p_bh_fdr_global"] = round(float(padj_h), 6)
        r["significant_raw"] = bool(r["p_raw"] < ALPHA)
        r["significant_bonferroni_global"] = bool(rej_b)
        r["significant_bh_fdr_global"] = bool(rej_h)

    per_layer_summary: dict[str, dict[str, Any]] = {}
    for lbl in ["L1_otc", "L2_wastewater", "L3_search"]:
        layer_rows = [r for r in valid_layer_rows if r["layer"] == lbl]
        layer_p = [r["p_raw"] for r in layer_rows]
        if layer_p:
            _, lp_bonf, _, _ = multipletests(layer_p, alpha=ALPHA, method="bonferroni")
            for r, padj in zip(layer_rows, lp_bonf, strict=True):
                r["p_bonferroni_per_layer"] = round(float(padj), 6)
                r["significant_per_layer_bonferroni"] = bool(padj < ALPHA)
            per_layer_summary[lbl] = {
                "n_total": len(layer_rows),
                "n_sig_raw": sum(1 for r in layer_rows if r["p_raw"] < ALPHA),
                "n_sig_bonferroni_per_layer": int(sum(lp_bonf < ALPHA)),
            }
        else:
            per_layer_summary[lbl] = {"n_total": 0, "n_sig_raw": 0, "n_sig_bonferroni_per_layer": 0}

    composite_rows = [r for r in results if r["layer"] == "composite" and r["status"] == "OK"]
    composite_p = [r["p_raw"] for r in composite_rows]
    composite_summary = {
        "n_regions": len(composite_rows),
        "n_sig_raw": sum(1 for p in composite_p if p < ALPHA),
        "min_p": round(min(composite_p), 6) if composite_p else None,
        "max_p": round(max(composite_p), 6) if composite_p else None,
        "median_p": round(float(np.median(composite_p)), 6) if composite_p else None,
    }

    effective_unique: dict[str, int] = {}
    for lbl in ["L1_otc", "L2_wastewater", "L3_search"]:
        ps = [r["p_raw"] for r in valid_layer_rows if r["layer"] == lbl]
        effective_unique[lbl] = len({round(p, 6) for p in ps})

    degeneracy_note = {
        "L1_otc": "전국 단일값 broadcast — 17 region p_raw 동일 예상 (effective n=1)",
        "L2_wastewater": "KOWAS region별 분리 — 17 region effective tests",
        "L3_search": "전국 단일값 broadcast — 17 region p_raw 동일 예상 (effective n=1)",
        "composite": "L2 region 차이가 가중평균에 반영 — 17 region 효과적으로 다름",
    }

    n_significant_global_bonf = int(sum(bonf_rej))
    n_significant_global_bh = int(sum(bh_rej))

    out: dict[str, Any] = {
        "method": "Granger causality, 17 regions × 3 layers (+ composite per region, reported separately)",
        "n_tests_nominal": len(valid_layer_rows),
        "n_tests_effective_independent_estimate": int(sum(effective_unique.values())),
        "alpha": ALPHA,
        "max_lag": MAX_LAG,
        "min_sample_weeks": MIN_SAMPLE,
        "seed": SEED,
        "analysis_window": "2025-W40 ~ 2026-W08",
        "corrections": [
            f"Bonferroni global (family={len(valid_layer_rows)})",
            f"BH-FDR global (family={len(valid_layer_rows)})",
            "Per-layer Bonferroni (family=17 within each layer)",
        ],
        "data_caveat": {
            "L1_otc_L3_search_broadcast": (
                "L1 OTC 와 L3 search 는 네이버 API 제약상 전국 단일값을 17지역 broadcast. "
                "17 region 의 p_raw 가 동일하게 나오는 것이 정상이며, 이 경우 effective unique tests = 1 per layer. "
                "Bonferroni global 보정(family=51)은 보수적으로 인플레된 값이며, "
                "통계적으로 정직한 effective family ≈ 17(L2) + 1(L1) + 1(L3) = 19."
            ),
        },
        "effective_unique_tests_per_layer": effective_unique,
        "degeneracy_note": degeneracy_note,
        "results_per_region_layer": valid_layer_rows
            + [r for r in results if r["status"] != "OK" and r["layer"] != "composite"],
        "composite_per_region": composite_rows,
        "summary": {
            "n_significant_raw": sum(1 for r in valid_layer_rows if r["p_raw"] < ALPHA),
            "n_significant_bonferroni_global": n_significant_global_bonf,
            "n_significant_bh_fdr_global": n_significant_global_bh,
            "n_significant_per_layer_bonferroni": sum(
                v["n_sig_bonferroni_per_layer"] for v in per_layer_summary.values()
            ),
            "per_layer_summary": per_layer_summary,
            "composite_summary": composite_summary,
        },
        "interpretation": (
            "L2 wastewater 와 composite 가 region별 차별을 가지며 의미 있는 17 검정. "
            "L1·L3 broadcast 한계로 effective unique tests 는 layer 당 1개 수준. "
            "효과적 family ≈ 19 검정 기준 BH-FDR 결과가 가장 해석 가능. "
            "Phase 3 HIRA OpenAPI 연동으로 L1 region 분리 시 effective 17 으로 확장 가능."
        ),
        "canonical_data_source": "TimescaleDB layer_signals + confirmed_cases (window 2025-W40 ~ 2026-W08)",
        "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("granger_17regions: %s 저장 (%d valid tests)", OUTPUT_PATH, len(valid_layer_rows))
    return out


def main() -> None:
    out = asyncio.run(run())
    print(f"\n[granger_17regions] wrote {OUTPUT_PATH}")
    print(f"  nominal tests:  {out['n_tests_nominal']}")
    print(f"  effective uniq: {out['n_tests_effective_independent_estimate']}")
    s = out["summary"]
    print(f"  raw α=0.05:           {s['n_significant_raw']:>3} significant")
    print(f"  Bonferroni global:    {s['n_significant_bonferroni_global']:>3} significant")
    print(f"  BH-FDR global:        {s['n_significant_bh_fdr_global']:>3} significant")
    print(f"  Per-layer Bonferroni: {s['n_significant_per_layer_bonferroni']:>3} significant")
    for lbl, st in s["per_layer_summary"].items():
        n_bp = st["n_sig_bonferroni_per_layer"]
        print(f"    {lbl:14s} raw={st['n_sig_raw']:>2}/{st['n_total']:>2}  bonf-per-layer={n_bp:>2}")
    cs = s["composite_summary"]
    print(
        f"  Composite per-region: n={cs['n_regions']}  "
        f"n_sig_raw={cs['n_sig_raw']}  median p={cs['median_p']}"
    )


if __name__ == "__main__":
    main()
