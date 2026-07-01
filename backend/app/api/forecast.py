"""실 임상(CDC ILINet) 기반 사전예측 모델 결과 제공 라우터.

ml/forecast/ 파이프라인이 생성한 사전 산출 JSON 을 읽어 제공한다(요청 시 모델 로드 없음).
- /validation : 시즌 단위 walk-forward 임상 검증 메트릭 (회귀 skill·WIS·경보·리드타임)
- /latest     : 권역별 최신주 기준 1–4주 선행 예측(점·95% 구간·유행경보확률)
- /regions    : 경보가 켜진 권역 요약
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/forecast", tags=["forecast"])

# 저장소 루트: backend/app/api/forecast.py → repo root
_OUTPUTS = Path(__file__).resolve().parents[3] / "analysis" / "outputs"
_VALIDATION = _OUTPUTS / "forecast_ilinet_validation.json"
_LATEST = _OUTPUTS / "forecast_ilinet_latest.json"


def _read(path: Path, what: str) -> dict:
    if not path.exists():
        raise HTTPException(
            status_code=503,
            detail=f"{what} 산출물이 아직 없습니다. `python -m ml.forecast.{path.stem.split('_')[-1]}` 로 생성하세요.",
        )
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("forecast 산출물 읽기 실패: %s", path)
        raise HTTPException(status_code=500, detail=f"{what} 산출물 파싱 실패") from exc


@router.get("/validation")
async def get_validation() -> dict:
    """실 임상 데이터 walk-forward 검증 메트릭 전체."""
    return _read(_VALIDATION, "검증")


@router.get("/latest")
async def get_latest() -> dict:
    """권역별 최신주 1–4주 선행 예측."""
    return _read(_LATEST, "최신예측")


@router.get("/regions")
async def get_regions() -> dict:
    """유행 경보(2주 후 baseline 초과 확률 높음) 권역 요약."""
    data = _read(_LATEST, "최신예측")
    summary = []
    for fc in data.get("forecasts", []):
        h2 = next((h for h in fc["horizons"] if h["h_weeks"] == 2), None)
        if h2 is None:
            continue
        summary.append({
            "region": fc["region"],
            "latest_epiweek": fc["latest_epiweek"],
            "current_wili": fc["current_wili"],
            "forecast_2w_wili": h2["point_wili"],
            "alarm_prob_2w": h2["epidemic_alarm_prob"],
            "above_baseline_2w": h2["above_baseline"],
        })
    summary.sort(key=lambda r: r["alarm_prob_2w"], reverse=True)
    return {"count": len(summary), "generated_at": data.get("generated_at"), "regions": summary}
