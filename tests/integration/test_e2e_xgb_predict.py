"""통합 테스트: ML serve.py /predict/risk → risk_score + confidence 검증.

XGBoost 체크포인트가 없으면 pytest.skip.
체크포인트 있으면 실제 예측값이 0~100 사이인지 확인.
"""
from __future__ import annotations

import pytest
from pathlib import Path

_CHECKPOINT = Path(__file__).parent.parent.parent / "ml" / "checkpoints" / "xgb_best.joblib"


def test_xgb_predict_endpoint_schema():
    """ML serve FastAPI /predict/risk 엔드포인트 스키마 검증."""
    if not _CHECKPOINT.exists():
        pytest.skip("ml/checkpoints/xgb_best.joblib 없음 — 학습 후 재실행")

    from starlette.testclient import TestClient
    from ml.serve import app as ml_app

    with TestClient(ml_app) as c:
        resp = c.get(
            "/predict/risk",
            params={"l1": 62.5, "l2": 71.0, "l3": 48.3,
                    "temperature": 12.0, "humidity": 65.0,
                    "region": "서울특별시"},
        )

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()

    # 스키마 검증: composite_score (=risk_score), alert_level 존재
    assert "composite_score" in data, f"composite_score 키 없음: {data}"
    assert "alert_level" in data, f"alert_level 키 없음: {data}"
    score = data["composite_score"]
    assert score is not None, "composite_score 가 None"
    assert 0.0 <= score <= 100.0, f"score 범위 초과: {score}"


def test_xgb_model_no_checkpoint_returns_not_loaded():
    """체크포인트 없을 때 status=model_not_loaded 반환 확인."""
    from unittest.mock import patch
    from starlette.testclient import TestClient
    from ml.serve import app as ml_app
    import ml.serve as serve_mod

    # 강제로 모델 미로드 상태로 되돌리기
    original = serve_mod._xgb_model
    serve_mod._xgb_model = None

    with patch("ml.xgboost.model.load_model", return_value=None):
        with TestClient(ml_app) as c:
            resp = c.get("/predict/risk", params={"l1": 50, "l2": 50, "l3": 50})

    serve_mod._xgb_model = original

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "model_not_loaded", f"예상: model_not_loaded, 실제: {data['status']}"


def test_xgb_predict_with_synthetic_model():
    """합성 데이터로 학습한 임시 모델로 predict/risk 200 + 유효 score 확인."""
    from unittest.mock import patch
    from sklearn.ensemble import GradientBoostingRegressor
    import numpy as np
    import ml.serve as serve_mod
    from starlette.testclient import TestClient
    from ml.serve import app as ml_app

    # 합성 모델 생성 (실제 가중치/하이퍼파라미터 변경 없이 임시 인스턴스)
    synthetic = GradientBoostingRegressor(n_estimators=10, random_state=42)
    X = np.random.rand(50, 5) * 100
    y = np.random.rand(50) * 100
    synthetic.fit(X, y)

    original = serve_mod._xgb_model
    serve_mod._xgb_model = synthetic

    with TestClient(ml_app) as c:
        resp = c.get(
            "/predict/risk",
            params={"l1": 55.0, "l2": 65.0, "l3": 40.0,
                    "temperature": 10.0, "humidity": 70.0},
        )

    serve_mod._xgb_model = original

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert 0.0 <= data["composite_score"] <= 100.0
