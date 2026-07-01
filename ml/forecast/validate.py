"""시즌 단위 walk-forward 백테스트 — 실 임상(CDC ILINet) 정답 대비 검증.

검증 시즌 S 는 season<S 데이터로만 학습(baseline·climatology 포함 누수 차단).
산출 메트릭:
- 회귀: MAE/RMSE + persistence·climatology 대비 skill(1 - MAE/MAE_base)
- 확률예측: WIS(weighted interval score), 95% 구간 coverage
- 조기경보: precision/recall/F1/AUPRC/MCC (실 임상 유행 라벨 label_h 대비)
- 유행개시 리드타임: 2주 선행 예측의 baseline 교차로 onset 대비 며칠 앞서 경보했는가
"""

from __future__ import annotations

import json
import logging
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    matthews_corrcoef,
    precision_score,
    recall_score,
)

from ml.forecast.dataset import load_dataset
from ml.forecast.epidata_client import fetch_ilinet
from ml.forecast import features as F
from ml.forecast import model as M

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

OUTPUT = Path(__file__).resolve().parent.parent.parent / "analysis" / "outputs" / "forecast_ilinet_validation.json"
QUANTILES = M.QUANTILES
ALARM_HORIZON = 2  # 조기경보 기준 지평(주)
ALARM_SUSTAIN = 2  # 연속 N주 교차 시 경보 확정


def _wis(y: np.ndarray, q: np.ndarray) -> float:
    """Weighted Interval Score. q columns = QUANTILES 순서(0.025..0.975, median 포함).

    중심구간 [0.25,0.75](α=0.5), [0.025,0.975](α=0.05) + median(0.5) 사용.
    낮을수록 좋음. (Bracher et al. 2021 정의)
    """
    qi = {round(a, 3): i for i, a in enumerate(QUANTILES)}
    med = q[:, qi[0.5]]
    total = 0.5 * np.abs(y - med)
    n_int = 0
    for lo, hi, alpha in [(0.25, 0.75, 0.5), (0.025, 0.975, 0.05)]:
        l, u = q[:, qi[lo]], q[:, qi[hi]]
        is_score = (u - l) + (2 / alpha) * (l - y) * (y < l) + (2 / alpha) * (y - u) * (y > u)
        total = total + (alpha / 2) * is_score
        n_int += 1
    return float(np.mean(total / (n_int + 0.5)))


def _coverage95(y: np.ndarray, q: np.ndarray) -> float:
    qi = {round(a, 3): i for i, a in enumerate(QUANTILES)}
    lo, hi = q[:, qi[0.025]], q[:, qi[0.975]]
    return float(np.mean((y >= lo) & (y <= hi)))


def _clf_metrics(y: np.ndarray, prob: np.ndarray, thr: float = 0.5) -> dict:
    pred = (prob >= thr).astype(int)
    out = {"n": int(len(y)), "pos_rate": round(float(y.mean()), 4)}
    if len(np.unique(y)) < 2:
        out["note"] = "single_class"
        return out
    out.update({
        "precision": round(float(precision_score(y, pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y, pred, zero_division=0)), 4),
        "f1": round(float(f1_score(y, pred, zero_division=0)), 4),
        "mcc": round(float(matthews_corrcoef(y, pred)), 4),
        "auprc": round(float(average_precision_score(y, prob)), 4),
        "auprc_baseline": round(float(y.mean()), 4),
    })
    return out


def _onset_leadtime(season_df: pd.DataFrame, point_h2: np.ndarray) -> list[dict]:
    """region별 2주 선행 예측의 baseline 교차로 onset 대비 리드타임 산출.

    경보주(alarm_woy): yhat_{t+2} >= baseline 가 연속 ALARM_SUSTAIN 주 지속된 첫 t 의 week_of_season.
    lead = onset_woy - alarm_woy (양수=조기경보). onset 없는 시즌은 false-alarm 여부만 기록.
    """
    d = season_df.copy()
    d["yhat_h2"] = point_h2
    rows = []
    for region, g in d.groupby("region"):
        g = g.sort_values("week_of_season")
        base = g["baseline"].iloc[0]
        onset = g["onset_woy"].iloc[0]
        cross = (g["yhat_h2"].to_numpy() >= base).astype(int)
        alarm_woy = np.nan
        run = 0
        woys = g["week_of_season"].to_numpy()
        for i, c in enumerate(cross):
            run = run + 1 if c else 0
            if run >= ALARM_SUSTAIN:
                alarm_woy = int(woys[i - ALARM_SUSTAIN + 1])
                break
        rec = {"region": region, "onset_woy": (None if pd.isna(onset) else int(onset)),
               "alarm_woy": (None if np.isnan(alarm_woy) else int(alarm_woy))}
        if not pd.isna(onset) and not np.isnan(alarm_woy):
            rec["lead_weeks"] = int(onset) - int(alarm_woy)
            rec["detected_before_onset"] = rec["lead_weeks"] >= 0
        rows.append(rec)
    return rows


