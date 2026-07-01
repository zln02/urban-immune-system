"""최종 학습 + 서빙 산출물 생성.

전체 실 임상(CDC ILINet) 데이터로 Forecaster 를 학습해 체크포인트로 저장하고,
권역별 최신주 기준 1–4주 선행 예측(점·95% 구간·유행경보확률)을 JSON 으로 출력한다.
백엔드 /api/v1/forecast/* 가 이 JSON 을 읽어 대시보드에 제공한다.
"""

from __future__ import annotations

import json
import logging
import warnings
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np

from ml.forecast.dataset import load_dataset
from ml.forecast.epidata_client import fetch_ilinet
from ml.forecast import features as F
from ml.forecast import model as M

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

CKPT_DIR = Path(__file__).resolve().parent.parent / "checkpoints" / "forecast"
LATEST_OUT = Path(__file__).resolve().parent.parent.parent / "analysis" / "outputs" / "forecast_ilinet_latest.json"


def train_and_save() -> dict:
    panel = load_dataset(fetch_ilinet())
    df = F.make_features(panel)

    fc = M.Forecaster().fit(df)
    CKPT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump({"models": fc.models, "feats": fc.feats, "horizons": fc.horizons},
                CKPT_DIR / "forecaster.joblib")
    logger.info("체크포인트 저장: %s", CKPT_DIR / "forecaster.joblib")

    # 권역별 최신주(피처 완비) 예측
    forecasts = []
    for region, g in df.groupby("region"):
        g = g.sort_values("epiweek")
        row = g[g[fc.feats].notna().all(axis=1)].tail(1)
        if row.empty:
            continue
        epiweek = int(row["epiweek"].iloc[0])
        cur_wili = float(row["wili"].iloc[0])
        baseline = float(row["baseline"].iloc[0]) if not row["baseline"].isna().iloc[0] else None
        horizon_preds = []
        for h in fc.horizons:
            pr = fc.predict(row, h)
            q = pr["quantiles"][0]
            qi = {round(a, 3): i for i, a in enumerate(M.QUANTILES)}
            point = float(pr["point"][0])
            alarm = float(pr["alarm"][0])
            horizon_preds.append({
                "h_weeks": h,
                "point_wili": round(point, 3),
                "lower_95": round(float(q[qi[0.025]]), 3),
                "upper_95": round(float(q[qi[0.975]]), 3),
                "epidemic_alarm_prob": round(alarm, 4),
                "above_baseline": (point >= baseline) if baseline is not None else None,
            })
        forecasts.append({
            "region": region,
            "latest_epiweek": epiweek,
            "current_wili": round(cur_wili, 3),
            "baseline": round(baseline, 3) if baseline is not None else None,
            "horizons": horizon_preds,
        })

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data_source": "CDC ILINet (Delphi Epidata fluview) — 실 임상 외래 표본감시 wILI",
        "model": "XGBoost+LightGBM delta-ensemble + XGBoost multi-quantile + XGBoost alarm classifier",
        "n_regions": len(forecasts),
        "forecasts": forecasts,
    }
    LATEST_OUT.parent.mkdir(parents=True, exist_ok=True)
    LATEST_OUT.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    logger.info("최신 예측 저장: %s", LATEST_OUT)
    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
    res = train_and_save()
    print("\n=== 최신 예측(권역별 발췌) ===")
    for f in res["forecasts"][:3]:
        print(f["region"], "epiweek", f["latest_epiweek"], "wili", f["current_wili"],
              "→", [(p["h_weeks"], p["point_wili"], p["epidemic_alarm_prob"]) for p in f["horizons"]])
