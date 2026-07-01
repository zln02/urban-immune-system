"""Delphi Epidata API 클라이언트 — CDC ILINet 실 임상 감시 데이터 다운로드.

소스: https://api.delphi.cmu.edu/epidata/  (Carnegie Mellon Delphi 그룹)
- fluview        : CDC ILINet 가중 ILI%(wili) — 외래 표본감시 실 임상 데이터 (1997~)
- covidcast      : 실 선행신호(google-symptoms 증상검색, doctor-visits 외래 CLI) (2020~)

모든 응답은 ml/data_cache/ 에 parquet 으로 캐시한다(네트워크 1회만, 재현성·오프라인 학습).
인증키 불필요(공개 엔드포인트). API 키가 필요한 ght 등은 사용하지 않는다.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

import pandas as pd
import requests

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.delphi.cmu.edu/epidata"
_CACHE_DIR = Path(__file__).resolve().parent.parent / "data_cache"

# CDC ILINet HHS 10개 권역 + 전국 — 실 임상 다지역 검증용
HHS_REGIONS: list[str] = ["nat"] + [f"hhs{i}" for i in range(1, 11)]


def _cache_path(name: str) -> Path:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _CACHE_DIR / f"{name}.parquet"


def _get(endpoint: str, params: dict, *, retries: int = 4, timeout: int = 60) -> list[dict]:
    """Delphi Epidata GET — result!=1 또는 네트워크 오류 시 재시도."""
    url = f"{_BASE_URL}/{endpoint}/"
    last_err: Exception | None = None
    for attempt in range(retries):
        try:
            resp = requests.get(url, params=params, timeout=timeout)
            resp.raise_for_status()
            payload = resp.json()
            result = payload.get("result")
            if result == 1:
                return payload.get("epidata", [])
            if result == -2:  # no data for query — 빈 결과는 정상
                logger.warning("Epidata no-data: %s %s", endpoint, params)
                return []
            last_err = RuntimeError(f"Epidata result={result}: {payload.get('message')}")
        except (requests.RequestException, ValueError) as exc:
            last_err = exc
        sleep = 2.0 * (attempt + 1)
        logger.warning("Epidata 재시도 %d/%d (%s) — %.1fs 대기", attempt + 1, retries, last_err, sleep)
        time.sleep(sleep)
    raise RuntimeError(f"Epidata 요청 실패: {endpoint} {params} — {last_err}")


def fetch_ilinet(
    regions: list[str] | None = None,
    epiweek_start: int = 200340,
    epiweek_end: int = 202420,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """CDC ILINet wILI 시계열을 권역별로 받아 long-format DataFrame 으로 반환.

    Args:
        regions: ILINet region 코드 리스트(기본 nat + hhs1..10)
        epiweek_start/end: MMWR epiweek 범위(YYYYWW)
        force: True 면 캐시 무시하고 재다운로드

    Returns:
        컬럼 [region, epiweek, wili, ili, num_ili, num_patients, num_providers]
    """
    regions = regions or HHS_REGIONS
    cache = _cache_path(f"ilinet_{epiweek_start}_{epiweek_end}")
    if cache.exists() and not force:
        logger.info("ILINet 캐시 로드: %s", cache)
        return pd.read_parquet(cache)

    frames: list[pd.DataFrame] = []
    for region in regions:
        rows = _get(
            "fluview",
            {"regions": region, "epiweeks": f"{epiweek_start}-{epiweek_end}"},
        )
        if not rows:
            logger.warning("ILINet %s: 데이터 없음", region)
            continue
        df = pd.DataFrame(rows)
        keep = ["region", "epiweek", "wili", "ili", "num_ili", "num_patients", "num_providers"]
        df = df[[c for c in keep if c in df.columns]].copy()
        frames.append(df)
        logger.info("ILINet %s: %d주", region, len(df))

    if not frames:
        raise RuntimeError("ILINet 데이터를 한 권역도 받지 못했습니다")

    out = pd.concat(frames, ignore_index=True)
    # wili 결측(초기 권역 미보고 주) 은 ili 로 보완 후 그래도 없으면 drop
    out["wili"] = pd.to_numeric(out["wili"], errors="coerce")
    out["ili"] = pd.to_numeric(out["ili"], errors="coerce")
    out["wili"] = out["wili"].fillna(out["ili"])
    out = out.dropna(subset=["wili"]).reset_index(drop=True)
    out.to_parquet(cache, index=False)
    logger.info("ILINet 저장: %s (%d행, %d권역)", cache, len(out), out["region"].nunique())
    return out


def fetch_covidcast_signal(
    data_source: str,
    signal: str,
    geo_value: str = "us",
    geo_type: str = "nation",
    time_start: int = 20200301,
    time_end: int = 20240501,
    *,
    force: bool = False,
) -> pd.DataFrame:
    """covidcast 실 선행신호(일단위)를 받아 [time_value, value] DataFrame 으로 반환.

    예) google-symptoms/s05_smoothed_search, doctor-visits/smoothed_adj_cli.
    2020년 이후만 존재 → 인플루엔자 다시즌 학습엔 보조 피처(오버랩 구간)로만 사용.
    """
    tag = f"cc_{data_source}_{signal}_{geo_value}_{time_start}_{time_end}".replace("/", "-")
    cache = _cache_path(tag)
    if cache.exists() and not force:
        return pd.read_parquet(cache)

    rows = _get(
        "covidcast",
        {
            "data_source": data_source,
            "signal": signal,
            "time_type": "day",
            "geo_type": geo_type,
            "geo_value": geo_value,
            "time_values": f"{time_start}-{time_end}",
        },
    )
    df = pd.DataFrame(rows)
    if df.empty:
        logger.warning("covidcast %s/%s: 데이터 없음", data_source, signal)
        return df
    df = df[["time_value", "value"]].copy()
    df["time_value"] = pd.to_datetime(df["time_value"].astype(str), format="%Y%m%d")
    df = df.sort_values("time_value").reset_index(drop=True)
    df.to_parquet(cache, index=False)
    logger.info("covidcast %s/%s 저장: %d일", data_source, signal, len(df))
    return df


if __name__ == "__main__":  # 수동 데이터 사전 캐시
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    ili = fetch_ilinet()
    print(f"ILINet: {len(ili)}행 · {ili['region'].nunique()}권역 · "
          f"epiweek {ili['epiweek'].min()}~{ili['epiweek'].max()}")
    print(ili.groupby("region")["wili"].agg(["count", "mean", "max"]).round(2))
