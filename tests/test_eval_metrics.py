"""ml.evaluation.metrics 단위 테스트."""
from __future__ import annotations

import math

import pytest

from ml.evaluation.metrics import (
    aggregate_regional_metrics,
    auprc,
    auprc_baseline,
    balanced_accuracy_from_confusion,
    enrich_metrics,
    mcc_from_confusion,
)


class TestMCC:
    def test_perfect_prediction(self) -> None:
        cm = {"TP": 10, "FP": 0, "FN": 0, "TN": 10}
        assert mcc_from_confusion(cm) == pytest.approx(1.0)

    def test_completely_wrong(self) -> None:
        cm = {"TP": 0, "FP": 10, "FN": 10, "TN": 0}
        assert mcc_from_confusion(cm) == pytest.approx(-1.0)

    def test_random(self) -> None:
        cm = {"TP": 5, "FP": 5, "FN": 5, "TN": 5}
        assert mcc_from_confusion(cm) == pytest.approx(0.0)

    def test_realistic_case(self) -> None:
        # 17지역 백테스트 서울 케이스: TP=14, FP=0, FN=3, TN=4
        cm = {"TP": 14, "FP": 0, "FN": 3, "TN": 4}
        m = mcc_from_confusion(cm)
        # FP=0 이지만 TN=4 로 작아 MCC ~0.69
        assert 0.6 < m < 0.85

    def test_zero_denominator(self) -> None:
        # 한 셀이 모두 0 이라 분모 0 → 0.0 반환
        cm = {"TP": 10, "FP": 0, "FN": 0, "TN": 0}
        assert mcc_from_confusion(cm) == 0.0

    def test_empty(self) -> None:
        cm = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
        assert mcc_from_confusion(cm) == 0.0


class TestBalancedAccuracy:
    def test_perfect(self) -> None:
        cm = {"TP": 10, "FP": 0, "FN": 0, "TN": 10}
        assert balanced_accuracy_from_confusion(cm) == pytest.approx(1.0)

    def test_class_imbalance(self) -> None:
        # 100 negative 중 99 맞히고, 10 positive 중 5 맞힘
        # accuracy = (5+99)/(100+10)=0.945 (편향)
        # balanced_acc = (5/10 + 99/100)/2 = (0.5+0.99)/2=0.745
        cm = {"TP": 5, "FP": 1, "FN": 5, "TN": 99}
        bal = balanced_accuracy_from_confusion(cm)
        assert bal == pytest.approx(0.745, abs=0.01)


class TestAUPRC:
    def test_perfect_separation(self) -> None:
        y_true = [0, 0, 0, 1, 1, 1]
        y_score = [0.1, 0.2, 0.3, 0.7, 0.8, 0.9]
        assert auprc(y_true, y_score) == pytest.approx(1.0)

    def test_shuffled_score(self) -> None:
        # 점수와 라벨 무관 — AUPRC 가 baseline(0.5) 근처
        y_true = [0, 1, 0, 1, 0, 1, 0, 1]
        y_score = [0.5, 0.3, 0.6, 0.4, 0.5, 0.6, 0.4, 0.3]  # shuffle
        ap = auprc(y_true, y_score)
        # 범위는 넓게 — random 이라도 0~1 사이만 보장
        assert 0.0 <= ap <= 1.0
        # baseline 비교: positive 비율 = 0.5
        baseline = auprc_baseline(y_true)
        assert baseline == pytest.approx(0.5)

    def test_single_class(self) -> None:
        y_true = [1, 1, 1]
        y_score = [0.1, 0.2, 0.3]
        assert math.isnan(auprc(y_true, y_score))

    def test_baseline(self) -> None:
        assert auprc_baseline([0, 0, 1, 1]) == pytest.approx(0.5)
        assert auprc_baseline([0, 0, 0, 1]) == pytest.approx(0.25)


class TestEnrich:
    def test_with_scores(self) -> None:
        cm = {"TP": 14, "FP": 0, "FN": 3, "TN": 4}
        y_true = [1] * 17 + [0] * 4
        y_score = [0.9] * 14 + [0.4] * 3 + [0.1] * 4
        m = enrich_metrics(cm, y_true=y_true, y_score=y_score)
        assert "mcc" in m
        assert "balanced_accuracy" in m
        assert "auprc" in m
        assert "auprc_baseline" in m
        assert m["precision"] == pytest.approx(1.0)

    def test_without_scores(self) -> None:
        cm = {"TP": 5, "FP": 1, "FN": 1, "TN": 5}
        m = enrich_metrics(cm)
        assert "mcc" in m
        assert "auprc" not in m  # 스코어 없으면 생략


class TestAggregate:
    def test_mean_median(self) -> None:
        per_region = {
            "A": {"f1": 0.9, "mcc": 0.8, "auprc": 0.85, "precision": 1.0, "recall": 0.8, "false_alarm_rate": 0.1, "balanced_accuracy": 0.85},
            "B": {"f1": 0.8, "mcc": 0.7, "auprc": 0.75, "precision": 0.9, "recall": 0.7, "false_alarm_rate": 0.2, "balanced_accuracy": 0.75},
            "C": {"f1": 0.7, "mcc": 0.6, "auprc": 0.65, "precision": 0.8, "recall": 0.6, "false_alarm_rate": 0.3, "balanced_accuracy": 0.65},
        }
        agg = aggregate_regional_metrics(per_region)
        assert agg["n_regions"] == 3
        assert agg["mean_f1"] == pytest.approx(0.8)
        assert agg["mean_mcc"] == pytest.approx(0.7)
        assert agg["median_auprc"] == pytest.approx(0.75)
