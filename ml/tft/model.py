"""Temporal Fusion Transformer (TFT) 기반 다변량 시계열 예측.

입력: L1(OTC) + L2(하수) + L3(검색) + 기온 + 습도 → 7/14/21일 위험도 예측
pytorch_forecasting 라이브러리 사용.

참고: Lim et al. (2021) "Temporal Fusion Transformers for Interpretable Multi-horizon Time Series Forecasting"
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import pytorch_lightning as pl
import torch
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.metrics import QuantileLoss

logger = logging.getLogger(__name__)

MODEL_DIR = Path(__file__).parent.parent / "checkpoints"
MODEL_PATH = MODEL_DIR / "tft_best.ckpt"

# 예측 지평선 (주 단위)
PREDICTION_HORIZONS = [1, 2, 3]  # 1주=7일, 2주=14일, 3주=21일
MAX_ENCODER_LENGTH = 24           # 과거 24주 입력


def create_dataset(df: pd.DataFrame) -> TimeSeriesDataSet:
    """pandas DataFrame → TFT 학습용 TimeSeriesDataSet 변환."""
    return TimeSeriesDataSet(
        df,
        time_idx="time_idx",
        target="influenza_cases",
        group_ids=["region"],
        min_encoder_length=MAX_ENCODER_LENGTH // 2,
        max_encoder_length=MAX_ENCODER_LENGTH,
        min_prediction_length=1,
        max_prediction_length=max(PREDICTION_HORIZONS),
        time_varying_known_reals=["time_idx"],
        time_varying_unknown_reals=["l1_otc", "l2_wastewater", "l3_search", "temperature", "humidity"],
        target_normalizer=None,
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_length=True,
    )


def build_model(dataset: TimeSeriesDataSet) -> TemporalFusionTransformer:
    return TemporalFusionTransformer.from_dataset(
        dataset,
        learning_rate=3e-4,
        hidden_size=64,
        attention_head_size=4,
        dropout=0.1,
        hidden_continuous_size=16,
        output_size=7,  # 분위수 예측
        loss=QuantileLoss(),
        log_interval=10,
        reduce_on_plateau_patience=4,
    )


def train(df: pd.DataFrame, max_epochs: int = 50, checkpoint_dir: Path | None = None) -> str:
    """TFT 모델을 학습하고 체크포인트 경로를 반환한다."""
    dataset = create_dataset(df)
    model = build_model(dataset)

    trainer = pl.Trainer(
        max_epochs=max_epochs,
        accelerator="auto",
        gradient_clip_val=0.1,
        default_root_dir=str(checkpoint_dir or MODEL_DIR),
    )
    loader = dataset.to_dataloader(train=True, batch_size=32, num_workers=0)
    trainer.fit(model, train_dataloaders=loader)

    best_path = trainer.checkpoint_callback.best_model_path  # type: ignore[union-attr]
    logger.info("TFT 학습 완료: %s", best_path)
    return best_path


def load_model() -> TemporalFusionTransformer | None:
    """저장된 체크포인트를 로드한다."""
    if not MODEL_PATH.exists():
        logger.warning("TFT 체크포인트 없음: %s", MODEL_PATH)
        return None
    return TemporalFusionTransformer.load_from_checkpoint(str(MODEL_PATH))


def predict(model: TemporalFusionTransformer, df: pd.DataFrame) -> dict:
    """7/14/21일 예측값과 Attention 가중치를 반환한다."""
    dataset = create_dataset(df)
    loader = dataset.to_dataloader(train=False, batch_size=1, num_workers=0)
    predictions, x = model.predict(loader, return_x=True, return_attention=True, mode="raw")

    return {
        "forecast_7d": float(predictions.prediction[0, 0, 3]),   # 중앙값
        "forecast_14d": float(predictions.prediction[0, 1, 3]),
        "forecast_21d": float(predictions.prediction[0, 2, 3]),
        "attention_weights": predictions.attention[0].tolist() if hasattr(predictions, "attention") else [],
    }
