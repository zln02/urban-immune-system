"""TFT 회귀 backtest — 17지역 composite score 예측 정확도 검증.

배경:
  기존 backtest_17regions.json 은 분류 메트릭(precision/recall/f1)만 보유.
  TFT 는 composite score(0-100, 2주 선행) 를 회귀로 예측하지만 회귀 메트릭(MAE/MAPE/RMSE)
  은 산출되지 않았다. 본 스크립트가 그 갭을 메운다.

주의:
  - TFT target 변수명이 "confirmed_future" 지만 실제로는 composite 0-100 점수다.
    (train_real.py L218-222: composite = 0.35·L1 + 0.40·L2 + 0.25·L3, shift(-2))
    즉 환자 수 절대값이 아니라 "위험 트렌드" 회귀.
  - 환자 수 절대 예측 검증은 별도 모델 필요 (현 단계 미수행).

비교 대상:
  - tft_best.ckpt       (2026-05-04 prod, val_loss=5.48)
  - tft_best-v3.ckpt    (2026-06-01 재학습, val_loss=5.72)

생성물:
  - analysis/outputs/tft_regression_backtest_17regions.json
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from dotenv import load_dotenv
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet

from ml.tft.train_real import (
    FEATURE_COLS,
    MAX_ENCODER,
    MAX_PREDICTION,
    _build_dataframe_from_db,
)
from ml.tft.train_synth import GROUP_COL, TARGET_COL, TIME_IDX_COL

_main_repo = Path("/home/wlsdud5035/urban-immune-system")
load_dotenv(_main_repo / ".env", override=False)

logger = logging.getLogger(__name__)

CHECKPOINTS = {
    "prod_20260504": _main_repo / "ml" / "checkpoints" / "tft_real" / "tft_best.ckpt",
    "v3_20260601": _main_repo / "ml" / "checkpoints" / "tft_real" / "tft_best-v3.ckpt",
}
OUTPUT_PATH = Path(__file__).parent / "outputs" / "tft_regression_backtest_17regions.json"


def _build_dataset_for_inference(df: pd.DataFrame) -> TimeSeriesDataSet:
    """train_real._build_dataset와 동일 config (TFT 입력 호환성 유지)."""
    return TimeSeriesDataSet(
        df,
        time_idx=TIME_IDX_COL,
        target=TARGET_COL,
        group_ids=[GROUP_COL],
        min_encoder_length=MAX_ENCODER // 2,
        max_encoder_length=MAX_ENCODER,
        min_prediction_length=1,
        max_prediction_length=MAX_PREDICTION,
        time_varying_known_reals=[TIME_IDX_COL],
        time_varying_unknown_reals=FEATURE_COLS + [TARGET_COL],
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
        allow_missing_timesteps=False,
    )


def _metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    """회귀 메트릭 산출 — composite 0-100 스케일. NaN 안전 처리."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    if y_true.size == 0:
        return {"n": 0, "mae": None, "mape_percent": None, "rmse": None}
    # NaN 마스킹 (시퀀스 boundary에서 target shift로 발생)
    valid = ~(np.isnan(y_true) | np.isnan(y_pred))
    yt = y_true[valid]
    yp = y_pred[valid]
    n_dropped = int((~valid).sum())
    if yt.size == 0:
        return {"n": 0, "n_dropped_nan": n_dropped, "mae": None, "mape_percent": None, "rmse": None}
    err = yp - yt
    mae = float(np.mean(np.abs(err)))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    nonzero = yt > 1.0
    mape = float(np.mean(np.abs(err[nonzero] / yt[nonzero])) * 100) if nonzero.any() else None
    return {
        "n": int(yt.size),
        "n_dropped_nan": n_dropped,
        "mae": round(mae, 3),
        "mape_percent": round(mape, 2) if mape is not None else None,
        "rmse": round(rmse, 3),
        "mean_true": round(float(np.mean(yt)), 2),
        "mean_pred": round(float(np.mean(yp)), 2),
    }


