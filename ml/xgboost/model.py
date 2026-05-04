"""XGBoost (scikit-learn GradientBoostingRegressor) 기반 위험도 예측 모델.

3계층 비의료 신호(L1 약국 OTC, L2 하수도, L3 검색)와 기상 데이터를
입력으로 받아 복합 위험 점수(0-100)를 출력한다.

Walk-forward TimeSeriesSplit 교차검증으로 시계열 미래 누출을 방지한다.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import TimeSeriesSplit

try:
    import joblib
except ImportError:  # joblib은 scikit-learn 의존성으로 항상 포함되어 있음
    raise ImportError("joblib이 설치되어 있지 않습니다. pip install joblib")

try:
    import yaml  # PyYAML — requirements.txt 확인
    _YAML_AVAILABLE = True
except ImportError:
    _YAML_AVAILABLE = False

logger = logging.getLogger(__name__)

# 체크포인트 경로 — __file__ 기준 상대경로
_CHECKPOINT_DIR = Path(__file__).parent.parent / "checkpoints"
_CHECKPOINT_PATH = _CHECKPOINT_DIR / "xgb_best.joblib"

# 설정 파일 경로
_CONFIG_PATH = Path(__file__).parent.parent / "configs" / "model_config.yaml"

# 피처 컬럼명
FEATURE_COLS = ["l1_otc", "l2_wastewater", "l3_search", "temperature", "humidity"]
TARGET_COL = "composite_score"
ALERT_COL = "alert_label"  # 이진 분류 레이블 (composite > 55 → 1)
ALERT_THRESHOLD = 55.0

# Hardened task 컬럼: t주 피처로 t+lead주 후 확진자 임계값 초과 예측 (선행 검증)
HARDENED_TARGET_COL = "confirmed_future"
HARDENED_ALERT_COL = "alert_future"
HARDENED_ALERT_THRESHOLD = 70.0


def _load_config() -> dict[str, Any]:
    """model_config.yaml에서 xgboost 설정을 로드한다. 없으면 기본값을 반환한다."""
    if _YAML_AVAILABLE and _CONFIG_PATH.exists():
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        return cfg.get("xgboost", {})
    logger.warning("model_config.yaml 로드 실패 — 기본 하이퍼파라미터 사용")
    return {}


def generate_synthetic_data(n_weeks: int = 104, seed: int = 42) -> pd.DataFrame:
    """104주(2년) 분량의 합성 역학 데이터를 생성한다.

    계절성 패턴:
    - 독감 피크: 겨울(12-2월)
    - L1 OTC: 확진 1-2주 선행
    - L2 하수도: 확진 2-3주 선행
    - L3 검색: 확진 1-2주 선행
    - 기온: 독감과 음의 상관관계

    Args:
        n_weeks: 생성할 주 수 (기본 104주 = 2년)
        seed: 재현성을 위한 랜덤 시드

    Returns:
        피처·타깃·경보 레이블이 포함된 DataFrame
    """
    rng = np.random.default_rng(seed)

    # 주 단위 시간축
    weeks = np.arange(n_weeks)

    # 기온: 15°C ± 15°C (겨울 최저 0°C, 여름 최고 30°C)
    temperature = 15.0 + 15.0 * np.cos(2 * np.pi * weeks / 52)
    temperature += rng.normal(0, 2.0, n_weeks)
    temperature = np.clip(temperature, -5.0, 38.0)

    # 습도: 겨울에 낮고 여름에 높음 (40-80%)
    humidity = 60.0 - 20.0 * np.cos(2 * np.pi * weeks / 52)
    humidity += rng.normal(0, 5.0, n_weeks)
    humidity = np.clip(humidity, 20.0, 95.0)

    # 확진 사례 지수 (0-100) — 겨울 피크 + 랜덤 노이즈
    # 2년 사이클: 2개의 겨울 피크
    confirmed_base = 40.0 - 35.0 * np.cos(2 * np.pi * weeks / 52)
    confirmed_base += rng.normal(0, 5.0, n_weeks)
    confirmed_base = np.clip(confirmed_base, 5.0, 95.0)

    # L2 하수도 — 2-3주 선행 (가장 이른 선행지표)
    lead_l2 = 3  # 주
    l2_base = np.roll(confirmed_base, -lead_l2)
    l2_base[:lead_l2] = confirmed_base[:lead_l2]  # 앞부분 채우기
    l2_wastewater = l2_base + rng.normal(0, 6.0, n_weeks)
    l2_wastewater = np.clip(l2_wastewater, 0.0, 100.0)

    # L1 OTC 약국 — 1-2주 선행
    lead_l1 = 2  # 주
    l1_base = np.roll(confirmed_base, -lead_l1)
    l1_base[:lead_l1] = confirmed_base[:lead_l1]
    l1_otc = l1_base + rng.normal(0, 8.0, n_weeks)
    l1_otc = np.clip(l1_otc, 0.0, 100.0)

    # L3 검색 트렌드 — 1-2주 선행 (노이즈 가장 많음)
    lead_l3 = 1  # 주
    l3_base = np.roll(confirmed_base, -lead_l3)
    l3_base[:lead_l3] = confirmed_base[:lead_l3]
    l3_search = l3_base + rng.normal(0, 10.0, n_weeks)
    l3_search = np.clip(l3_search, 0.0, 100.0)

    # 복합 위험 점수 — CLAUDE.md 앙상블 가중치 (L2 최우선)
    # w1=0.35, w2=0.40, w3=0.25
    composite_score = 0.35 * l1_otc + 0.40 * l2_wastewater + 0.25 * l3_search
    composite_score = np.clip(composite_score, 0.0, 100.0)

    # 이진 경보 레이블 (composite > 55 → 1)
    alert_label = (composite_score > ALERT_THRESHOLD).astype(int)

    # Hardened: 선행 검증용 — t주 피처로 t+2주 후 확진자(=confirmed_base) 임계값 초과 예측
    # 발표용 진짜 검증: "선행 신호로 미래 확진자 임계값 넘김 예측"
    confirmed_future = np.roll(confirmed_base, -2)  # 2주 후
    confirmed_future[-2:] = confirmed_base[-2:]
    alert_future = (confirmed_future > HARDENED_ALERT_THRESHOLD).astype(int)

    # 날짜 인덱스 (2023-01-02부터 주 단위)
    date_index = pd.date_range(start="2023-01-02", periods=n_weeks, freq="W-MON")

    df = pd.DataFrame(
        {
            "l1_otc": l1_otc,
            "l2_wastewater": l2_wastewater,
            "l3_search": l3_search,
            "temperature": temperature,
            "humidity": humidity,
            "composite_score": composite_score,
            "alert_label": alert_label,
            "confirmed_future": confirmed_future,
            "alert_future": alert_future,
        },
        index=date_index,
    )

    logger.info(
        "합성 데이터 생성 완료: %d주, 경보 비율=%.1f%%",
        n_weeks,
        alert_label.mean() * 100,
    )
    return df


def train(
    df: pd.DataFrame,
    n_splits: int = 5,
    gap: int = 4,
    target_col: str = TARGET_COL,
    alert_col: str = ALERT_COL,
    alert_threshold: float = ALERT_THRESHOLD,
    save_checkpoint: bool = True,
) -> dict[str, Any]:
    """Walk-forward TimeSeriesSplit으로 GradientBoostingRegressor를 학습·저장한다.

    Walk-forward 교차검증으로 미래 데이터 누출을 방지한다 (gap=4주).
    최종 모델은 전체 데이터로 재학습 후 체크포인트에 저장한다.

    Args:
        df: FEATURE_COLS + target_col + alert_col 컬럼을 포함한 DataFrame
        n_splits: TimeSeriesSplit 분할 수 (기본 5)
        gap: 훈련/검증 사이 갭 주 수 (미래 누출 방지, 기본 4)
        target_col: 회귀 타깃 컬럼 (composite_score 또는 confirmed_future)
        alert_col: 이진 경보 레이블 컬럼
        alert_threshold: 회귀값 → 이진 분류 임계값
        save_checkpoint: 최종 모델 디스크 저장 여부

    Returns:
        cv_scores, final_eval 등 학습 결과 요약 dict
    """
    cfg = _load_config()

    X = df[FEATURE_COLS].values
    y = df[target_col].values
    y_label = df[alert_col].values

    # 하이퍼파라미터: model_config.yaml > 기본값
    params: dict[str, Any] = {
        "n_estimators": cfg.get("n_estimators", 200),
        "max_depth": cfg.get("max_depth", 4),
        "learning_rate": cfg.get("learning_rate", 0.05),
        "subsample": cfg.get("subsample", 0.8),
        "min_samples_leaf": cfg.get("min_samples_leaf", 5),
        "random_state": cfg.get("random_state", 42),
    }
    logger.info("GradientBoostingRegressor 하이퍼파라미터: %s", params)

    # Walk-forward 교차검증
    tscv = TimeSeriesSplit(n_splits=n_splits, gap=gap)
    cv_scores: list[dict[str, float]] = []

    for fold_idx, (train_idx, val_idx) in enumerate(tscv.split(X)):
        X_train, X_val = X[train_idx], X[val_idx]
        y_train, y_val = y[train_idx], y[val_idx]
        y_label_val = y_label[val_idx]

        model_fold = GradientBoostingRegressor(**params)
        model_fold.fit(X_train, y_train)

        y_pred = model_fold.predict(X_val)
        y_pred_clipped = np.clip(y_pred, 0.0, 100.0)

        # 이진 레이블로 분류 지표 계산
        y_pred_label = (y_pred_clipped > alert_threshold).astype(int)

        mae = float(np.mean(np.abs(y_pred_clipped - y_val)))

        # 레이블이 한 클래스만 있는 경우 분류 지표 스킵
        if len(np.unique(y_label_val)) < 2 or len(np.unique(y_pred_label)) < 2:
            f1 = precision = recall = auc = float("nan")
        else:
            f1 = float(f1_score(y_label_val, y_pred_label, zero_division=0))
            precision = float(
                precision_score(y_label_val, y_pred_label, zero_division=0)
            )
            recall = float(recall_score(y_label_val, y_pred_label, zero_division=0))
            try:
                auc = float(roc_auc_score(y_label_val, y_pred_clipped))
            except ValueError:
                auc = float("nan")

        fold_score = {
            "fold": fold_idx + 1,
            "mae": mae,
            "f1": f1,
            "precision": precision,
            "recall": recall,
            "auc_roc": auc,
        }
        cv_scores.append(fold_score)
        logger.info(
            "Fold %d — MAE=%.2f, F1=%.3f, AUC=%.3f",
            fold_idx + 1,
            mae,
            f1,
            auc,
        )

    # 전체 데이터로 최종 모델 학습
    final_model = GradientBoostingRegressor(**params)
    final_model.fit(X, y)

    # 최종 모델 평가 (target_col 기반, evaluate는 ALERT_COL 고정이므로 별도 처리)
    final_pred = np.clip(final_model.predict(X), 0.0, 100.0)
    final_pred_label = (final_pred > alert_threshold).astype(int)
    final_eval: dict[str, Any] = {
        "mae": float(np.mean(np.abs(final_pred - y))),
        "target_col": target_col,
        "alert_col": alert_col,
        "alert_threshold": alert_threshold,
    }
    if len(np.unique(y_label)) >= 2 and len(np.unique(final_pred_label)) >= 2:
        final_eval["f1"] = float(f1_score(y_label, final_pred_label, zero_division=0))
        final_eval["precision"] = float(precision_score(y_label, final_pred_label, zero_division=0))
        final_eval["recall"] = float(recall_score(y_label, final_pred_label, zero_division=0))
        try:
            final_eval["auc_roc"] = float(roc_auc_score(y_label, final_pred))
        except ValueError:
            final_eval["auc_roc"] = float("nan")
    logger.info("최종 모델 평가: %s", final_eval)

    # 체크포인트 저장 (composite task만 — hardened는 발표용 평가, 추론에는 composite 모델 사용)
    if save_checkpoint:
        _CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(final_model, _CHECKPOINT_PATH)
        logger.info("모델 저장 완료: %s", _CHECKPOINT_PATH)

    # CV 요약 집계 (nan 제외)
    valid_scores = [s for s in cv_scores if not np.isnan(s["f1"])]
    summary: dict[str, Any] = {
        "cv_scores": cv_scores,
        "final_eval": final_eval,
        "checkpoint": str(_CHECKPOINT_PATH),
    }
    if valid_scores:
        summary["cv_mean_f1"] = float(np.mean([s["f1"] for s in valid_scores]))
        summary["cv_mean_mae"] = float(np.mean([s["mae"] for s in cv_scores]))
        summary["cv_mean_auc"] = float(
            np.mean([s["auc_roc"] for s in valid_scores if not np.isnan(s["auc_roc"])])
        )

    return summary


def load_model() -> GradientBoostingRegressor | None:
    """저장된 체크포인트에서 모델을 로드한다.

    체크포인트가 없으면 합성 데이터로 자동 학습 후 저장한다.

    Returns:
        로드된 GradientBoostingRegressor 또는 None (로드 실패 시)
    """
    if _CHECKPOINT_PATH.exists():
        try:
            model = joblib.load(_CHECKPOINT_PATH)
            logger.info("체크포인트 로드 완료: %s", _CHECKPOINT_PATH)
            return model  # type: ignore[return-value]
        except Exception as exc:
            logger.error("체크포인트 로드 실패: %s", exc)

    # 체크포인트 없음 → 합성 데이터로 초기 학습
    logger.warning("체크포인트 없음 — 합성 데이터로 초기 학습 시작")
    try:
        df = generate_synthetic_data()
        train(df)
        model = joblib.load(_CHECKPOINT_PATH)
        logger.info("초기 학습 완료, 모델 로드")
        return model  # type: ignore[return-value]
    except Exception as exc:
        logger.error("초기 학습 실패: %s", exc)
        return None


def predict(
    model: GradientBoostingRegressor,
    features: np.ndarray,
) -> np.ndarray:
    """주어진 피처 배열에 대해 복합 위험 점수를 예측한다.

    Args:
        model: 로드된 GradientBoostingRegressor
        features: shape (n_samples, 5) — [l1_otc, l2_wastewater, l3_search, temperature, humidity]

    Returns:
        0-100으로 클리핑된 복합 위험 점수 배열 (n_samples,)
    """
    raw = model.predict(features)
    return np.clip(raw, 0.0, 100.0)


def evaluate(
    model: GradientBoostingRegressor,
    df: pd.DataFrame,
) -> dict[str, float]:
    """모델 성능을 F1, Precision, Recall, AUC-ROC로 평가한다.

    Args:
        model: 평가할 GradientBoostingRegressor
        df: FEATURE_COLS + TARGET_COL + ALERT_COL 컬럼을 포함한 DataFrame

    Returns:
        f1, precision, recall, auc_roc, mae 지표 dict
    """
    X = df[FEATURE_COLS].values
    y_true = df[TARGET_COL].values
    y_label_true = df[ALERT_COL].values

    y_pred_raw = model.predict(X)
    y_pred = np.clip(y_pred_raw, 0.0, 100.0)
    y_pred_label = (y_pred > ALERT_THRESHOLD).astype(int)

    mae = float(np.mean(np.abs(y_pred - y_true)))

    if len(np.unique(y_label_true)) < 2 or len(np.unique(y_pred_label)) < 2:
        logger.warning("단일 클래스 데이터 — 분류 지표를 계산할 수 없음")
        return {
            "mae": mae,
            "f1": float("nan"),
            "precision": float("nan"),
            "recall": float("nan"),
            "auc_roc": float("nan"),
        }

    f1 = float(f1_score(y_label_true, y_pred_label, zero_division=0))
    precision = float(precision_score(y_label_true, y_pred_label, zero_division=0))
    recall = float(recall_score(y_label_true, y_pred_label, zero_division=0))

    try:
        auc = float(roc_auc_score(y_label_true, y_pred))
    except ValueError as exc:
        logger.warning("AUC-ROC 계산 실패: %s", exc)
        auc = float("nan")

    result = {
        "mae": mae,
        "f1": f1,
        "precision": precision,
        "recall": recall,
        "auc_roc": auc,
    }
    logger.info(
        "평가 결과 — MAE=%.2f, F1=%.3f, Precision=%.3f, Recall=%.3f, AUC=%.3f",
        mae, f1, precision, recall, auc,
    )
    return result
