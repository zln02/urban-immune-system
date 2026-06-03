"""다질병 XGBoost self-target proxy backtest — pathogen 인자화 + 피처 고도화.

기존 backtest_xgboost_covid.py 보다 개선된 점:
  - DATA 범위: 2025-06 ~ 2026-06 (53주) 전체 활용 (기존: 2026-01 이후 13주만)
  - 피처: L2_t, L2_lag1, L2_lag2, L2_MA3, L2_diff1, L3_t, L3_lag1, L3_MA3
  - region별 walk-forward 우선, 부족하면 pool
  - covid + norovirus 동일 로직 generic 처리
  - 모델: GradientBoosting (sklearn) — sklearn-내장으로 의존성 최소

타깃: L2(t+LEAD_WEEKS) ≥ 임계 (pathogen별 분포 기준)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import (
    average_precision_score,
    confusion_matrix,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
)
from sklearn.model_selection import TimeSeriesSplit

_main_repo = Path("/home/wlsdud5035/urban-immune-system")
load_dotenv(_main_repo / ".env", override=False)

logger = logging.getLogger(__name__)

LEAD_WEEKS = 2

DEFAULT_THRESHOLDS = {
    "covid": 32.0,
    "norovirus": 30.0,
    "influenza": 70.0,
}


async def _fetch_signals(db_url: str, pathogen: str) -> pd.DataFrame:
    import asyncpg
    conn = await asyncpg.connect(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        rows = await conn.fetch(
            """
            SELECT time, region, layer, value
            FROM layer_signals
            WHERE pathogen = $1 AND layer IN ('wastewater', 'search')
            ORDER BY region, time, layer
            """,
            pathogen,
        )
    finally:
        await conn.close()

    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        raise RuntimeError(f"{pathogen} 신호 없음")

    df["isoweek"] = df["time"].apply(lambda t: t.isocalendar()[1])
    df["isoyear"] = df["time"].apply(lambda t: t.isocalendar()[0])
    wide = df.pivot_table(
        index=["isoyear", "isoweek", "region"],
        columns="layer", values="value", aggfunc="mean",
    ).reset_index()
    wide = wide.rename(columns={"wastewater": "l2_wastewater", "search": "l3_search"})

    wide = wide.sort_values(["region", "isoyear", "isoweek"]).reset_index(drop=True)
    for col in ["l2_wastewater", "l3_search"]:
        if col not in wide.columns:
            wide[col] = np.nan
        wide[col] = wide.groupby("region")[col].transform(lambda s: s.ffill().bfill())

    wide["time"] = pd.to_datetime(
        wide["isoyear"].astype(str) + "-W" + wide["isoweek"].astype(str).str.zfill(2) + "-1",
        format="%G-W%V-%u", utc=True,
    )
    return wide[["time", "region", "l2_wastewater", "l3_search"]].sort_values(
        ["region", "time"]
    ).reset_index(drop=True)


def _build_features(df: pd.DataFrame, threshold: float) -> tuple[pd.DataFrame, list[str]]:
    out = []
    for region, g in df.groupby("region"):
        g = g.sort_values("time").reset_index(drop=True)
        if len(g) < LEAD_WEEKS + 6:
            continue
        g["l2_future"] = g["l2_wastewater"].shift(-LEAD_WEEKS)
        g["alert_future"] = (g["l2_future"] >= threshold).astype(int)
        g["l2_lag1"] = g["l2_wastewater"].shift(1)
        g["l2_lag2"] = g["l2_wastewater"].shift(2)
        g["l2_ma3"] = g["l2_wastewater"].rolling(window=3, min_periods=1).mean()
        g["l2_diff1"] = g["l2_wastewater"].diff(1)
        g["l3_lag1"] = g["l3_search"].shift(1)
        g["l3_ma3"] = g["l3_search"].rolling(window=3, min_periods=1).mean()
        out.append(g)
    if not out:
        raise RuntimeError("모든 region 데이터 부족")
    features = [
        "l2_wastewater", "l2_lag1", "l2_lag2", "l2_ma3", "l2_diff1",
        "l3_search", "l3_lag1", "l3_ma3",
    ]
    return pd.concat(out, ignore_index=True), features


def _metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray | None) -> dict:
    if len(y_true) == 0:
        return {"n": 0}
    n_pos = int(y_true.sum())
    n_neg = int(len(y_true) - n_pos)
    if n_pos == 0 or n_neg == 0:
        return {"n": int(len(y_true)), "n_pos": n_pos, "n_neg": n_neg,
                "f1": None, "skipped_reason": "single_class"}
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    far = fp / (fp + tn) if (fp + tn) > 0 else 0.0
    return {
        "n": int(len(y_true)),
        "n_pos": n_pos,
        "n_neg": n_neg,
        "f1": round(float(f1_score(y_true, y_pred, zero_division=0)), 4),
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "false_alarm_rate": round(float(far), 4),
        "mcc": round(float(matthews_corrcoef(y_true, y_pred)), 4),
        "auprc": (round(float(average_precision_score(y_true, y_prob)), 4)
                  if y_prob is not None else None),
        "confusion_matrix": {"TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn)},
    }


def _walk_forward(g: pd.DataFrame, features: list[str], min_n: int = 20,
                  n_estimators: int = 100, max_depth: int = 3,
                  prob_threshold: float = 0.5) -> dict:
    valid = g.dropna(subset=features + ["alert_future"]).reset_index(drop=True)
    if len(valid) < min_n:
        return {"status": "skipped", "reason": f"n={len(valid)} (need ≥{min_n})"}

    X = valid[features].values
    y = valid["alert_future"].values.astype(int)

    n_splits = min(5, max(2, len(valid) // 6))
    tscv = TimeSeriesSplit(n_splits=n_splits, gap=2)

    all_true, all_pred, all_prob = [], [], []
    for tr_idx, te_idx in tscv.split(X):
        if len(set(y[tr_idx])) < 2:
            continue
        clf = GradientBoostingClassifier(
            n_estimators=n_estimators, max_depth=max_depth,
            learning_rate=0.05, random_state=42,
        )
        clf.fit(X[tr_idx], y[tr_idx])
        prob = clf.predict_proba(X[te_idx])[:, 1]
        pred = (prob >= prob_threshold).astype(int)
        all_true.extend(y[te_idx].tolist())
        all_pred.extend(pred.tolist())
        all_prob.extend(prob.tolist())

    if not all_true:
        return {"status": "skipped", "reason": "all folds single-class"}
    return {"status": "ok", "n_folds_used": n_splits,
            **_metrics(np.array(all_true), np.array(all_pred), np.array(all_prob))}


async def run_pathogen(pathogen: str, threshold: float, db_url: str,
                       prob_threshold: float = 0.5) -> dict:
    logger.info("=== %s backtest (alert=%s, prob=%s, lead=%d주) ===",
                pathogen, threshold, prob_threshold, LEAD_WEEKS)
    raw = await _fetch_signals(db_url, pathogen)
    logger.info("DataFrame: %d행 × %d지역, 기간 %s ~ %s",
                len(raw), raw["region"].nunique(), raw["time"].min(), raw["time"].max())

    df_feat, features = _build_features(raw, threshold)
    pos_rate = float(df_feat["alert_future"].mean())
    logger.info("피처 빌드: %d행, 피처 %d개, 양성 비율=%.2f%%",
                len(df_feat), len(features), pos_rate * 100)

    region_results: dict[str, dict] = {}
    for region in sorted(df_feat["region"].unique()):
        g = df_feat[df_feat["region"] == region]
        region_results[region] = _walk_forward(g, features, prob_threshold=prob_threshold)

    ok_regions = [r for r, m in region_results.items() if m.get("status") == "ok"]
    logger.info("region별 학습 성공: %d/%d", len(ok_regions), len(region_results))

    pool = df_feat.dropna(subset=features + ["alert_future"]).reset_index(drop=True)
    pool = pool.sort_values("time").reset_index(drop=True)
    pool["region_code"] = pool["region"].astype("category").cat.codes
    pool_features = features + ["region_code"]
    n_pool = len(pool)
    pool_pos_rate = float(pool["alert_future"].mean()) if n_pool > 0 else 0.0
    logger.info("Pool: n=%d, 양성 비율=%.2f%%", n_pool, pool_pos_rate * 100)

    # weekly group CV: 같은 주차 17지역은 같은 fold (leakage 방지)
    weeks_sorted = sorted(pool["time"].unique())
    n_weeks = len(weeks_sorted)
    pool_result: dict = {}
    if n_pool >= 50 and 0.05 <= pool_pos_rate <= 0.95 and n_weeks >= 30:
        fold_w = max(4, n_weeks // 6)
        all_true, all_pred, all_prob = [], [], []
        train_end = fold_w
        n_folds_used = 0
        while True:
            test_start = train_end + 2  # gap 2주
            test_end = test_start + fold_w
            if test_end > n_weeks:
                break
            tr_mask = pool["time"].isin(weeks_sorted[:train_end])
            te_mask = pool["time"].isin(weeks_sorted[test_start:test_end])
            X_tr = pool.loc[tr_mask, pool_features].values
            y_tr = pool.loc[tr_mask, "alert_future"].values.astype(int)
            X_te = pool.loc[te_mask, pool_features].values
            y_te = pool.loc[te_mask, "alert_future"].values.astype(int)
            train_end += fold_w
            if len(set(y_tr)) < 2 or len(y_te) == 0:
                continue
            clf = GradientBoostingClassifier(
                n_estimators=200, max_depth=4,
                learning_rate=0.05, random_state=42,
            )
            clf.fit(X_tr, y_tr)
            prob = clf.predict_proba(X_te)[:, 1]
            pred = (prob >= prob_threshold).astype(int)
            all_true.extend(y_te.tolist())
            all_pred.extend(pred.tolist())
            all_prob.extend(prob.tolist())
            n_folds_used += 1
        if all_true:
            pool_result = {
                "status": "ok",
                "cv": f"Weekly group CV n_folds={n_folds_used}, gap=2주 (leakage-free)",
                "n_folds_used": n_folds_used,
                **_metrics(np.array(all_true), np.array(all_pred), np.array(all_prob)),
            }
        else:
            pool_result = {"status": "skipped", "reason": "all folds single-class"}
    else:
        pool_result = {
            "status": "skipped",
            "reason": f"n={n_pool}, n_weeks={n_weeks}, pos_rate={pool_pos_rate:.3f}",
        }

    # ─── trivial baselines (proxy 라벨 한계 노출용 정직성 메트릭) ───
    full = df_feat.dropna(subset=["l2_wastewater", "l2_ma3", "alert_future"]).copy()
    y_full = full["alert_future"].values.astype(int)
    baselines: dict[str, dict] = {}
    for name, pred_vec in [
        ("trivial_L2_t",   (full["l2_wastewater"].values >= threshold).astype(int)),
        ("trivial_L2_MA3", (full["l2_ma3"].values >= threshold).astype(int)),
        ("trivial_L2_lag2", (full["l2_lag2"].fillna(0).values >= threshold).astype(int)
            if "l2_lag2" in full.columns else None),
    ]:
        if pred_vec is None:
            continue
        baselines[name] = _metrics(y_full, pred_vec, None)
    logger.info("Trivial baselines:")
    for k, v in baselines.items():
        if "f1" in v and v["f1"] is not None:
            logger.info("  %-18s F1=%.3f FAR=%.3f", k, v["f1"], v["false_alarm_rate"])

    def avg_key(key: str) -> float | None:
        vals = [region_results[r][key] for r in ok_regions
                if region_results[r].get(key) is not None]
        return round(float(np.mean(vals)), 4) if vals else None

    # 모델 우위 계산 (vs best trivial)
    best_trivial_f1 = max(
        (v.get("f1") for v in baselines.values() if v.get("f1") is not None),
        default=None,
    )
    pool_f1 = pool_result.get("f1")
    model_gain_vs_trivial = (
        round(pool_f1 - best_trivial_f1, 4)
        if (pool_f1 is not None and best_trivial_f1 is not None) else None
    )

    summary = {
        "pathogen": pathogen,
        "alert_threshold": threshold,
        "lead_weeks": LEAD_WEEKS,
        "n_total_regions": len(region_results),
        "n_ok_regions": len(ok_regions),
        "pool_status": pool_result.get("status"),
        "pool_n": pool_result.get("n"),
        "pool_n_pos": pool_result.get("n_pos"),
        "pool_f1": pool_f1,
        "pool_precision": pool_result.get("precision"),
        "pool_recall": pool_result.get("recall"),
        "pool_far": pool_result.get("false_alarm_rate"),
        "pool_mcc": pool_result.get("mcc"),
        "pool_auprc": pool_result.get("auprc"),
        "mean_f1_per_region": avg_key("f1"),
        "mean_recall_per_region": avg_key("recall"),
        "mean_far_per_region": avg_key("false_alarm_rate"),
        "mean_mcc_per_region": avg_key("mcc"),
        # 정직성: trivial baseline 대비 모델 우위
        "best_trivial_name": (
            max(baselines.items(), key=lambda kv: kv[1].get("f1") or 0)[0]
            if baselines else None
        ),
        "best_trivial_f1": best_trivial_f1,
        "best_trivial_far": (
            baselines.get(max(baselines.items(), key=lambda kv: kv[1].get("f1") or 0)[0], {}).get("false_alarm_rate")
            if baselines else None
        ),
        "model_gain_vs_trivial_f1": model_gain_vs_trivial,
    }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": f"{pathogen} self-target proxy backtest (확장된 53주 데이터)",
        "config": {
            "pathogen": pathogen,
            "features": features,
            "target": f"L2 KOWAS {pathogen}(t+{LEAD_WEEKS}주) ≥ {threshold}",
            "model_region": "GradientBoostingClassifier (n=100, depth=3, lr=0.05)",
            "model_pool": "GradientBoostingClassifier (n=200, depth=4, lr=0.05)",
            "cv_region": "TimeSeriesSplit n_splits<=5, gap=2 (region-internal)",
            "cv_pool": "Weekly group CV (같은 주차 17지역 = 같은 fold, gap=2주, leakage-free)",
            "alert_threshold": threshold,
            "prob_threshold": prob_threshold,
            "lead_weeks": LEAD_WEEKS,
        },
        "data_summary": {
            "n_rows": int(len(df_feat)),
            "n_regions": int(df_feat["region"].nunique()),
            "alert_future_positive_rate": round(pos_rate, 4),
            "date_range": [str(raw["time"].min().date()), str(raw["time"].max().date())],
        },
        "summary": summary,
        "pool_result": pool_result,
        "baselines": baselines,
        "regions": region_results,
        "honesty_note": (
            "self-target proxy 라벨 (L2 t+2주 값)은 L2(t)와 강한 자기상관을 가져 "
            "단순 임계 비교(trivial baseline)가 ML 모델보다 좋을 수 있음. "
            "외부 임상 데이터(KDCA 확진자) 연동 시 ML 우위 회복 예상. "
            "CV는 weekly group split (같은 주차 17지역은 같은 fold, leakage-free)."
        ),
    }


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pathogen", required=True, choices=["covid", "norovirus", "influenza"])
    parser.add_argument("--threshold", type=float, default=None)
    parser.add_argument("--prob", type=float, default=0.5, help="classification probability threshold")
    parser.add_argument("--output", type=str, default=None)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    threshold = args.threshold if args.threshold is not None else DEFAULT_THRESHOLDS[args.pathogen]
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        logger.error("DATABASE_URL 환경변수 없음")
        return 2

    result = await run_pathogen(args.pathogen, threshold, db_url, prob_threshold=args.prob)

    out = (Path(args.output) if args.output else
           Path(__file__).parent / "outputs" / f"backtest_xgboost_{args.pathogen}_17regions.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    logger.info("저장: %s", out)

    print(f"\n=== {args.pathogen} backtest summary ===")
    print(json.dumps(result["summary"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
