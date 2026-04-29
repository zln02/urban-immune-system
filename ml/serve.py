"""ML inference service entrypoint."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import List

import numpy as np
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)
app = FastAPI(title="Urban Immune System ML Service", version="0.3.0")

# Lazy-loaded models
_xgb_model = None
_tft_model = None

# TFT 체크포인트 경로
_TFT_CKPT = Path(__file__).parent / "checkpoints" / "tft_synth" / "tft_best.ckpt"

# Attention 변수 레이블 매핑 (TFT encoder variable selection 순서 기준)
_ATTN_LABELS = {
    "encoder_length": "인코더길이",
    "confirmed_future_center": "타깃중심",
    "confirmed_future_scale": "타깃스케일",
    "l1_otc": "OTC약국판매",
    "l2_wastewater": "하수기반감시",
    "l3_search": "검색트렌드",
    "temperature": "기온",
    "humidity": "습도",
}

# encoder variable importance 순서 (train_synth.py 학습 기준)
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


class TFTPredictRequest(BaseModel):
    region: str = "서울특별시"
    horizon_weeks: int = 7


class TFTPredictResponse(BaseModel):
    region: str
    horizon: int
    predictions: List[float]
    attention_top3: List[str]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "ml"}


@app.get("/predict/risk")
async def predict_risk(
    l1: float = Query(50.0, ge=0, le=100),
    l2: float = Query(50.0, ge=0, le=100),
    l3: float = Query(50.0, ge=0, le=100),
    temperature: float = Query(15.0),
    humidity: float = Query(50.0),
    region: str = Query("서울특별시"),
) -> dict:
    """XGBoost 기반 위험도 예측."""
    global _xgb_model
    if _xgb_model is None:
        from ml.xgboost.model import load_model
        _xgb_model = load_model()

    if _xgb_model is None:
        return {
            "region": region,
            "status": "model_not_loaded",
            "composite_score": None,
            "alert_level": None,
        }

    features = np.array([[l1, l2, l3, temperature, humidity]])
    score = float(_xgb_model.predict(features)[0])
    score = max(0.0, min(100.0, score))

    # Alert level from CLAUDE.md ensemble rules
    if score < 30:
        level = "GREEN"
    elif score < 55:
        level = "YELLOW"
    elif score < 75:
        level = "ORANGE"
    else:
        level = "RED"

    return {
        "region": region,
        "status": "ok",
        "composite_score": round(score, 2),
        "alert_level": level,
        "model": "xgboost",
    }


def _load_tft():
    """TFT 모델을 지연 로드한다. 체크포인트 없으면 None 반환."""
    global _tft_model
    if _tft_model is not None:
        return _tft_model
    # tft_best.ckpt → 실제 best 체크포인트 (tft_synth/ 내 tft_best.ckpt 또는 버전별)
    ckpt_path = _TFT_CKPT
    if not ckpt_path.exists():
        # 버전별 파일 탐색 (tft_best-v2.ckpt 등)
        candidates = sorted(ckpt_path.parent.glob("tft_best*.ckpt"))
        if candidates:
            # 버전 번호가 가장 높은 파일 선택
            ckpt_path = candidates[-1]
        else:
            return None
    try:
        from pytorch_forecasting import TemporalFusionTransformer
        _tft_model = TemporalFusionTransformer.load_from_checkpoint(str(ckpt_path))
        _tft_model.eval()
        logger.info("TFT 체크포인트 로드 완료: %s", ckpt_path)
    except Exception as exc:
        logger.error("TFT 로드 실패: %s", exc)
        _tft_model = None
    return _tft_model


def _tft_attention_top3(model) -> list[str]:
    """학습된 encoder variable importance 기준 top-3 한국어 레이블 반환."""
    try:
        # 저장된 tft_metrics.json에서 attention 읽기 (추론 없이 빠른 응답)
        import json
        metrics_path = Path(__file__).parent / "outputs" / "tft_metrics.json"
        if metrics_path.exists():
            data = json.loads(metrics_path.read_text(encoding="utf-8"))
            importance = data.get("attention_summary", {}).get("mean_encoder_variable_importance")
            if importance and isinstance(importance[0], list):
                importance = importance[0]
            if importance and len(importance) >= len(_ENCODER_VAR_ORDER):
                pairs = list(zip(_ENCODER_VAR_ORDER, importance))
                # 실제 피처(L1/L2/L3/temp/humidity)만 필터링
                feature_vars = {"l1_otc", "l2_wastewater", "l3_search", "temperature", "humidity"}
                filtered = [(var, val) for var, val in pairs if var in feature_vars]
                filtered.sort(key=lambda x: x[1], reverse=True)
                return [_ATTN_LABELS.get(var, var) for var, _ in filtered[:3]]
    except Exception as exc:
        logger.warning("Attention top3 추출 실패: %s", exc)
    return ["검색트렌드", "하수기반감시", "OTC약국판매"]  # 기본값


def _make_tft_predictions(model, region: str, horizon_steps: int) -> list[float]:
    """합성 데이터로 horizon_steps 예측값(정규화 스코어 0-100) 반환."""
    import warnings
    import pandas as pd
    from ml.tft.train_synth import _make_dataframe, _build_dataset, MAX_PREDICTION
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            df = _make_dataframe(n_weeks=104, n_regions=1, seed=42)
            val_df = df.reset_index(drop=True)
            # train_ds로 val_ds 구성
            train_cutoff = df["time_idx"].max() - MAX_PREDICTION - 4
            train_df = df[df["time_idx"] <= train_cutoff].reset_index(drop=True)
            train_ds = _build_dataset(train_df, training=True)
            from pytorch_forecasting import TimeSeriesDataSet
            val_ds = TimeSeriesDataSet.from_dataset(train_ds, val_df, predict=True, stop_randomization=True)
            loader = val_ds.to_dataloader(train=False, batch_size=1, num_workers=0)
            import torch
            pred = model.predict(loader, mode="prediction")
            pred_t = torch.as_tensor(pred).float()
            # 3 horizon 값 (1주/2주/3주 = 7/14/21일)
            if pred_t.ndim >= 2:
                raw = pred_t[0].tolist()
            else:
                raw = [float(pred_t.mean())] * 3
            # 0-100 클리핑
            raw = [max(0.0, min(100.0, v)) for v in raw[:3]]
            # horizon_weeks → 필요한 step 수만큼 반환
            steps = max(1, horizon_steps // 7)
            steps = min(steps, 3)
            return raw[:steps]
    except Exception as exc:
        logger.error("TFT 추론 실패: %s", exc)
        raise


def _tft_predict_endpoint(horizon_days: int):
    """horizon_days(7/14/21)에 따른 TFT 예측 엔드포인트 공통 로직."""
    async def _endpoint(body: TFTPredictRequest) -> TFTPredictResponse:
        model = _load_tft()
        if model is None:
            raise HTTPException(
                status_code=503,
                detail="TFT 모델 미학습 — `python -m ml.tft.train_synth --epochs 50` 실행 필요",
            )
        predictions = _make_tft_predictions(model, body.region, horizon_days)
        attention_top3 = _tft_attention_top3(model)
        return TFTPredictResponse(
            region=body.region,
            horizon=horizon_days,
            predictions=predictions,
            attention_top3=attention_top3,
        )
    return _endpoint


@app.post("/predict/tft-7d", response_model=TFTPredictResponse)
async def predict_tft_7d(body: TFTPredictRequest) -> TFTPredictResponse:
    """TFT 기반 7일(1주) 선행 예측."""
    return await _tft_predict_endpoint(7)(body)


@app.post("/predict/tft-14d", response_model=TFTPredictResponse)
async def predict_tft_14d(body: TFTPredictRequest) -> TFTPredictResponse:
    """TFT 기반 14일(2주) 선행 예측."""
    return await _tft_predict_endpoint(14)(body)


@app.post("/predict/tft-21d", response_model=TFTPredictResponse)
async def predict_tft_21d(body: TFTPredictRequest) -> TFTPredictResponse:
    """TFT 기반 21일(3주) 선행 예측."""
    return await _tft_predict_endpoint(21)(body)