def _evaluate_checkpoint(ckpt_path: Path, df: pd.DataFrame) -> dict:
    logger.info("체크포인트 평가 시작: %s", ckpt_path.name)
    if not ckpt_path.exists():
        return {"error": "checkpoint not found", "path": str(ckpt_path)}

    model = TemporalFusionTransformer.load_from_checkpoint(str(ckpt_path))
    model.eval()

    ds = _build_dataset_for_inference(df)
    dl = ds.to_dataloader(train=False, batch_size=8, num_workers=0)

    with torch.no_grad():
        try:
            raw_pred = model.predict(dl, mode="prediction", return_index=True, return_y=True)
        except Exception as exc:
            logger.warning("predict with return_y 실패: %s — fallback", exc)
            preds_tensor = model.predict(dl, mode="prediction")
            y_pred_all = preds_tensor.cpu().numpy() if torch.is_tensor(preds_tensor) else np.asarray(preds_tensor)
            y_true_list, idx_list = [], []
            for x, y in iter(dl):
                ty = y[0] if isinstance(y, tuple) else y
                y_true_list.append(ty.cpu().numpy())
            y_true_all = np.concatenate(y_true_list, axis=0)
            index = None
        else:
            if hasattr(raw_pred, "output"):
                out = raw_pred.output
                y_pred_all = out.cpu().numpy() if torch.is_tensor(out) else np.asarray(out)
                y_attr = raw_pred.y
                if isinstance(y_attr, tuple):
                    y_true_t = y_attr[0]
                else:
                    y_true_t = y_attr
                y_true_all = y_true_t.cpu().numpy() if torch.is_tensor(y_true_t) else np.asarray(y_true_t)
                index = raw_pred.index
            else:
                y_pred_all = raw_pred[0].cpu().numpy() if torch.is_tensor(raw_pred[0]) else np.asarray(raw_pred[0])
                y_true_all = None
                index = raw_pred[2] if len(raw_pred) > 2 else None

    if y_true_all is None:
        y_true_list = []
        for x, y in iter(dl):
            ty = y[0] if isinstance(y, tuple) else y
            y_true_list.append(ty.cpu().numpy())
        y_true_all = np.concatenate(y_true_list, axis=0)

    logger.info("예측 완료 y_pred=%s y_true=%s", y_pred_all.shape, y_true_all.shape)

    # horizon별
    horizon_metrics = {}
    n_horizon = y_pred_all.shape[1] if y_pred_all.ndim >= 2 else 1
    for h in range(n_horizon):
        yp = y_pred_all[:, h] if y_pred_all.ndim >= 2 else y_pred_all
        yt = y_true_all[:, h] if y_true_all.ndim >= 2 else y_true_all
        horizon_metrics[f"horizon_{h+1}week"] = _metrics(yt, yp)

    # region별
    region_metrics = {}
    if index is not None and isinstance(index, pd.DataFrame) and GROUP_COL in index.columns:
        regions = index[GROUP_COL].values
        for region in pd.unique(regions):
            mask = regions == region
            if y_pred_all.ndim >= 2 and y_pred_all.shape[1] >= 2:
                region_metrics[str(region)] = {
                    "horizon_1week": _metrics(y_true_all[mask, 0], y_pred_all[mask, 0]),
                    "horizon_2week": _metrics(y_true_all[mask, 1], y_pred_all[mask, 1]),
                }
            else:
                region_metrics[str(region)] = {
                    "overall": _metrics(y_true_all[mask].flatten(), y_pred_all[mask].flatten()),
                }

    overall = _metrics(y_true_all.flatten(), y_pred_all.flatten())

    return {
        "checkpoint": ckpt_path.name,
        "n_sequences": int(y_pred_all.shape[0]),
        "prediction_length": int(n_horizon),
        "overall": overall,
        "by_horizon": horizon_metrics,
        "by_region": region_metrics,
    }


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info("데이터 로드 중 (DB)...")
    df = _build_dataframe_from_db(pathogen="influenza", min_weeks=14)
    logger.info("DataFrame: %d행 × %d region", len(df), df[GROUP_COL].nunique())

    results = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "purpose": "TFT composite score(0-100) 회귀 검증 — 환자수 절대 예측 아님",
        "target_semantics": "confirmed_future = composite shift(-2 weeks); composite = 0.35·L1+0.40·L2+0.25·L3",
        "data_summary": {
            "n_rows": int(len(df)),
            "n_regions": int(df[GROUP_COL].nunique()),
            "regions": sorted(df[GROUP_COL].unique().tolist()),
            "time_idx_max": int(df[TIME_IDX_COL].max()),
        },
        "evaluations": {},
    }

    for label, ckpt_path in CHECKPOINTS.items():
        try:
            results["evaluations"][label] = _evaluate_checkpoint(ckpt_path, df)
        except Exception as exc:
            logger.exception("%s 평가 실패: %s", label, exc)
            results["evaluations"][label] = {"error": str(exc), "type": type(exc).__name__}

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    logger.info("결과 저장: %s", OUTPUT_PATH)
    print(f"\n결과 파일: {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
