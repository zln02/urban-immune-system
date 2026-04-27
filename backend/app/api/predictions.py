"""예측 API — ML 서비스 연동 + DB fallback."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..services.prediction_service import get_risk_prediction

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/predictions", tags=["predictions"])

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
    top2 = [fi["variable"] for fi in feature_importance[:2]]
    interpretation = (
        f"{top2[0]}와 {top2[1]}가 가장 중요한 결정 요인"
        if len(top2) == 2
        else (top2[0] + "가 가장 중요한 결정 요인" if top2 else "변수 정보 없음")
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
    region: str = Query("서울특별시", min_length=2, max_length=100),
    days: int = Query(28, ge=7, le=365),
) -> dict:
    """이상탐지 스코어 (Autoencoder 재구성 오차) — Phase 3 스텁.

    ml/anomaly/autoencoder.py 학습 후 연결 예정. 발표 시점에는 미구현 명시.
    """
    return {
        "region": region,
        "days": days,
        "anomaly_scores": [],
        "status": "not_implemented",
        "message": "Autoencoder 학습 미완 — Phase 3 로드맵 (ml/anomaly/autoencoder.py)",
    }
