"""per-horizon 예측기 — 분위 GBM 앙상블(점예측+예측구간) + 유행 조기경보 분류기.

설계:
- 점예측: XGBoost + LightGBM 앙상블. persistence 대비 '변화량(delta)' 을 학습해
  잔차 학습으로 단순 지속모델을 능가하도록 함. ŷ = wili_t + mean(Δ̂).
- 예측구간: XGBoost 다분위(reg:quantileerror) 로 [0.025,0.25,0.5,0.75,0.975] 산출 → WIS 평가.
- 조기경보: XGBoost 분류기로 P(h주 후 유행) 추정 → baseline 교차 조기 알람.

모든 모델은 walk-forward 에서 '검증 시즌 이전' 데이터로만 학습된다(validate.py 가 보장).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from lightgbm import LGBMRegressor
from xgboost import XGBClassifier, XGBRegressor

from ml.forecast.features import HORIZONS, feature_matrix

logger = logging.getLogger(__name__)

QUANTILES: list[float] = [0.025, 0.25, 0.5, 0.75, 0.975]

_XGB_REG = dict(n_estimators=350, max_depth=4, learning_rate=0.04,
                subsample=0.85, colsample_bytree=0.85, min_child_weight=3,
                reg_lambda=1.5, random_state=42, n_jobs=4)
_LGB_REG = dict(n_estimators=400, max_depth=5, num_leaves=31, learning_rate=0.04,
                subsample=0.85, colsample_bytree=0.85, min_child_samples=20,
                reg_lambda=1.5, random_state=42, n_jobs=4, verbose=-1)
_XGB_CLF = dict(n_estimators=300, max_depth=4, learning_rate=0.05,
                subsample=0.85, colsample_bytree=0.85, min_child_weight=3,
                reg_lambda=1.5, random_state=42, n_jobs=4, eval_metric="logloss")


@dataclass
class HorizonModel:
    """단일 지평 h 에 대한 점/구간/경보 모델 묶음."""
    h: int
    feats: list[str]
    xgb_delta: XGBRegressor | None = None
    lgb_delta: LGBMRegressor | None = None
    xgb_quant: XGBRegressor | None = None
    clf: XGBClassifier | None = None
    clf_trivial: float | None = None  # 단일클래스 시 상수확률

    def fit(self, df: pd.DataFrame) -> "HorizonModel":
        y = df[f"y_{self.h}"].to_numpy()
        X = df[self.feats].to_numpy()
        delta = y - df["wili"].to_numpy()  # persistence 대비 변화량

        self.xgb_delta = XGBRegressor(**_XGB_REG).fit(X, delta)
        self.lgb_delta = LGBMRegressor(**_LGB_REG).fit(X, delta)
        self.xgb_quant = XGBRegressor(
            objective="reg:quantileerror",
            quantile_alpha=np.array(QUANTILES),
            **_XGB_REG,
        ).fit(X, y)

        lab = df[f"label_{self.h}"].to_numpy()
        if len(np.unique(lab)) < 2:
            self.clf_trivial = float(lab.mean())
        else:
            self.clf = XGBClassifier(**_XGB_CLF).fit(X, lab)
        return self

    def predict_point(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.feats].to_numpy()
        base = df["wili"].to_numpy()
        d = 0.5 * (self.xgb_delta.predict(X) + self.lgb_delta.predict(X))
        return np.clip(base + d, 0.0, None)

    def predict_quantiles(self, df: pd.DataFrame) -> np.ndarray:
        """반환 shape (n, len(QUANTILES)) — 각 행 비감소 정렬·음수 클립."""
        X = df[self.feats].to_numpy()
        q = self.xgb_quant.predict(X)
        if q.ndim == 1:
            q = q.reshape(-1, 1)
        q = np.clip(q, 0.0, None)
        q.sort(axis=1)  # 분위 교차(quantile crossing) 보정
        return q

    def predict_alarm(self, df: pd.DataFrame) -> np.ndarray:
        X = df[self.feats].to_numpy()
        if self.clf is not None:
            return self.clf.predict_proba(X)[:, 1]
        return np.full(len(df), self.clf_trivial if self.clf_trivial is not None else 0.0)


@dataclass
class Forecaster:
    """전 지평 예측기. fit() 한 번에 모든 horizon 모델 학습."""
    horizons: list[int] = field(default_factory=lambda: list(HORIZONS))
    models: dict[int, HorizonModel] = field(default_factory=dict)
    feats: list[str] = field(default_factory=list)

    def fit(self, train_df: pd.DataFrame, extra_feats: list[str] | None = None) -> "Forecaster":
        self.feats = feature_matrix(train_df, extra=extra_feats)
        for h in self.horizons:
            sub = train_df.dropna(subset=self.feats + [f"y_{h}", f"label_{h}"])
            self.models[h] = HorizonModel(h=h, feats=self.feats).fit(sub)
        return self

    def predict(self, df: pd.DataFrame, h: int) -> dict[str, np.ndarray]:
        m = self.models[h]
        return {
            "point": m.predict_point(df),
            "quantiles": m.predict_quantiles(df),
            "alarm": m.predict_alarm(df),
        }


# ─── 기준(benchmark) 모델 — skill 비교용 ────────────────────────────────────

def persistence(df: pd.DataFrame, h: int) -> np.ndarray:
    """ŷ_{t+h} = wili_t (단순 지속)."""
    return df["wili"].to_numpy()


def climatology(df: pd.DataFrame, h: int) -> np.ndarray:
    """ŷ_{t+h} = 권역·주차 기후학적 기대값(과거 평균, 누출 없음)."""
    return df["clim_woy"].to_numpy()
