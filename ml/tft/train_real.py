"""TFT 실데이터 학습 — TimescaleDB layer_signals 26주 누적 기반 prod 전환.

train_synth.py 와 동일한 학습 로직을 사용하되 입력만 합성→실 DB 로 교체.

D-5 안정화 (2026-05-02):
  - encoder_length 24 → 12 : 26주로 region당 시퀀스 1~2 → 13개로 증가 (총 ~221 시퀀스)
  - prediction_length 3 → 2: 7/14일 horizon (21일은 데이터 누적 후)
  - hidden_size 48 → 32   : capacity 축소, 과적합 방지
  - dropout 0.15 → 0.25 + weight_decay 1e-4
  - EarlyStop min_delta 0.001 → 0.05 (noise 무시)
  - SWA (Stochastic Weight Averaging) 추가

CLI:
  python -m ml.tft.train_real                           # 기본: 50 epoch, 안정화 설정
  python -m ml.tft.train_real --epochs 30 --regions 5   # 빠른 테스트
  python -m ml.tft.train_real --weeks 26                # 분석창 명시

생성물:
  - ml/checkpoints/tft_real/tft_best.ckpt
  - ml/outputs/tft_real_metrics.json
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

import lightning.pytorch as pl
import numpy as np
import pandas as pd
import torch
import warnings
from dotenv import load_dotenv
from lightning.pytorch.callbacks import EarlyStopping, ModelCheckpoint
from lightning.pytorch.loggers import CSVLogger
from pytorch_forecasting import TemporalFusionTransformer, TimeSeriesDataSet
from pytorch_forecasting.metrics import QuantileLoss

# train_synth 의 공통 상수만 import (MAX_ENCODER/MAX_PREDICTION 은 자체 override)
from ml.tft.train_synth import (
    GROUP_COL, LEAD_WEEKS, TARGET_COL, TIME_IDX_COL,
)

# 실데이터 전용 피처 — humidity 제거 (DB에 humidity layer 미적재 → 0 패딩 시 attention 왜곡)
FEATURE_COLS = ["l1_otc", "l2_wastewater", "l3_search", "temperature"]

# 실데이터 전용 시퀀스 설정 (D-5 안정화)
# 26주 데이터로는 train_synth 의 (24, 3) 이면 region당 시퀀스 ~1개 → 학습 불가능.
# (12, 2) 로 줄여서 region당 13 시퀀스 확보 (17 region × 13 = 221 시퀀스).
MAX_ENCODER = 12       # 12주 과거 입력 (synth 24 → real 12)
MAX_PREDICTION = 2     # 1/2주 후 예측 = 7/14일 (synth 3 → real 2)

logger = logging.getLogger(__name__)

CHECKPOINT_DIR = Path(__file__).parent.parent / "checkpoints" / "tft_real"
OUTPUT_PATH = Path(__file__).parent.parent / "outputs" / "tft_real_metrics.json"

_DEFAULT_DB_URL = "postgresql://uis_user:changeme_local@localhost:5432/urban_immune"

# 프로젝트 루트 .env 로드
_project_root = Path(__file__).parent.parent.parent
load_dotenv(_project_root / ".env", override=False)


def _build_dataset(df: pd.DataFrame, training: bool) -> TimeSeriesDataSet:
    """실데이터 4-feature TimeSeriesDataSet (humidity 제외)."""
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


def _attention_summary_real(model, dataset) -> dict | None:
    """실데이터 학습용 attention summary (humidity 제외 ORDER)."""
    _ENCODER_VAR_ORDER = [
        "encoder_length",
        "confirmed_future_center",
        "confirmed_future_scale",
        "l1_otc", "l2_wastewater", "l3_search", "temperature",
    ]
    _LABEL_KR = {
        "l1_otc": "OTC약국판매",
        "l2_wastewater": "하수기반감시",
        "l3_search": "검색트렌드",
        "temperature": "기온",
    }
    _SHORT_KR = {
        "l3_search": "검색량(L3)",
        "l2_wastewater": "하수(L2)",
        "l1_otc": "OTC(L1)",
        "temperature": "기온(AUX)",
    }
    _FEATURE_VARS = set(_LABEL_KR.keys())
    try:
        loader = dataset.to_dataloader(train=False, batch_size=4, num_workers=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            raw = model.predict(loader, mode="raw", return_x=True, return_index=True)
        out = raw.output
        attn_t = torch.as_tensor(out["encoder_attention"]).float()
        var_t = torch.as_tensor(out["encoder_variables"]).float()
        per_step = attn_t.mean(dim=(0, 2, 3)).tolist() if attn_t.ndim == 4 else attn_t.mean().tolist()
        per_variable = var_t.mean(dim=(0, 1)).tolist() if var_t.ndim >= 3 else var_t.mean().tolist()
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
        summary_kr = " · ".join(f"{_SHORT_KR.get(v, v)} {val:.2f}" for v, val in top3)
        logger.info("Attention 한국어 요약: %s", summary_kr)
        print(f"\n  [Attention] {summary_kr}")
        return {
            "encoder_attention_shape": list(attn_t.shape),
            "encoder_variable_importance_shape": list(var_t.shape),
            "mean_attention_per_encoder_step": per_step,
            "mean_encoder_variable_importance": per_variable,
            "encoder_variable_names": list(model.hparams.get("x_reals", [])) if hasattr(model, "hparams") else [],
            "attention_top3_kr": [_LABEL_KR.get(v, v) for v, _ in top3],
            "attention_summary_kr": summary_kr,
        }
    except Exception as exc:
        logger.warning("Attention 추출 실패: %s", exc)
        return None


async def _fetch_layer_signals(db_url: str, pathogen: str = "influenza") -> pd.DataFrame:
    """layer_signals 에서 region × layer × time wide-format DataFrame 반환.

    SELECT 결과:
      time, region, l1_otc, l2_wastewater, l3_search, temperature, humidity
    """
    import asyncpg

    conn = await asyncpg.connect(_normalize_dsn(db_url))
    try:
        rows = await conn.fetch(
            """
            SELECT time, region, layer, value
            FROM layer_signals
            WHERE pathogen = $1
              AND layer IN ('otc', 'wastewater', 'search', 'weather')
            ORDER BY region, time, layer
            """,
            pathogen,
        )
    finally:
        await conn.close()

    if not rows:
        raise RuntimeError(
            "layer_signals 가 비어있습니다. 먼저 다음을 실행하세요:\n"
            "  python -m pipeline.collectors.naver_backfill --weeks 26\n"
            "  python -m pipeline.collectors.kowas_loader\n"
        )

    df = pd.DataFrame([dict(r) for r in rows])
    # layer 별 wide pivot
    pivot = df.pivot_table(index=["time", "region"], columns="layer", values="value", aggfunc="mean")
    pivot = pivot.reset_index()
    pivot = pivot.rename(columns={
        "otc": "l1_otc",
        "wastewater": "l2_wastewater",
        "search": "l3_search",
        "weather": "temperature",  # AUX weather → temperature 컬럼 매핑 (현재 weather_collector는 단일 metric)
    })
    # 누락 컬럼 보강 (기상 미수집 지역) — humidity 제거 (DB 미적재로 attention 왜곡)
    for col in FEATURE_COLS:
        if col not in pivot.columns:
            pivot[col] = 0.0
    pivot = pivot.sort_values(["region", "time"]).reset_index(drop=True)
    return pivot


def _normalize_dsn(db_url: str) -> str:
    return db_url.replace("postgresql+asyncpg://", "postgresql://")


def _build_dataframe_from_db(pathogen: str = "influenza", min_weeks: int = 20) -> pd.DataFrame:
    """DB에서 학습 DataFrame을 구성한다 (TFT 입력 형태)."""
    db_url = os.getenv("DATABASE_URL", _DEFAULT_DB_URL)
    raw = asyncio.run(_fetch_layer_signals(db_url, pathogen=pathogen))

    # 결측치 처리: 같은 region 내 forward-fill, 그래도 빈 칸은 0
    raw[FEATURE_COLS] = raw.groupby("region")[FEATURE_COLS].ffill().bfill().fillna(0)

    # composite proxy → confirmed_future 타깃 (XGBoost·SY 비교용)
    # composite = 0.35*L1 + 0.40*L2 + 0.25*L3 (게이트 미적용 raw composite)
    raw["composite"] = 0.35 * raw["l1_otc"] + 0.40 * raw["l2_wastewater"] + 0.25 * raw["l3_search"]
    raw[TARGET_COL] = raw.groupby("region")["composite"].shift(-LEAD_WEEKS)
    raw[TARGET_COL] = raw.groupby("region")[TARGET_COL].ffill().bfill().fillna(0)

    # region별 time_idx 0부터
    raw[TIME_IDX_COL] = raw.groupby("region").cumcount()

    # 너무 짧은 region 제외
    counts = raw.groupby("region").size()
    valid = counts[counts >= min_weeks].index
    raw = raw[raw["region"].isin(valid)].reset_index(drop=True)

    if raw.empty:
        raise RuntimeError(
            f"학습 가능한 region 없음 (min_weeks={min_weeks}주 미만). "
            "더 많은 데이터를 수집한 뒤 재시도하세요."
        )

    logger.info("학습 DataFrame: %d행 × %d region (각 평균 %d주)",
                len(raw), raw["region"].nunique(), int(counts[valid].mean()))
    return raw[[TIME_IDX_COL, GROUP_COL, *FEATURE_COLS, TARGET_COL]]


def main() -> int:
    parser = argparse.ArgumentParser(description="TFT 실데이터 학습 (TimescaleDB)")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--regions", type=int, default=17, help="(미사용 — DB의 모든 region 사용)")
    parser.add_argument("--weeks", type=int, default=26, help="분석창 (메타정보 only)")
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--min-weeks", type=int, default=14, help="region당 최소 주차 (encoder=12 + pred=2)")
    parser.add_argument("--pathogen", type=str, default="influenza")
    parser.add_argument("--output", type=Path, default=OUTPUT_PATH)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    pl.seed_everything(42, workers=True)

    try:
        df = _build_dataframe_from_db(pathogen=args.pathogen, min_weeks=args.min_weeks)
    except RuntimeError as exc:
        logger.error("실데이터 로드 실패: %s", exc)
        logger.info("Fallback 권장: python -m ml.tft.train_synth --epochs %d", args.epochs)
        return 2

    # train / val 분할
    val_cutoff = df[TIME_IDX_COL].max() - MAX_PREDICTION - 4
    train_df = df[df[TIME_IDX_COL] <= val_cutoff].reset_index(drop=True)
    val_df = df.reset_index(drop=True)

    train_ds = _build_dataset(train_df, training=True)
    val_ds = TimeSeriesDataSet.from_dataset(train_ds, val_df, predict=True, stop_randomization=True)

    train_loader = train_ds.to_dataloader(train=True, batch_size=args.batch_size, num_workers=0)
    val_loader = val_ds.to_dataloader(train=False, batch_size=args.batch_size, num_workers=0)

    model = TemporalFusionTransformer.from_dataset(
        train_ds,
        learning_rate=5e-4,        # D-5 안정화: 1e-3 → 5e-4 (수렴 속도 ↓, 안정성 ↑)
        hidden_size=32,            # 48 → 32 (capacity 축소, 26주 데이터에 적합)
        attention_head_size=4,
        dropout=0.25,              # 0.15 → 0.25 (정규화 강화)
        hidden_continuous_size=12, # 16 → 12 (capacity 동조)
        output_size=7,
        loss=QuantileLoss(),
        log_interval=0,
        reduce_on_plateau_patience=3,  # 4 → 3 (작은 데이터셋, 빠른 LR 감쇠)
        # NOTE: pytorch_forecasting 1.7 의 TFT 는 optimizer/weight_decay 인자를
        # 직접 받지 않음. 정규화는 dropout=0.25 + SWA + EarlyStopping 으로 대체.
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
    early_stop = EarlyStopping(
        monitor="val_loss",
        patience=10,
        mode="min",
        min_delta=0.05,        # 0.001 → 0.05: noise 무시, 진짜 개선만 인정
    )
    # SWA: 후반 epoch 가중치 평균화로 generalization 개선 (작은 데이터셋에서 효과 큼)
    from lightning.pytorch.callbacks import StochasticWeightAveraging
    swa_cb = StochasticWeightAveraging(swa_lrs=2.5e-4, swa_epoch_start=0.6)

    trainer = pl.Trainer(
        max_epochs=args.epochs,
        accelerator="cpu",
        gradient_clip_val=0.1,
        callbacks=[ckpt_cb, early_stop, swa_cb],
        logger=csv_logger,
        enable_progress_bar=False,
        enable_model_summary=False,
        deterministic=True,        # 재현성 (seed_everything 와 함께)
    )

    logger.info("TFT 실데이터 학습 시작 (epochs=%d · batch=%d)", args.epochs, args.batch_size)
    trainer.fit(model, train_dataloaders=train_loader, val_dataloaders=val_loader)

    # 학습 곡선
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

    # 검증 예측
    pred = model.predict(val_loader, mode="prediction")
    pred_t = torch.as_tensor(pred) if not isinstance(pred, torch.Tensor) else pred
    pred_summary = {
        "n_samples": int(pred_t.shape[0]) if pred_t.ndim >= 1 else 1,
        "horizon_steps": int(pred_t.shape[1]) if pred_t.ndim >= 2 else None,
        "mean_pred_per_horizon": pred_t.float().mean(dim=0).tolist() if pred_t.ndim >= 2 else float(pred_t.mean()),
    }

    attn = _attention_summary_real(model, val_ds)

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": {
            "data_source": "real_db",
            "pathogen": args.pathogen,
            "n_weeks_meta": args.weeks,
            "n_regions": int(df[GROUP_COL].nunique()),
            "n_rows": int(len(df)),
            "max_epochs": args.epochs,
            "batch_size": args.batch_size,
            "max_encoder_length": MAX_ENCODER,
            "max_prediction_length": MAX_PREDICTION,
            "feature_cols": FEATURE_COLS,
            "target_col": TARGET_COL,
            "min_weeks_per_region": args.min_weeks,
        },
        "model_params": int(sum(p.numel() for p in model.parameters())),
        "best_checkpoint": str(ckpt_cb.best_model_path) if ckpt_cb.best_model_path else None,
        "best_val_loss": float(ckpt_cb.best_model_score) if ckpt_cb.best_model_score is not None else None,
        "loss_curve_tail": loss_curve[-30:],
        "prediction_summary": pred_summary,
        "attention_summary": attn,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("결과 저장: %s", args.output)

    print("\n=== TFT 실데이터 학습 요약 ===")
    print(f"  region 수: {result['config']['n_regions']}")
    print(f"  학습 행: {result['config']['n_rows']}")
    print(f"  파라미터: {result['model_params']:,}")
    print(f"  best_val_loss: {result['best_val_loss']}")
    print(f"  best ckpt: {result['best_checkpoint']}")
    if attn and attn.get("attention_summary_kr"):
        print(f"  attention top-3: {attn['attention_summary_kr']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
