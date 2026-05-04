"""ml/xgboost/model.py 단위 테스트."""
from __future__ import annotations

import numpy as np


def test_generate_synthetic_data_shape() -> None:
    """합성 데이터가 올바른 형태로 생성되는지 확인."""
    from ml.xgboost.model import ALERT_COL, FEATURE_COLS, TARGET_COL, generate_synthetic_data

    df = generate_synthetic_data(n_weeks=52)
    assert len(df) == 52
    for col in FEATURE_COLS + [TARGET_COL, ALERT_COL]:
        assert col in df.columns


def test_generate_synthetic_data_ranges() -> None:
    """합성 데이터 값 범위가 0-100 내인지 확인."""
    from ml.xgboost.model import FEATURE_COLS, TARGET_COL, generate_synthetic_data

    df = generate_synthetic_data(n_weeks=104)
    for col in FEATURE_COLS[:3] + [TARGET_COL]:  # l1, l2, l3, composite
        assert df[col].min() >= 0.0, f"{col} min < 0"
        assert df[col].max() <= 100.0, f"{col} max > 100"


def test_generate_synthetic_data_has_both_classes() -> None:
    """합성 데이터에 경보/비경보 레이블이 모두 존재하는지 확인."""
    from ml.xgboost.model import ALERT_COL, generate_synthetic_data

    df = generate_synthetic_data(n_weeks=104)
    unique_labels = df[ALERT_COL].unique()
    assert 0 in unique_labels, "비경보(0) 레이블 누락"
    assert 1 in unique_labels, "경보(1) 레이블 누락"


def test_train_returns_metrics() -> None:
    """train()이 CV 점수와 최종 평가를 포함한 결과를 반환하는지 확인."""
    from ml.xgboost.model import generate_synthetic_data, train

    df = generate_synthetic_data(n_weeks=60)
    result = train(df, n_splits=3, gap=2)

    assert "cv_scores" in result
    assert "final_eval" in result
    assert "checkpoint" in result
    assert len(result["cv_scores"]) == 3


def test_evaluate_returns_all_metrics() -> None:
    """evaluate()가 F1, precision, recall, AUC-ROC, MAE를 모두 반환하는지 확인."""
    from ml.xgboost.model import evaluate, generate_synthetic_data, train

    df = generate_synthetic_data(n_weeks=60)
    train(df, n_splits=3, gap=2)

    from ml.xgboost.model import load_model
    model = load_model()
    assert model is not None

    metrics = evaluate(model, df)
    for key in ["mae", "f1", "precision", "recall", "auc_roc"]:
        assert key in metrics, f"{key} 지표 누락"


def test_predict_clips_output() -> None:
    """predict()가 0-100 범위로 클리핑하는지 확인."""
    from ml.xgboost.model import generate_synthetic_data, load_model, predict, train

    df = generate_synthetic_data(n_weeks=60)
    train(df, n_splits=3, gap=2)
    model = load_model()
    assert model is not None

    features = np.array([[80.0, 90.0, 70.0, 5.0, 30.0]])
    result = predict(model, features)
    assert result[0] >= 0.0
    assert result[0] <= 100.0


def test_f1_score_meets_target() -> None:
    """XGBoost F1 >= 0.70 캡스톤 목표 달성 확인."""
    from ml.xgboost.model import evaluate, generate_synthetic_data, load_model, train

    df = generate_synthetic_data(n_weeks=104)
    train(df, n_splits=5, gap=4)
    model = load_model()
    assert model is not None

    metrics = evaluate(model, df)
    assert metrics["f1"] >= 0.70, f"F1={metrics['f1']:.3f} < 0.70 목표 미달"
