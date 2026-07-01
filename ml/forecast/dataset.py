"""주간 패널 구성 + CDC식 계절 baseline·유행개시(onset) 라벨.

핵심 정직성: 유행 baseline 은 **과거 시즌의 비유행기(off-season)** 통계로만 계산해
미래 누출을 차단한다(CDC ILINet baseline 산정 방식 = 직전 3시즌 비유행 평균 + 2·SD).
이로써 "유행 개시" 라벨이 실제 임상(wILI) 정답에 근거하면서도 walk-forward 에서
검증 시즌 정보를 쓰지 않는다.
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# MMWR 시즌은 매년 30주차에 시작(여름 저점) → 다음해 29주차까지가 한 시즌
SEASON_START_WEEK = 30
# 비유행기(off-season): 늦봄~초가을. baseline 산정 표본
OFFSEASON_WEEKS = list(range(21, 40))
# baseline 산정에 사용할 직전 시즌 수
BASELINE_LOOKBACK_SEASONS = 3
# 유행 개시 판정: baseline 초과가 최소 연속 N주 지속
ONSET_SUSTAIN_WEEKS = 2


def _epiweek_parts(epiweek: int) -> tuple[int, int]:
    """MMWR epiweek(YYYYWW) → (year, week)."""
    return epiweek // 100, epiweek % 100


def build_panel(ili: pd.DataFrame) -> pd.DataFrame:
    """ILINet long-format → 시즌/주차/전국맥락이 부착된 패널.

    추가 컬럼:
        year, week, season(시즌 시작연도), week_of_season(시즌 내 0-based 순번),
        t_idx(권역 내 시간 순번), nat_wili(같은 epiweek 전국 wILI 맥락)
    """
    df = ili.copy()
    df[["year", "week"]] = df["epiweek"].apply(lambda e: pd.Series(_epiweek_parts(int(e))))
    # 시즌: week >= 30 이면 당해연도, 아니면 전년도
    df["season"] = np.where(df["week"] >= SEASON_START_WEEK, df["year"], df["year"] - 1)
    df = df.sort_values(["region", "epiweek"]).reset_index(drop=True)

    # 시즌 내 주차 순번(0-based) — epiweek 정렬 기준
    df["week_of_season"] = df.groupby(["region", "season"]).cumcount()
    # 권역 내 전체 시간 순번
    df["t_idx"] = df.groupby("region").cumcount()

    # 전국(nat) wILI 를 같은 epiweek 으로 각 권역행에 join (cross-region 맥락 피처)
    nat = df[df["region"] == "nat"][["epiweek", "wili"]].rename(columns={"wili": "nat_wili"})
    df = df.merge(nat, on="epiweek", how="left")
    return df


def _region_baseline(region_df: pd.DataFrame) -> pd.DataFrame:
    """권역 1개에 대해 시즌별 baseline(직전 3시즌 off-season 평균+2SD)을 부착.

    누출 방지: season S 의 baseline 은 season < S 의 off-season 표본만 사용.
    초기 시즌(과거 부족)은 가용한 과거 off-season 으로 확장, 전무하면 NaN.
    """
    region_df = region_df.sort_values("epiweek").reset_index(drop=True)
    seasons = sorted(region_df["season"].unique())
    off = region_df[region_df["week"].isin(OFFSEASON_WEEKS)]

    baseline_map: dict[int, float] = {}
    for s in seasons:
        prior = sorted([x for x in seasons if x < s])[-BASELINE_LOOKBACK_SEASONS:]
        sample = off[off["season"].isin(prior)]["wili"].dropna()
        if len(sample) >= 5:
            baseline_map[s] = float(sample.mean() + 2.0 * sample.std(ddof=1))
        else:
            # 과거 부족 → 가용 전체 과거 off-season 으로 확장
            sample2 = off[off["season"] < s]["wili"].dropna()
            baseline_map[s] = (
                float(sample2.mean() + 2.0 * sample2.std(ddof=1)) if len(sample2) >= 5 else np.nan
            )
    region_df["baseline"] = region_df["season"].map(baseline_map)
    return region_df


def add_baseline_and_onset(panel: pd.DataFrame) -> pd.DataFrame:
    """권역별 baseline + 유행기 라벨(epidemic) + 시즌 onset 주차 부착.

    epidemic: wili >= baseline (당주 유행 상태, 실 임상 정답)
    onset_woy: 시즌별 첫 '연속 ONSET_SUSTAIN_WEEKS 주 유행' 의 시작 week_of_season
    """
    out = pd.concat(
        [_region_baseline(g) for _, g in panel.groupby("region", sort=False)],
        ignore_index=True,
    )
    out["epidemic"] = (out["wili"] >= out["baseline"]).astype("float")
    out.loc[out["baseline"].isna(), "epidemic"] = np.nan

    # 시즌 onset: 연속 지속 유행 첫 주차
    onset_rows = []
    for (region, season), g in out.groupby(["region", "season"]):
        g = g.sort_values("week_of_season")
        ep = g["epidemic"].fillna(0).to_numpy()
        onset = np.nan
        run = 0
        for i, v in enumerate(ep):
            run = run + 1 if v >= 1 else 0
            if run >= ONSET_SUSTAIN_WEEKS:
                onset = int(g.iloc[i - ONSET_SUSTAIN_WEEKS + 1]["week_of_season"])
                break
        onset_rows.append({"region": region, "season": season, "onset_woy": onset})
    onset_df = pd.DataFrame(onset_rows)
    out = out.merge(onset_df, on=["region", "season"], how="left")
    return out


def load_dataset(ili: pd.DataFrame) -> pd.DataFrame:
    """ILINet → 학습 가능한 라벨링 패널 (build_panel + baseline/onset)."""
    panel = build_panel(ili)
    panel = add_baseline_and_onset(panel)
    n_ep = int(panel["epidemic"].sum(skipna=True))
    logger.info(
        "패널 구성: %d행 · %d권역 · %d시즌 · 유행주 %d (%.1f%%)",
        len(panel), panel["region"].nunique(), panel["season"].nunique(),
        n_ep, 100 * n_ep / panel["epidemic"].notna().sum(),
    )
    return panel
