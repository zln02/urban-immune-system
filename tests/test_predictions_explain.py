"""GET /api/v1/predictions/explain 단위 테스트.

TFT attention 기반 XAI 엔드포인트 동작 검증.
- tft_metrics.json 실제 파일 기반 (또는 mock) 결과 일치
- feature_importance 내림차순 정렬 확인
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from backend.app.api.predictions import _load_tft_metrics, get_prediction_explain

# 실제 tft_metrics.json 경로
_METRICS_PATH = (
    Path(__file__).parent.parent / "ml" / "outputs" / "tft_metrics.json"
)

# 테스트용 최소 metrics fixture
_MOCK_METRICS: dict = {
    "best_val_loss": 1.882218599319458,
    "config": {
        "max_encoder_length": 24,
        "max_prediction_length": 3,
        "feature_cols": ["l1_otc", "l2_wastewater", "l3_search", "temperature", "humidity"],
        "target_col": "confirmed_future",
    },
    "attention_summary": {
        "encoder_variable_names": [
            "encoder_length",
            "confirmed_future_center",
            "confirmed_future_scale",
            "time_idx",
            "relative_time_idx",
            "l1_otc",
            "l2_wastewater",
            "l3_search",
        ],
        "mean_encoder_variable_importance": [
            [0.152, 0.269, 0.092, 0.023, 0.062, 0.086, 0.224, 0.093]
        ],
        "mean_attention_per_encoder_step": [0.0417, 0.0416, 0.0416],
    },
}


def test_load_tft_metrics_real_file() -> None:
    """실제 파일이 존재하면 dict를 반환하고 attention_summary 키를 포함해야 한다."""
    if not _METRICS_PATH.exists():
        pytest.skip("tft_metrics.json 파일 없음 — 학습 후 재실행")
    metrics = _load_tft_metrics()
    assert isinstance(metrics, dict)
    assert "attention_summary" in metrics


def test_load_tft_metrics_file_missing(tmp_path: Path) -> None:
    """파일이 없을 때 빈 dict 를 반환해야 한다 (예외 발생 금지)."""
    from backend.app.api import predictions as pred_module
    original = pred_module._TFT_METRICS_PATH
    pred_module._TFT_METRICS_PATH = tmp_path / "nonexistent.json"
    try:
        result = _load_tft_metrics()
        assert result == {}
    finally:
        pred_module._TFT_METRICS_PATH = original


@pytest.mark.asyncio
async def test_explain_feature_importance_sorted_desc() -> None:
    """feature_importance 가 importance 내림차순 정렬되어야 한다."""
    with patch("backend.app.api.predictions._load_tft_metrics", return_value=_MOCK_METRICS):
        response = await get_prediction_explain(region="서울특별시")

    fi = response["feature_importance"]
    importances = [item["importance"] for item in fi]
    assert importances == sorted(importances, reverse=True), (
        f"feature_importance 정렬 오류: {importances}"
    )


@pytest.mark.asyncio
async def test_explain_rank_assignment() -> None:
    """rank 는 1부터 오름차순으로 부여되어야 한다."""
    with patch("backend.app.api.predictions._load_tft_metrics", return_value=_MOCK_METRICS):
        response = await get_prediction_explain(region="서울특별시")

    ranks = [item["rank"] for item in response["feature_importance"]]
    assert ranks == list(range(1, len(ranks) + 1))


@pytest.mark.asyncio
async def test_explain_matches_metrics_json_values() -> None:
    """feature_importance 값들이 tft_metrics.json 의 mean_encoder_variable_importance 와 일치해야 한다."""
    expected_vals = sorted(
        _MOCK_METRICS["attention_summary"]["mean_encoder_variable_importance"][0],
        reverse=True,
    )
    with patch("backend.app.api.predictions._load_tft_metrics", return_value=_MOCK_METRICS):
        response = await get_prediction_explain(region="서울특별시")

    actual_vals = [item["importance"] for item in response["feature_importance"]]
    assert len(actual_vals) == len(expected_vals)
    for a, e in zip(actual_vals, expected_vals):
        assert abs(a - e) < 1e-6, f"중요도 불일치: {a} != {e}"


@pytest.mark.asyncio
async def test_explain_required_keys() -> None:
    """응답에 필수 키가 모두 포함되어야 한다."""
    with patch("backend.app.api.predictions._load_tft_metrics", return_value=_MOCK_METRICS):
        response = await get_prediction_explain(region="서울특별시")

    required = {
        "region", "model", "model_version", "best_val_loss",
        "feature_importance", "attention_per_encoder_step",
        "encoder_variable_names", "config", "interpretation",
    }
    assert required.issubset(response.keys()), (
        f"누락된 키: {required - response.keys()}"
    )


@pytest.mark.asyncio
async def test_explain_region_passthrough() -> None:
    """요청한 region 값이 응답에 그대로 반환되어야 한다."""
    with patch("backend.app.api.predictions._load_tft_metrics", return_value=_MOCK_METRICS):
        for region in ("서울특별시", "부산광역시", "제주특별자치도"):
            response = await get_prediction_explain(region=region)
            assert response["region"] == region


@pytest.mark.asyncio
async def test_explain_empty_metrics_graceful() -> None:
    """tft_metrics.json 이 비어있어도 예외 없이 응답해야 한다."""
    with patch("backend.app.api.predictions._load_tft_metrics", return_value={}):
        response = await get_prediction_explain(region="서울특별시")
    assert response["feature_importance"] == []
    assert response["attention_per_encoder_step"] == []


@pytest.mark.asyncio
async def test_explain_top2_interpretation() -> None:
    """interpretation 문자열이 상위 2개 변수를 포함해야 한다."""
    with patch("backend.app.api.predictions._load_tft_metrics", return_value=_MOCK_METRICS):
        response = await get_prediction_explain(region="서울특별시")

    top2_vars = [fi["variable"] for fi in response["feature_importance"][:2]]
    interp = response["interpretation"]
    for var in top2_vars:
        assert var in interp, f"interpretation 에 {var} 가 없음: {interp}"


@pytest.mark.asyncio
async def test_explain_real_file_if_exists() -> None:
    """실제 tft_metrics.json 이 있으면 실제 파일로 end-to-end 확인."""
    if not _METRICS_PATH.exists():
        pytest.skip("tft_metrics.json 없음")
    response = await get_prediction_explain(region="서울특별시")
    assert len(response["feature_importance"]) > 0
    # 정렬 재확인
    importances = [item["importance"] for item in response["feature_importance"]]
    assert importances == sorted(importances, reverse=True)
