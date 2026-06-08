"""XGBoost COVID-19 self-target proxy backtest — 17지역 walk-forward.

배경:
  KDCA COVID 확진자 timeseries가 DB에 미연동 → 인플루엔자처럼 supervised 학습 불가.
  대안: L2 KOWAS COVID(t+2주) 자체를 라벨로 사용 ("자체 시그널 선행성" 검증).
  → 의미는 다름: 인플루엔자는 KDCA peak 대비 외부 검증, COVID는 L2 자체 미래값 예측.

피처: L2(t) + L3(t) + temperature(t)  (L1 OTC는 인플루엔자 전용 카테고리라 제외)
타깃: L2 KOWAS COVID(t+2주) ≥ COVID_ALERT_THRESHOLD (이진 분류)

산출:
  - analysis/outputs/backtest_xgboost_covid_17regions.json
  - 17지역 walk-forward 5-fold gap=4주
  - 메트릭: F1, Precision, Recall, FAR, MCC, AUPRC

발표 정직성:
  "COVID는 KDCA confirmed 데이터 미연동 → KOWAS self-target proxy로 자체 시그널
   선행성 검증만 수행. 외부 임상 검증은 KDCA 데이터 연동 후 P0."
"""

from __future__ import annotations

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

# 임계: L2 KOWAS COVID 값이 32 이상 = outbreak (실측 분포 p75 ≈ 32.11 기준)
# 인플루엔자는 70 사용하지만 COVID는 분포 다름 (p95=55.49). p75를 임계로 → 양성 ~25%
COVID_ALERT_THRESHOLD = 32.0
LEAD_WEEKS = 2  # t+2주 후 outbreak 예측

# 데이터 부족 (region당 13주) → region-pooled 학습 사용
# region을 categorical feature(one-hot)로 추가

OUTPUT_PATH = Path(__file__).parent / "outputs" / "backtest_xgboost_covid_17regions.json"


async def _fetch_covid_signals(db_url: str) -> pd.DataFrame:
    """DB에서 COVID 17지역 시계열 + temperature wide-format DataFrame."""
    import asyncpg

    conn = await asyncpg.connect(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        # L2 KOWAS COVID + L3 search COVID + weather (전역) join
        rows = await conn.fetch(
            """
            SELECT time, region, layer, value
            FROM layer_signals
            WHERE pathogen IN ('covid', 'influenza')
              AND layer IN ('wastewater', 'search', 'weather')
              AND time >= '2026-01-01'
            ORDER BY region, time, layer
            """
        )
    finally:
        await conn.close()

    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        raise RuntimeError("DB에 COVID 신호 없음 — naver_backfill --pathogen covid 먼저 실행")

    # weather는 pathogen=influenza로만 적재 (AUX). COVID 신호와 join.
    weather = df[df["layer"] == "weather"][["time", "region", "value"]].rename(
        columns={"value": "temperature"}
    )
    covid = df[df["layer"].isin(["wastewater", "search"])].pivot_table(
        index=["time", "region"], columns="layer", values="value", aggfunc="mean"
    ).reset_index()
    covid = covid.rename(columns={"wastewater": "l2_wastewater", "search": "l3_search"})

    merged = covid.merge(weather, on=["time", "region"], how="left")
    merged["temperature"] = merged["temperature"].fillna(20.0)  # 기상 결측 평균값
    merged = merged.sort_values(["region", "time"]).reset_index(drop=True)
    return merged


def _build_features(df: pd.DataFrame) -> pd.DataFrame:
    """region별 t+LEAD주 후 라벨 + 피처 정렬."""
    out = []
    for region, g in df.groupby("region"):
        g = g.sort_values("time").reset_index(drop=True)
        if len(g) < LEAD_WEEKS + 5:
            logger.warning("%s: 데이터 부족 (n=%d) → skip", region, len(g))
            continue
        g["l2_future"] = g["l2_wastewater"].shift(-LEAD_WEEKS)
        g["alert_future"] = (g["l2_future"] >= COVID_ALERT_THRESHOLD).astype(int)
        g["time_idx"] = np.arange(len(g))
        out.append(g)
    if not out:
        raise RuntimeError("모든 region 데이터 부족")
    return pd.concat(out, ignore_index=True)


def _metrics(y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray | None) -> dict:
    """이진 분류 메트릭. y_pred는 hard label (0/1), y_prob은 확률 [0,1]."""
    if len(y_true) == 0:
        return {"n": 0}
    n_pos = int(y_true.sum())
    n_neg = int(len(y_true) - n_pos)
    if n_pos == 0 or n_neg == 0:
        # 단일 클래스 → 메트릭 정의 불가, NaN 보고
        return {
            "n": int(len(y_true)),
            "n_pos": n_pos,
            "n_neg": n_neg,
            "f1": None,
            "precision": None,
            "recall": None,
            "skipped_reason": "single_class",
        }
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
        "auprc": (
            round(float(average_precision_score(y_true, y_prob)), 4)
            if y_prob is not None else None
        ),
        "confusion_matrix": {"TP": int(tp), "FP": int(fp), "FN": int(fn), "TN": int(tn)},
    }


