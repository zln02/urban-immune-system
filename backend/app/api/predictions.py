"""예측 API — ML 서비스 연동 + DB fallback."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import torch
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.prediction_service import get_risk_prediction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])

# ── Autoencoder 싱글톤 캐시 ──────────────────────────────────────────────────
# RAG 벡터DB 패턴과 동일 (alerts.py:304-317 참조): 모듈 첫 로드 시 1회 초기화
_AUTOENCODER_CACHE: dict[str, Any] | None | bool = None  # None=미시도, False=실패

# 체크포인트 경로 — predictions.py → api/ → app/ → backend/ → project_root
_CKPT_DIR = Path(__file__).parent.parent.parent.parent / "ml" / "checkpoints" / "autoencoder"

# 전국 17개 시·도 목록 (korea-regions.ts 와 동일 순서)
_KR_REGIONS = [
    "서울특별시", "경기도", "인천광역시", "강원특별자치도",
    "충청북도", "충청남도", "대전광역시", "세종특별자치시",
    "전라북도", "전라남도", "광주광역시",
    "경상북도", "경상남도", "대구광역시", "울산광역시", "부산광역시",
    "제주특별자치도",
]


def _load_autoencoder() -> dict[str, Any]:
    """Autoencoder 체크포인트를 로드해 캐시 dict 반환.

    Returns:
        {model, threshold, X_min, X_max, feature_cols, threshold_percentile}
    Raises:
        RuntimeError: 체크포인트 파일이 없거나 로드 실패 시
    """
    global _AUTOENCODER_CACHE
    if isinstance(_AUTOENCODER_CACHE, dict):
        return _AUTOENCODER_CACHE
    if _AUTOENCODER_CACHE is False:
        raise RuntimeError("Autoencoder 로드 실패 (이전 시도에서 오류 발생)")

    meta_path = _CKPT_DIR / "meta.json"
    model_path = _CKPT_DIR / "model.pt"
    if not meta_path.exists() or not model_path.exists():
        _AUTOENCODER_CACHE = False
        raise RuntimeError("Autoencoder 체크포인트 없음")

    try:
        from ml.anomaly.autoencoder import SignalAutoencoder
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        input_dim = meta.get("input_dim", 4)
        model = SignalAutoencoder(input_dim=input_dim)
        model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
        model.eval()
        _AUTOENCODER_CACHE = {
            "model": model,
            "threshold": float(meta["threshold"]),
            "threshold_percentile": float(meta.get("threshold_percentile", 95.0)),
            "X_min": np.array(meta["X_min"], dtype=np.float32),
            "X_max": np.array(meta["X_max"], dtype=np.float32),
            "feature_cols": meta["feature_cols"],
        }
        logger.info("Autoencoder 체크포인트 로드 완료: threshold=%.5f", meta["threshold"])
        return _AUTOENCODER_CACHE  # type: ignore[return-value]
    except Exception as exc:
        _AUTOENCODER_CACHE = False
        logger.error("Autoencoder 로드 오류: %s", exc)
        raise RuntimeError(f"Autoencoder 로드 오류: {exc}") from exc

# tft_metrics.json 경로 — 프로젝트 루트 기준
# predictions.py → api/ → app/ → backend/ → project_root
_TFT_METRICS_PATH = Path(__file__).parent.parent.parent.parent / "ml" / "outputs" / "tft_metrics.json"


def _load_tft_metrics() -> dict:
    """ml/outputs/tft_metrics.json 을 읽어 반환. 파일 없으면 빈 dict."""
    try:
        return json.loads(_TFT_METRICS_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("tft_metrics.json 로드 실패: %s", exc)
        return {}


@router.get("/forecast")
async def get_forecast(
    region: str = Query("서울특별시", min_length=2, max_length=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """ML 모델 기반 위험도 예측 (ML 서비스 미연결 시 가중평균 fallback).

    최근 28일 평균(value > 0)으로 단일 시점 noise를 흡수.
    """
    query = text("""
        SELECT layer, AVG(value) AS value
        FROM layer_signals
        WHERE region = :region
          AND layer IN ('otc', 'wastewater', 'search', 'aux')
          AND time >= NOW() - INTERVAL '28 days'
          AND value > 0
        GROUP BY layer
    """)
    result = await db.execute(query, {"region": region})
    signals = {r["layer"]: float(r["value"]) for r in result.mappings().all()}

    if not signals:
        return {
            "region": region,
            "status": "no_data",
            "message": "DB에 신호 데이터가 없습니다. 수집기를 먼저 실행하세요.",
        }

    l1 = signals.get("otc", 0.0)
    l2 = signals.get("wastewater", 0.0)
    l3 = signals.get("search", 0.0)
    aux = signals.get("aux", 15.0)

    try:
        return await get_risk_prediction(
            l1=l1, l2=l2, l3=l3, temperature=aux, region=region,
        )
    except Exception as exc:
        logger.warning("ML 서비스 미연결, fallback 사용: %s", exc)
        score = round(0.35 * l1 + 0.40 * l2 + 0.25 * l3, 2)
        level = "GREEN" if score < 30 else "YELLOW" if score < 55 else "RED"
        return {
            "region": region,
            "status": "fallback",
            "composite_score": score,
            "alert_level": level,
            "l1_score": l1,
            "l2_score": l2,
            "l3_score": l3,
            "message": "ML 서비스 미연결 — 가중평균 fallback",
        }


@router.get("/explain")
async def get_prediction_explain(
    region: str = Query("서울특별시", min_length=2, max_length=100),
) -> dict:
    """TFT attention 기반 예측 설명 (XAI).

    ml/outputs/tft_metrics.json 의 attention_summary 를 읽어
    변수 중요도(feature_importance)와 encoder step별 attention 가중치를 반환한다.
    region 파라미터는 현재 전역 모델 기준(단일 응답)이지만,
    향후 지역별 attention 분리를 위해 시그니처에 포함한다.
    """
    metrics = _load_tft_metrics()
    attention = metrics.get("attention_summary") or {}
    config = metrics.get("config") or {}

    # 변수명과 중요도 매핑
    raw_importance: list[list[float]] = attention.get("mean_encoder_variable_importance") or []
    # shape 이 [[v1, v2, ...]] (1행 × n_vars) 또는 [v1, v2, ...] 모두 처리
    if raw_importance and isinstance(raw_importance[0], list):
        importance_vals: list[float] = raw_importance[0]
    elif raw_importance and isinstance(raw_importance[0], (int, float)):
        importance_vals = [float(v) for v in raw_importance]  # type: ignore[arg-type]
    else:
        importance_vals = []

    var_names: list[str] = attention.get("encoder_variable_names") or []
    # importance 값 개수에 맞춰 변수명 슬라이싱 (TFT x_reals 순서 유지)
    n_vars = len(importance_vals)
    if len(var_names) > n_vars:
        var_names = var_names[:n_vars]
    elif len(var_names) < n_vars:
        # 이름이 부족하면 generic fallback
        var_names = var_names + [f"var_{i}" for i in range(len(var_names), n_vars)]

    # importance 내림차순 정렬 + rank 부여
    paired = sorted(
        zip(var_names, importance_vals),
        key=lambda x: x[1],
        reverse=True,
    )
    feature_importance = [
        {"variable": name, "importance": round(imp, 6), "rank": rank}
        for rank, (name, imp) in enumerate(paired, start=1)
    ]

    # 해석 문자열 — 상위 2개 변수 기반 자동 생성
    top2: list[str] = [str(fi["variable"]) for fi in feature_importance[:2]]
    interpretation = (
        f"{top2[0]}와 {top2[1]}가 가장 중요한 결정 요인"
        if len(top2) == 2
        else (f"{top2[0]}가 가장 중요한 결정 요인" if top2 else "변수 정보 없음")
    )

    return {
        "region": region,
        "model": "TFT-temporal_fusion_transformer",
        "model_version": "tft_synth_v2",
        "best_val_loss": metrics.get("best_val_loss"),
        "feature_importance": feature_importance,
        "attention_per_encoder_step": attention.get("mean_attention_per_encoder_step") or [],
        "encoder_variable_names": attention.get("encoder_variable_names") or [],
        "config": {
            "max_encoder_length": config.get("max_encoder_length"),
            "max_prediction_length": config.get("max_prediction_length"),
            "feature_cols": config.get("feature_cols"),
            "target_col": config.get("target_col"),
        },
        "interpretation": interpretation,
    }


@router.get("/anomaly")
async def get_anomaly_scores(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """전국 17개 시·도 Autoencoder 이상탐지 스코어.

    체크포인트(ml/checkpoints/autoencoder/) 기반 추론:
    - 체크포인트 없으면 503 반환
    - 각 지역 최신 L1/L2/L3/temperature 피처 조회 후 재구성 오차 계산
    - 스코어 0~100 (50 = 임계값)
    """
    # 1) 모델 로드 (캐시된 경우 즉시 반환)
    try:
        cache = _load_autoencoder()
    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Autoencoder 미학습 — "
                "`python -m ml.anomaly.train_synth --save-checkpoint` 실행 필요"
            ),
        ) from exc

    model: Any = cache["model"]
    threshold: float = cache["threshold"]
    threshold_percentile: float = cache["threshold_percentile"]
    X_min: np.ndarray = cache["X_min"]
    X_max: np.ndarray = cache["X_max"]
    span = np.maximum(X_max - X_min, 1e-6)

    # 2) 17개 지역 최신 L1/L2/L3 조회 (risk_scores 최신 1 row)
    risk_query = text("""
        SELECT DISTINCT ON (region)
            region, l1_score, l2_score, l3_score
        FROM risk_scores
        WHERE region = ANY(:regions)
        ORDER BY region, time DESC
    """)
    risk_result = await db.execute(risk_query, {"regions": _KR_REGIONS})
    risk_map: dict[str, dict] = {
        row["region"]: dict(row)
        for row in risk_result.mappings().all()
    }

    # 3) temperature — layer_signals AUX/weather
    temp_query = text("""
        SELECT DISTINCT ON (region)
            region, value
        FROM layer_signals
        WHERE region = ANY(:regions)
          AND layer = 'AUX'
          AND source LIKE '%weather%'
        ORDER BY region, time DESC
    """)
    temp_result = await db.execute(temp_query, {"regions": _KR_REGIONS})
    temp_map: dict[str, float] = {
        row["region"]: float(row["value"])
        for row in temp_result.mappings().all()
    }

    # 4) 지역별 추론
    anomaly_scores: list[dict] = []
    for region in _KR_REGIONS:
        risk = risk_map.get(region, {})
        l1 = float(risk.get("l1_score") or 0.0)
        l2 = float(risk.get("l2_score") or 0.0)
        l3 = float(risk.get("l3_score") or 0.0)
        fallback_temperature = region not in temp_map
        temperature = temp_map.get(region, 20.0)

        # 정규화 (체크포인트 X_min/X_max 기준)
        raw_feat = np.array([[l1, l2, l3, temperature]], dtype=np.float32)
        normalized = np.clip((raw_feat - X_min) / span, -0.5, 1.5)

        # reconstruction_error
        with torch.no_grad():
            tensor = torch.FloatTensor(normalized)
            error = float(model.reconstruction_error(tensor).numpy()[0])

        # 0~100 스케일 매핑 (50 = 임계값)
        score = round(min(error / threshold * 50.0, 100.0), 2)

        # status 판정
        if error > threshold:
            status = "anomaly"
        elif error > threshold * 0.7:
            status = "warning"
        else:
            status = "normal"

        anomaly_scores.append({
            "region": region,
            "score": score,
            "reconstruction_error": round(error, 6),
            "status": status,
            "features": {
                "l1": round(l1, 2),
                "l2": round(l2, 2),
                "l3": round(l3, 2),
                "temperature": round(temperature, 2),
            },
            "fallback_temperature": fallback_temperature,
        })

    return {
        "model": "autoencoder",
        "threshold": round(threshold, 6),
        "threshold_percentile": threshold_percentile,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "anomaly_scores": anomaly_scores,
    }