def run_backtest(df: pd.DataFrame, test_seasons: list[int]) -> dict:
    horizons = F.HORIZONS
    # 누적 pooled 예측 저장
    pooled = {h: {"y": [], "point": [], "pers": [], "clim": [], "q": [], "lab": [], "alarm": []}
              for h in horizons}
    lead_records: list[dict] = []
    per_season: dict[int, dict] = {}

    for s in test_seasons:
        train = df[df["season"] < s]
        test = df[df["season"] == s]
        if len(train) < 500 or test.empty:
            continue
        fc = M.Forecaster().fit(train)
        season_clf = {}
        for h in horizons:
            te = test.dropna(subset=fc.feats + [f"y_{h}", f"label_{h}"])
            if te.empty:
                continue
            pr = fc.predict(te, h)
            y = te[f"y_{h}"].to_numpy()
            pooled[h]["y"].append(y)
            pooled[h]["point"].append(pr["point"])
            pooled[h]["pers"].append(M.persistence(te, h))
            pooled[h]["clim"].append(M.climatology(te, h))
            pooled[h]["q"].append(pr["quantiles"])
            pooled[h]["lab"].append(te[f"label_{h}"].to_numpy())
            pooled[h]["alarm"].append(pr["alarm"])
            if h == ALARM_HORIZON:
                season_clf = {"mae": float(np.mean(np.abs(pr["point"] - y)))}

        # onset 리드타임 (ALARM_HORIZON 점예측)
        te2 = test.dropna(subset=fc.feats)
        if not te2.empty:
            p2 = fc.predict(te2, ALARM_HORIZON)["point"]
            recs = _onset_leadtime(te2, p2)
            for r in recs:
                r["season"] = int(s)
            lead_records.extend(recs)
        per_season[int(s)] = season_clf
        logger.info("시즌 %d 검증 완료 (train=%d, test=%d)", s, len(train), len(test))

    # ─── 메트릭 집계 ──────────────────────────────────────────────
    regression = {}
    probabilistic = {}
    alarm_clf = {}
    for h in horizons:
        if not pooled[h]["y"]:
            continue
        y = np.concatenate(pooled[h]["y"])
        pt = np.concatenate(pooled[h]["point"])
        pe = np.concatenate(pooled[h]["pers"])
        cl = np.concatenate(pooled[h]["clim"])
        q = np.concatenate(pooled[h]["q"])
        lab = np.concatenate(pooled[h]["lab"])
        alarm = np.concatenate(pooled[h]["alarm"])

        mae = float(np.mean(np.abs(pt - y)))
        mae_p = float(np.mean(np.abs(pe - y)))
        mae_c = float(np.mean(np.abs(cl - y)))
        regression[f"h{h}"] = {
            "mae": round(mae, 4),
            "rmse": round(float(np.sqrt(np.mean((pt - y) ** 2))), 4),
            "mae_persistence": round(mae_p, 4),
            "mae_climatology": round(mae_c, 4),
            "skill_vs_persistence": round(1 - mae / mae_p, 4) if mae_p > 0 else None,
            "skill_vs_climatology": round(1 - mae / mae_c, 4) if mae_c > 0 else None,
            "n": int(len(y)),
        }
        probabilistic[f"h{h}"] = {
            "wis": round(_wis(y, q), 4),
            "coverage_95": round(_coverage95(y, q), 4),
        }
        alarm_clf[f"h{h}"] = _clf_metrics(lab, alarm)

    # 리드타임 집계 (유행 발생 시즌만)
    epi = [r for r in lead_records if r.get("lead_weeks") is not None]
    leads = [r["lead_weeks"] for r in epi]
    detected = [r for r in epi if r["detected_before_onset"]]
    # false alarm: onset 없는 시즌인데 경보 발령
    no_onset = [r for r in lead_records if r["onset_woy"] is None]
    false_alarm = [r for r in no_onset if r["alarm_woy"] is not None]
    leadtime = {
        "alarm_horizon_weeks": ALARM_HORIZON,
        "n_region_seasons_with_epidemic": len(epi),
        "detection_rate_before_onset": round(len(detected) / len(epi), 4) if epi else None,
        "mean_lead_weeks": round(float(np.mean(leads)), 3) if leads else None,
        "median_lead_weeks": round(float(np.median(leads)), 3) if leads else None,
        "n_no_onset_region_seasons": len(no_onset),
        "false_alarm_rate_no_onset_seasons": round(len(false_alarm) / len(no_onset), 4) if no_onset else None,
    }

    return {
        "regression": regression,
        "probabilistic": probabilistic,
        "alarm_classification": alarm_clf,
        "onset_leadtime": leadtime,
        "per_season_h2_mae": per_season,
    }


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")
    panel = load_dataset(fetch_ilinet())
    df = F.make_features(panel)
    all_seasons = sorted(df["season"].unique())
    # 충분한 학습 이력 확보 후 2010~최신 시즌을 walk-forward 검증
    test_seasons = [int(s) for s in all_seasons if s >= 2010]
    logger.info("walk-forward 검증 시즌: %s", test_seasons)

    result = run_backtest(df, test_seasons)
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_source": "CDC ILINet (Delphi Epidata fluview) — 실 임상 외래 표본감시 wILI",
        "ground_truth": "wILI(가중 ILI%) — 임상 확진 대리 표준지표(CDC FluSight 동일)",
        "regions": "nat + HHS 1-10 (11)",
        "n_rows": int(len(df)),
        "seasons_total": [int(s) for s in all_seasons],
        "test_seasons": test_seasons,
        "model": "XGBoost+LightGBM delta-ensemble (point) · XGBoost multi-quantile (interval) · XGBoost classifier (alarm)",
        "validation": "season-holdout walk-forward (train season<S), baseline/climatology 누수 차단",
        "honesty_note": (
            "이전 self-target proxy 라벨(OTC z-score, KDCA 대비 Cohen κ=0.058)을 폐기하고 "
            "실제 임상 감시 지표(CDC ILINet wILI)를 ground truth 로 직접 검증. "
            "COVID 교란 시즌(2020-21)은 유행 미발생으로 리드타임 통계에서 자동 제외(onset 없음)."
        ),
    }
    out = {"meta": meta, "results": result}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    logger.info("결과 저장: %s", OUTPUT)
    print("\n=== 실 임상(CDC ILINet) walk-forward 검증 결과 ===")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
