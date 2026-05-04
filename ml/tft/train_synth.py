"""TFT 빠른 학습 PoC — 합성 시계열로 파이프라인 작동·Attention 해석 가능성 입증.

목적 (D-6 발표):
  - TFT가 실제로 학습 가능한 환경이 갖춰져 있다는 것을 증명
  - Attention weight 추출 가능 → 보건당국 신뢰 메시지의 코드적 근거
  - max_epochs=5 정도의 짧은 학습으로 5분 이내 완료 (CPU 환경 가정)

생성물:
  - ml/checkpoints/tft_synth/  (Lightning 체크포인트)
  - ml/outputs/tft_metrics.json (loss curve + attention summary)

CLI:
  python -m ml.tft.train_synth                  # 기본: 5 epoch, 1 region
  python -m ml.tft.train_synth --epochs 20      # 더 길게
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import warnings
from datetime import datetime, timezone
from pathlib import Path

# pytorch_forecasting 1.7+은 `lightning.pytorch` 를 사용하므로 trainer/콜백도 동일 패키지에서 import
import lightning.pytorch as pl
import numpy as np
import pandas as pd
import torch
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning.pytorch.loggers import CSVLogger
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.metrics import QuantileLoss

from ml.xgboost.model import generate_synthetic_data

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(__file__).parent.parent / "checkpoints" / "tft_synth"
OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "tft_metrics.json"

FEATURE_COLS = ["l1_otc", "l2_wastewater", "l3_search", "temperature", "humidity"]
TARGET_COL = "confirmed_future"  # 선행 검증 task와 동일 (XGBoost와 비교 가능)
GROUP_COL = "region"
TIME_IDX_COL = "time_idx"
LEAD_WEEKS = 2  # t+2주 후 확진자 예측

MAX_ENCODER = 24       # 24주 과거 입력
MAX_PREDICTION = 3     # 1/2/3주 후 예측 (= 7/14/21일)


def _make_dataframe(n_weeks: int = 104, n_regions: int = 1, seed: int = 42) -> pd.DataFrame:
    """region 차원을 더한 학습 DataFrame을 생성한다.

    PR #11(reproduce_validation)이 develop에 머지되기 전이라도 독립 작동하도록,
    confirmed_future / alert_future 컬럼을 여기서 직접 계산한다.
    """
    frames: list[pd.DataFrame] = []
    for r in range(n_regions):
        df = generate_synthetic_data(n_weeks=n_weeks, seed=seed + r)
        df = df.reset_index(drop=False).rename(columns={"index": "time"})

        # composite_score를 proxy "확진자 지수"로 보고 t+LEAD주 후 값을 타깃으로
        if TARGET_COL not in df.columns:
            comp = df["composite_score"].to_numpy()
            future = np.roll(comp, -LEAD_WEEKS)
            future[-LEAD_WEEKS:] = comp[-LEAD_WEEKS:]
            df[TARGET_COL] = future

        df[GROUP_COL] = f"R{r:02d}"
        df[TIME_IDX_COL] = np.arange(len(df))
        frames.append(df)
    return pd.concat(frames, ignore_index=True)


def _build_dataset(df: pd.DataFrame, training: bool) -> TimeSeriesDataSet:
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


def _attention_summary(model: TemporalFusionTransformer, dataset: TimeSeriesDataSet) -> dict | None:
    """TFT의 encoder attention + variable importance 요약.

    pytorch-forecasting 1.x: raw output은 dict-like 구조로 다음 키 포함
      - encoder_attention: (batch, encoder_len, heads, encoder_len) — 시점 가중치
      - encoder_variables / decoder_variables / static_variables — 변수 중요도
    """
    # encoder variable importance 순서 및 한국어 레이블 매핑
    _ENCODER_VAR_ORDER = [
        "encoder_length",
        "confirmed_future_center",
        "confirmed_future_scale",
        "l1_otc",
        "l2_wastewater",
        "l3_search",
        "temperature",
        "humidity",
    ]
    _LABEL_KR = {
        "l1_otc": "OTC약국판매",
        "l2_wastewater": "하수기반감시",
        "l3_search": "검색트렌드",
        "temperature": "기온",
        "humidity": "습도",
    }
    _FEATURE_VARS = set(_LABEL_KR.keys())

    try:
        loader = dataset.to_dataloader(train=False, batch_size=4, num_workers=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = model.predict(loader, mode="raw", return_x=True, return_index=True)

        out = raw.output
        encoder_attention = out["encoder_attention"]
        encoder_variables = out["encoder_variables"]

        attn_t = (
            encoder_attention.float()
            if isinstance(encoder_attention, torch.Tensor)
            else torch.as_tensor(encoder_attention).float()
        )
        var_t = (
            encoder_variables.float()
            if isinstance(encoder_variables, torch.Tensor)
            else torch.as_tensor(encoder_variables).float()
        )

        # encoder time step별 평균 attention (전체 batch + heads + target step 평균)
        # shape (B, T_enc, heads, T_enc) → (T_enc,) 마지막 query축에 대한 평균
        per_step = attn_t.mean(dim=(0, 2, 3)).tolist() if attn_t.ndim == 4 else attn_t.mean().tolist()

        # variable importance: (B, T_enc, n_vars) → (n_vars,)
        per_variable = var_t.mean(dim=(0, 1)).tolist() if var_t.ndim >= 3 else var_t.mean().tolist()

        # 한국어 1줄 요약: 실제 피처 변수만 필터링 후 top-3
        importance_values = per_variable[0] if (
            isinstance(per_variable, list) and per_variable and isinstance(per_variable[0], list)
        ) else per_variable

        feature_pairs = [
            (var, importance_values[i])
            for i, var in enumerate(_ENCODER_VAR_ORDER[:len(importance_values)])
            if var in _FEATURE_VARS
        ]
        feature_pairs.sort(key=lambda x: x[1], reverse=True)
        top3 = feature_pairs[:3]

        # "검색량(L3) 0.41 · 하수(L2) 0.32 · OTC(L1) 0.27" 형식
        short_label = {
            "l3_search": "검색량(L3)",
            "l2_wastewater": "하수(L2)",
            "l1_otc": "OTC(L1)",
            "temperature": "기온(AUX)",
            "humidity": "습도(AUX)",
        }
        summary_parts = [f"{short_label.get(var, var)} {val:.2f}" for var, val in top3]
        attention_summary_kr = " · ".join(summary_parts)
        logger.info("Attention 한국어 요약: %s", attention_summary_kr)
        print(f"\n  [Attention] {attention_summary_kr}")

        return {
            "encoder_attention_shape": list(attn_t.shape),
            "encoder_variable_importance_shape": list(var_t.shape),
            "mean_attention_per_encoder_step": per_step,
            "mean_encoder_variable_importance": per_variable,
            "encoder_variable_names": list(model.hparams.get("x_reals", [])) if hasattr(model, "hparams") else [],
            "attention_top3_kr": [_LABEL_KR.get(var, var) for var, _ in top3],
            "attention_summary_kr": attention_summary_kr,
        }
    except Exception as exc:
        logger.warning("Attention 추출 실패: %s", exc)
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="TFT 빠른 PoC 학습")
    parser.add_argument("--epochs", type=int, default=5)
    parser.add_argument("--regions", type=int, default=1, help="시뮬할 region 수 (n_regions × seed)")
    parser.add_argument("--weeks", type=int, default=104)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    pl.seed_everything(42, workers=True)

    df = _make_dataframe(n_weeks=args.weeks, n_regions=args.regions, seed=42)
    logger.info("학습 데이터: %d행 × %d region (각 %d주)", len(df), args.regions, args.weeks)

    # train / val 분할: 마지막 (MAX_PREDICTION + buffer) 주를 검증
    val_cutoff = df[TIME_IDX_COL].max() - MAX_PREDICTION - 4
    train_df = df[df[TIME_IDX_COL] <= val_cutoff].reset_index(drop=True)
    val_df = df.reset_index(drop=True)

    train_ds = _build_dataset(train_df, training=True)
    val_ds = TimeSeriesDataSet.from_dataset(train_ds, val_df, predict=True, stop_randomization=True)

    train_loader = train_ds.to_dataloader(train=True, batch_size=args.batch_size, num_workers=0)
    val_loader = val_ds.to_dataloader(train=False, batch_size=args.batch_size, num_workers=0)

    model = TemporalFusionTransformer.from_dataset(
        train_ds,
        learning_rate=3e-3,
        hidden_size=32,
        attention_head_size=2,
        dropout=0.1,
        hidden_continuous_size=16,
        output_size=7,
        loss=QuantileLoss(),
        log_interval=0,
        reduce_on_plateau_patience=4,
    )
    logger.info("모델 파라미터 수: %d", sum(p.numel() for p in model.parameters()))

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    csv_logger = CSVLogger(save_dir=str(CHECKPOINT_DIR), name="tft")
    ckpt_cb = ModelCheckpoint(
        dirpath=str(CHECKPOINT_DIR),
        filename="tft_best",
        monitor="val_loss",
        save_top_k=1,
        mode="min",
    )
    early_stop = EarlyStopping(monitor="val_loss", patience=3, mode="min", min_delta=0.001)

    trainer = pl.Trainer(
        max_epochs=args.epochs,
        accelerator="cpu",
        gradient_clip_val=0.1,
        callbacks=[ckpt_cb, early_stop],
        logger=csv_logger,
        enable_progress_bar=False,
        enable_model_summary=False,
    )

    logger.info("TFT 학습 시작 (epochs=%d, batch=%d)", args.epochs, args.batch_size)
    trainer.fit(model, train_dataloaders=train_loader, val_dataloaders=val_loader)

    # 학습 곡선 읽기
    loss_csv = Path(csv_logger.log_dir) / "metrics.csv"
    loss_curve: list[dict] = []
    if loss_csv.exists():
        m = pd.read_csv(loss_csv)
        for _, r in m.iterrows():
            loss_curve.append({
                "epoch": int(r["epoch"]) if not pd.isna(r.get("epoch")) else None,
                "step": int(r["step"]) if not pd.isna(r.get("step")) else None,
                "train_loss": float(r["train_loss_step"]) if not pd.isna(r.get("train_loss_step")) else None,
                "val_loss": float(r["val_loss"]) if not pd.isna(r.get("val_loss")) else None,
            })

    # 검증 예측 + 점 비교
    pred = model.predict(val_loader, mode="prediction")
    pred_t = torch.as_tensor(pred) if not isinstance(pred, torch.Tensor) else pred
    pred_summary = {
        "n_samples": int(pred_t.shape[0]) if pred_t.ndim >= 1 else 1,
        "horizon_steps": int(pred_t.shape[1]) if pred_t.ndim >= 2 else None,
        "mean_pred_per_horizon": pred_t.float().mean(dim=0).tolist() if pred_t.ndim >= 2 else float(pred_t.mean()),
    }

    attn = _attention_summary(model, val_ds)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "n_weeks": args.weeks,
            "n_regions": args.regions,
            "max_epochs": args.epochs,
            "batch_size": args.batch_size,
            "max_encoder_length": MAX_ENCODER,
            "max_prediction_length": MAX_PREDICTION,
            "feature_cols": FEATURE_COLS,
            "target_col": TARGET_COL,
        },
        "model_params": int(sum(p.numel() for p in model.parameters())),
        "best_checkpoint": str(ckpt_cb.best_model_path) if ckpt_cb.best_model_path else None,
        "best_val_loss": float(ckpt_cb.best_model_score) if ckpt_cb.best_model_score is not None else None,
        "loss_curve_tail": loss_curve[-20:],  # 마지막 20행만
        "prediction_summary": pred_summary,
        "attention_summary": attn,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("결과 저장: %s", args.output)

    print("\n=== TFT PoC 요약 ===")
    print(f"  파라미터 수: {result['model_params']:,}")
    print(f"  best_val_loss: {result['best_val_loss']}")
    print(f"  best ckpt: {result['best_checkpoint']}")
    if attn:
        print(f"  attention shape: {attn['shape']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