def _walk_forward_region(g: pd.DataFrame, features: list[str]) -> dict:
    """단일 region walk-forward 5-fold gap=4주."""
    valid = g.dropna(subset=features + ["alert_future"]).reset_index(drop=True)
    if len(valid) < 14:
        return {"status": "skipped", "reason": f"n={len(valid)} (need ≥14)"}

    X = valid[features].values
    y = valid["alert_future"].values.astype(int)

    n_splits = min(5, max(2, len(valid) // 5))
    tscv = TimeSeriesSplit(n_splits=n_splits, gap=4)

    all_true, all_pred, all_prob = [], [], []
    for tr_idx, te_idx in tscv.split(X):
        # 단일 클래스 fold 회피
        if len(set(y[tr_idx])) < 2:
            continue
        clf = GradientBoostingClassifier(
            n_estimators=80, max_depth=3, learning_rate=0.1, random_state=42
        )
        clf.fit(X[tr_idx], y[tr_idx])
        prob = clf.predict_proba(X[te_idx])[:, 1]
        pred = (prob >= 0.5).astype(int)
        all_true.extend(y[te_idx].tolist())
        all_pred.extend(pred.tolist())
        all_prob.extend(prob.tolist())

    if not all_true:
        return {"status": "skipped", "reason": "all folds single-class"}

    return {
        "status": "ok",
        "n_folds_used": n_splits,
        **_metrics(np.array(all_true), np.array(all_pred), np.array(all_prob)),
    }


async def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        logger.error("DATABASE_URL 환경변수 없음")
        return 2

    logger.info("COVID 신호 로드 중...")
    raw = await _fetch_covid_signals(db_url)
    # pathogen 정보 없으므로 wastewater는 covid·influenza 둘 다 있을 수 있음 → COVID만 필터링 필요
    # 위 SELECT에서 covid+influenza 둘 다 가져왔음 → 여기서 분리
    # 정확히 분리하려면 SELECT에 pathogen도 가져와야 함. 재쿼리.

    import asyncpg
    conn = await asyncpg.connect(db_url.replace("postgresql+asyncpg://", "postgresql://"))
    try:
        rows = await conn.fetch(
            """
            SELECT time, region, layer, value
            FROM layer_signals
            WHERE pathogen = 'covid' AND layer IN ('wastewater', 'search')
              AND time >= '2026-01-01'
            ORDER BY region, time, layer
            """
        )
    finally:
        await conn.close()

    df = pd.DataFrame([dict(r) for r in rows])
    if df.empty:
        raise RuntimeError("COVID 신호 없음")
    # L2 wastewater(화요일)와 L3 search(월요일) timestamp 불일치 → ISO week 기준 정렬
    df["isoweek"] = df["time"].apply(lambda t: t.isocalendar()[1])
    df["isoyear"] = df["time"].apply(lambda t: t.isocalendar()[0])
    covid = df.pivot_table(
        index=["isoyear", "isoweek", "region"], columns="layer", values="value", aggfunc="mean"
    ).reset_index()
    covid = covid.rename(columns={"wastewater": "l2_wastewater", "search": "l3_search"})
    # region별 forward-fill (L2 또는 L3 한쪽만 있는 주차 보완)
    covid = covid.sort_values(["region", "isoyear", "isoweek"]).reset_index(drop=True)
    for col in ["l2_wastewater", "l3_search"]:
        if col not in covid.columns:
            covid[col] = np.nan
        covid[col] = covid.groupby("region")[col].transform(lambda s: s.ffill().bfill())
    # 가짜 time 컬럼: isoweek 시작 (월요일) 추정 — 후속 처리 호환용
    covid["time"] = pd.to_datetime(
        covid["isoyear"].astype(str) + "-W" + covid["isoweek"].astype(str).str.zfill(2) + "-1",
        format="%G-W%V-%u", utc=True,
    )
    # temperature는 COVID DB에 미적재 → 상수 20.0으로 채움 (피처에서 제거 권장)
    covid["temperature"] = 20.0
    merged = covid[["time", "region", "l2_wastewater", "l3_search", "temperature"]]
    merged = merged.sort_values(["region", "time"]).reset_index(drop=True)

    logger.info("DataFrame: %d행 × %d지역", len(merged), merged["region"].nunique())
    if "l2_wastewater" not in merged.columns or "l3_search" not in merged.columns:
        logger.error("필수 컬럼 누락: %s", list(merged.columns))
        return 3

    df_feat = _build_features(merged)
    logger.info("피처 빌드 완료: %d행, alert_future 양성 비율=%.2f%%",
                len(df_feat), df_feat["alert_future"].mean() * 100)

    # temperature는 COVID DB에 미적재 → 피처에서 제외 (l2/l3만 사용)
    features = ["l2_wastewater", "l3_search"]
    region_results = {}

    # region별 walk-forward (best effort, 데이터 부족하면 skip)
    for region in sorted(df_feat["region"].unique()):
        g = df_feat[df_feat["region"] == region]
        res = _walk_forward_region(g, features)
        region_results[region] = res

    # ─── Region-pooled 학습 (데이터 부족 보완) ───────────────────────────
    # region별 13주 데이터 부족 → 모든 지역 합쳐 단일 모델 학습.
    # region은 categorical feature(label encoded)로 추가.
    pool = df_feat.dropna(subset=features + ["alert_future"]).reset_index(drop=True)
    # time_idx 재정렬 (region 무관 시간순)
    pool = pool.sort_values("time").reset_index(drop=True)
    pool["region_code"] = pool["region"].astype("category").cat.codes
    pool_features = features + ["region_code"]
    X_pool = pool[pool_features].values
    y_pool = pool["alert_future"].values.astype(int)
    n_pool = len(pool)
    pos_rate = float(y_pool.mean()) if n_pool > 0 else 0.0
    logger.info("Pool: n=%d, 양성 비율=%.2f%%", n_pool, pos_rate * 100)

    pool_result = {}
    if n_pool >= 50 and 0.05 <= pos_rate <= 0.95:
        tscv = TimeSeriesSplit(n_splits=5, gap=4)
        all_true, all_pred, all_prob = [], [], []
        for tr_idx, te_idx in tscv.split(X_pool):
            if len(set(y_pool[tr_idx])) < 2 or len(set(y_pool[te_idx])) < 2:
                continue
            clf = GradientBoostingClassifier(
                n_estimators=100, max_depth=3, learning_rate=0.1, random_state=42
            )
            clf.fit(X_pool[tr_idx], y_pool[tr_idx])
            prob = clf.predict_proba(X_pool[te_idx])[:, 1]
            pred = (prob >= 0.5).astype(int)
            all_true.extend(y_pool[te_idx].tolist())
            all_pred.extend(pred.tolist())
            all_prob.extend(prob.tolist())
        if all_true:
            pool_result = {
                "status": "ok",
                "cv": "TimeSeriesSplit n_splits=5, gap=4",
                **_metrics(np.array(all_true), np.array(all_pred), np.array(all_prob)),
            }
        else:
            pool_result = {"status": "skipped", "reason": "all folds had single class"}
    else:
        pool_result = {"status": "skipped",
                       "reason": f"n={n_pool} (need ≥50) or pos_rate={pos_rate:.3f}"}

    # summary: pool 우선, region 평균 보조
    ok_regions = [r for r, m in region_results.items() if m.get("status") == "ok"
                  and m.get("f1") is not None]
    if pool_result.get("status") == "ok":
        summary = {
            "primary_evaluation": "region_pooled",
            "note": "데이터 부족(region당 13주)으로 region-pooled 단일 모델 학습. region_code는 categorical feature.",
            "pooled_f1": pool_result.get("f1"),
            "pooled_precision": pool_result.get("precision"),
            "pooled_recall": pool_result.get("recall"),
            "pooled_far": pool_result.get("false_alarm_rate"),
            "pooled_mcc": pool_result.get("mcc"),
            "pooled_auprc": pool_result.get("auprc"),
            "pooled_n": pool_result.get("n"),
            "pooled_n_pos": pool_result.get("n_pos"),
            "n_ok_regions_individual": len(ok_regions),
            "n_total_regions": len(region_results),
        }
        if ok_regions:
            def avg(key: str) -> float | None:
                vals = [region_results[r][key] for r in ok_regions
                        if region_results[r].get(key) is not None]
                return round(float(np.mean(vals)), 4) if vals else None
            summary["mean_f1_per_region"] = avg("f1")
            summary["mean_recall_per_region"] = avg("recall")
    else:
        summary = {
            "primary_evaluation": "failed",
            "pool_status": pool_result,
            "n_ok_regions_individual": len(ok_regions),
            "note": "데이터 부족 — KDCA COVID 확진자 연동 후 정식 학습 권장",
        }

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "COVID-19 self-target proxy backtest — KDCA confirmed 미연동, L2 KOWAS COVID(t+2주) 라벨",
        "pool_result": pool_result,
        "honesty_note": (
            "인플루엔자 backtest와 의미가 다름: 인플루엔자=KDCA peak 외부 검증, "
            "COVID=L2 KOWAS 자체 시그널 선행성 (내부 검증). "
            "외부 임상 검증은 KDCA COVID 데이터 연동 후 P0."
        ),
        "config": {
            "pathogen": "covid",
            "features": features,
            "target": f"L2 KOWAS COVID(t+{LEAD_WEEKS}주) ≥ {COVID_ALERT_THRESHOLD}",
            "model": "GradientBoostingClassifier (n_est=80, max_depth=3)",
            "cv": "TimeSeriesSplit n_splits=5, gap=4",
            "alert_threshold": COVID_ALERT_THRESHOLD,
            "lead_weeks": LEAD_WEEKS,
        },
        "data_summary": {
            "n_rows": int(len(df_feat)),
            "n_regions": int(df_feat["region"].nunique()),
            "alert_future_positive_rate": round(float(df_feat["alert_future"].mean()), 4),
        },
        "summary": summary,
        "regions": region_results,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    logger.info("결과 저장: %s", OUTPUT_PATH)
    print("\n=== COVID backtest 결과 ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
