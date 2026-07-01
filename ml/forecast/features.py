"""누수 없는 시계열 피처 엔지니어링.

원칙: 시각 t 의 피처는 t 시점까지 관측 가능한 정보만 사용한다(미래 누출 금지).
타깃 y_h 와 라벨 label_h 는 권역 내에서 -h 주 미래값으로 생성한다.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

# 예측 지평(주)
HORIZONS: list[int] = [1, 2, 3, 4]

# 모델 입력 피처 컬럼(아래 make_features 가 생성)
FEATURE_COLS: list[str] = [
    "wili", "wili_lag1", "wili_lag2", "wili_lag3", "wili_lag4",
    "diff1", "diff2", "slope3", "roll_mean4", "roll_std4", "roll_max4",
    "accel", "log_wili",
    "nat_wili", "nat_diff1", "ratio_nat",
    "sin_woy", "cos_woy", "week_of_season",
    "clim_woy", "wili_vs_clim", "baseline", "wili_vs_baseline",
]


def _add_region_features(g: pd.DataFrame) -> pd.DataFrame:
    """권역 1개 시계열에 대한 lag/momentum/seasonality 피처 (t까지만 사용)."""
    g = g.sort_values("epiweek").reset_index(drop=True)
    w = g["wili"]

    g["wili_lag1"] = w.shift(1)
    g["wili_lag2"] = w.shift(2)
    g["wili_lag3"] = w.shift(3)
    g["wili_lag4"] = w.shift(4)
    g["diff1"] = w.diff(1)
    g["diff2"] = w.diff(2)
    g["accel"] = g["diff1"] - g["diff1"].shift(1)
    # 최근 3주 선형 추세(기울기)
    g["slope3"] = (w - w.shift(3)) / 3.0
    g["roll_mean4"] = w.shift(1).rolling(4, min_periods=1).mean()
    g["roll_std4"] = w.shift(1).rolling(4, min_periods=2).std()
    g["roll_max4"] = w.shift(1).rolling(4, min_periods=1).max()
    g["log_wili"] = np.log1p(w)

    # 전국 맥락
    g["nat_diff1"] = g["nat_wili"].diff(1)
    g["ratio_nat"] = w / g["nat_wili"].replace(0, np.nan)

    # 계절성(MMWR week-of-year harmonic)
    g["sin_woy"] = np.sin(2 * np.pi * g["week"] / 52.0)
    g["cos_woy"] = np.cos(2 * np.pi * g["week"] / 52.0)

    g["wili_vs_baseline"] = w - g["baseline"]
    return g


def _add_climatology(df: pd.DataFrame) -> pd.DataFrame:
    """기후학적 기대값(clim_woy): 권역·주차별 과거 평균 wILI (expanding, 누출 방지).

    각 (region, week) 의 clim 은 그 행보다 이른 epiweek 들의 평균만 사용한다.
    """
    df = df.sort_values(["region", "week", "epiweek"]).reset_index(drop=True)
    # 같은 (region, week) 그룹 내에서 과거값들의 expanding mean (현재행 제외)
    grp = df.groupby(["region", "week"])["wili"]
    df["clim_woy"] = grp.transform(lambda s: s.expanding().mean().shift(1))
    # 시즌 첫 등장 등으로 NaN 이면 권역 평균으로 보완
    df["clim_woy"] = df["clim_woy"].fillna(df.groupby("region")["wili"].transform("mean"))
    df["wili_vs_clim"] = df["wili"] - df["clim_woy"]
    return df.sort_values(["region", "epiweek"]).reset_index(drop=True)


def make_features(panel: pd.DataFrame) -> pd.DataFrame:
    """패널 → 피처 + per-horizon 타깃/라벨.

    생성 타깃:
        y_h        : h주 후 wili (회귀 타깃)
        label_h    : h주 후 epidemic(유행) 여부 (이진 분류 타깃)
        onset_woy  : (이미 부착) 시즌 onset 주차 — 리드타임 평가용
    """
    df = pd.concat(
        [_add_region_features(g) for _, g in panel.groupby("region", sort=False)],
        ignore_index=True,
    )
    df = _add_climatology(df)

    # per-horizon 미래 타깃/라벨 (권역 내 shift -h)
    for h in HORIZONS:
        df[f"y_{h}"] = df.groupby("region")["wili"].shift(-h)
        df[f"label_{h}"] = df.groupby("region")["epidemic"].shift(-h)

    # 권역 코드(범주형 피처)
    df["region_code"] = df["region"].astype("category").cat.codes
    return df


def feature_matrix(df: pd.DataFrame, extra: list[str] | None = None) -> list[str]:
    """실제 사용할 피처 컬럼 리스트(존재하는 것만) 반환."""
    cols = [c for c in FEATURE_COLS if c in df.columns] + ["region_code"]
    if extra:
        cols += [c for c in extra if c in df.columns]
    return cols
