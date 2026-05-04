"""평가 지표 — MCC, AUPRC, Balanced Accuracy.

발표 정직성 강화: F1 단독 표기 → 클래스 불균형에서 더 엄격한 MCC·AUPRC 병기.

사용처:
- analysis/backtest_2025_flu.compute_confusion 에서 enrich_metrics 호출
- ml/xgboost/model.evaluate 에서 추가 평가
- tests/test_eval_metrics.py 회귀 검증
"""
from __future__ import annotations

import math
from typing import Any

import numpy as np
from sklearn.metrics import average_precision_score


def mcc_from_confusion(cm: dict[str, int]) -> float:
    """Matthews Correlation Coefficient — confusion matrix 만으로 계산.

    MCC = (TP·TN − FP·FN) / sqrt((TP+FP)·(TP+FN)·(TN+FP)·(TN+FN))

    범위: [-1, +1]
    - +1: 완벽 예측
    -  0: 무작위 예측 수준
    - -1: 완전히 반대로 예측

    클래스 불균형(우리 케이스: epidemic_label True 비율 ~50%) 에서도
    F1 보다 신뢰도 높음. F1 은 TN 을 무시하지만 MCC 는 4셀 모두 반영.

    Args:
        cm: {"TP": int, "FP": int, "FN": int, "TN": int}

    Returns:
        MCC ∈ [-1, 1]. 분모 0 이면 0.0 반환.
    """
    tp = cm.get("TP", 0)
    fp = cm.get("FP", 0)
    fn = cm.get("FN", 0)
    tn = cm.get("TN", 0)

    numerator = tp * tn - fp * fn
    denom_sq = (tp + fp) * (tp + fn) * (tn + fp) * (tn + fn)
    if denom_sq <= 0:
        return 0.0
    return numerator / math.sqrt(denom_sq)


def balanced_accuracy_from_confusion(cm: dict[str, int]) -> float:
    """클래스별 recall 평균 = (TPR + TNR) / 2.

    클래스 불균형 시 accuracy 가 majority class 에 편향되는 문제 회피.
    """
    tp, fp, fn, tn = cm.get("TP", 0), cm.get("FP", 0), cm.get("FN", 0), cm.get("TN", 0)
    tpr = tp / (tp + fn) if (tp + fn) > 0 else 0.0  # sensitivity / recall
    tnr = tn / (tn + fp) if (tn + fp) > 0 else 0.0  # specificity
    return (tpr + tnr) / 2


def auprc(y_true: list[int] | np.ndarray, y_score: list[float] | np.ndarray) -> float:
    """Area Under Precision-Recall Curve = average_precision_score.

    클래스 불균형(positive 희소) 에서 AUC-ROC 보다 정직한 지표.
    Saito & Rehmsmeier (2015) 권장 — "ROC 가 좋아 보여도 PR 곡선이 진실".

    Args:
        y_true: 0/1 binary label array
        y_score: 연속 점수 (raw composite score, probability 등)

    Returns:
        AUPRC ∈ [0, 1]. positive 비율보다 높으면 의미 있는 분류기.
        단일 클래스 입력 시 NaN.
    """
    y_true_arr = np.asarray(y_true, dtype=int)
    y_score_arr = np.asarray(y_score, dtype=float)
    if y_true_arr.size == 0 or len(np.unique(y_true_arr)) < 2:
        return float("nan")
    return float(average_precision_score(y_true_arr, y_score_arr))


def auprc_baseline(y_true: list[int] | np.ndarray) -> float:
    """AUPRC 의 무작위 분류기 baseline = positive 비율.

    AUPRC 가 이 값보다 높아야 의미 있는 분류기.
    """
    arr = np.asarray(y_true, dtype=int)
    if arr.size == 0:
        return float("nan")
    return float(arr.mean())


def enrich_metrics(
    cm: dict[str, int],
    y_true: list[int] | np.ndarray | None = None,
    y_score: list[float] | np.ndarray | None = None,
) -> dict[str, float]:
    """confusion matrix + (선택) raw scores 로 확장 메트릭 계산.

    기존 precision/recall/f1/far 위에 mcc, balanced_accuracy, auprc, auprc_baseline 추가.

    Args:
        cm: confusion matrix dict
        y_true: optional 0/1 라벨 (AUPRC 계산용)
        y_score: optional 연속 점수 (AUPRC 계산용)

    Returns:
        기존 + mcc + balanced_accuracy + auprc (입력 있으면) + auprc_baseline (입력 있으면)
    """
    tp, fp, fn, tn = cm.get("TP", 0), cm.get("FP", 0), cm.get("FN", 0), cm.get("TN", 0)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    far = fp / (fp + tn) if (fp + tn) > 0 else 0.0

    out: dict[str, Any] = {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "false_alarm_rate": round(far, 4),
        "mcc": round(mcc_from_confusion(cm), 4),
        "balanced_accuracy": round(balanced_accuracy_from_confusion(cm), 4),
    }
    if y_true is not None and y_score is not None:
        ap = auprc(y_true, y_score)
        out["auprc"] = round(ap, 4) if not math.isnan(ap) else None
        out["auprc_baseline"] = round(auprc_baseline(y_true), 4)
    return out


def aggregate_regional_metrics(per_region: dict[str, dict[str, float]]) -> dict[str, float]:
    """17지역 region별 메트릭 dict 를 평균/중앙값 집계.

    Args:
        per_region: {region: {"f1": ..., "mcc": ..., "auprc": ...}}

    Returns:
        mean / median 평균 dict
    """
    keys = ["precision", "recall", "f1", "false_alarm_rate", "mcc", "balanced_accuracy", "auprc"]
    out: dict[str, float] = {"n_regions": len(per_region)}
    for k in keys:
        vals = [
            m[k]
            for m in per_region.values()
            if m.get(k) is not None
            and not (isinstance(m[k], float) and math.isnan(m[k]))
        ]
        if vals:
            out[f"mean_{k}"] = round(float(np.mean(vals)), 4)
            out[f"median_{k}"] = round(float(np.median(vals)), 4)
    return out
