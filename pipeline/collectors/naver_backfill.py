"""Naver DataLab OTC + Search 시계열 백필.

목적:
  현재 OTC/Search 데이터가 2026-01-26~04-20 (13주) 만 있어서,
  2025-11 인플루엔자 시즌 진입 시점에 alerts 교차검증이 작동하지 않음.
  KOWAS L2는 2~4주 선행 감지를 입증했으나 단독 신호로는 시스템이 GREEN 유지하는
  설계 정책(GFT 실패 방지 교차검증)에 막혀있음.

해결:
  Naver DataLab 검색 + 쇼핑인사이트 API로 1년치(2025-04 ~ 2026-04) 시계열을 일괄 수집,
  17개 시·도에 동일 전국 시계열을 복제 적재. (Naver 자체가 region 시계열을 안 줌)

CLI:
  python -m pipeline.collectors.naver_backfill
  python -m pipeline.collectors.naver_backfill --weeks 26 --layers search
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone

import httpx

from pipeline.collectors.db_writer import insert_signal
from pipeline.collectors.normalization import min_max_normalize

logger = logging.getLogger(__name__)

DATALAB_SEARCH = "https://openapi.naver.com/v1/datalab/search"
DATALAB_SHOPPING = "https://openapi.naver.com/v1/datalab/shopping/categories"

SYMPTOM_KEYWORDS = ["독감 증상", "인플루엔자", "고열 원인", "몸살 원인", "타미플루"]
OTC_CATEGORY_ID = "50000167"  # 일반의약품 - 감기·해열·진통제 카테고리
OTC_PARAM_NAME = "감기약"

# KOWAS와 동일한 17개 시·도 풀네임 — kowas_parser.SIDO_ORDER 와 정확히 일치해야 함
SIDO_ALL = [
    "서울특별시", "부산광역시", "대구광역시", "인천광역시", "광주광역시",
    "대전광역시", "울산광역시", "세종특별자치시", "경기도", "강원특별자치도",
    "충청북도", "충청남도", "전라북도", "전라남도", "경상북도",
    "경상남도", "제주특별자치도",
]


def _client() -> httpx.Client:
    cid = os.getenv("NAVER_CLIENT_ID", "")
    csec = os.getenv("NAVER_CLIENT_SECRET", "")
    if not cid or not csec:
        raise RuntimeError("NAVER_CLIENT_ID/SECRET 환경변수 필수")
    return httpx.Client(
        headers={
            "X-Naver-Client-Id": cid,
            "X-Naver-Client-Secret": csec,
            "Content-Type": "application/json",
        },
        timeout=30.0,
    )


def fetch_search_series(client: httpx.Client, start: date, end: date) -> list[tuple[date, float]]:
    """Naver DataLab 검색 트렌드 1년치 일괄 조회 (주 단위)."""
    payload = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "keywordGroups": [{"groupName": "독감증상", "keywords": SYMPTOM_KEYWORDS}],
    }
    resp = client.post(DATALAB_SEARCH, json=payload)
    resp.raise_for_status()
    data = resp.json().get("results", [{}])[0].get("data", [])
    return [(date.fromisoformat(p["period"]), float(p["ratio"])) for p in data]


def fetch_shopping_series(client: httpx.Client, start: date, end: date) -> list[tuple[date, float]]:
    """Naver 쇼핑인사이트 OTC 카테고리 1년치 일괄 조회 (주 단위)."""
    payload = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "category": [{"name": OTC_PARAM_NAME, "param": [OTC_CATEGORY_ID]}],
    }
    resp = client.post(DATALAB_SHOPPING, json=payload)
    resp.raise_for_status()
    data = resp.json().get("results", [{}])[0].get("data", [])
    return [(date.fromisoformat(p["period"]), float(p["ratio"])) for p in data]


async def backfill_layer(
    layer: str,
    series: list[tuple[date, float]],
    source: str,
    regions: list[str],
) -> int:
    """단일 layer 시계열을 17개 region에 복제 적재."""
    if not series:
        logger.warning("%s: 시계열 비어있음", layer)
        return 0
    raw = [v for _, v in series]
    norm = min_max_normalize(raw)
    inserted = 0
    for region in regions:
        for (when, raw_v), nv in zip(series, norm):
            ts = datetime.combine(when, datetime.min.time(), tzinfo=timezone.utc)
            try:
                await insert_signal(
                    region=region, layer=layer, value=nv,
                    raw_value=raw_v, source=source, ts=ts,
                )
                inserted += 1
            except Exception as exc:
                logger.error("INSERT 실패 %s/%s/%s: %s", region, layer, when, exc)
    return inserted


async def main() -> int:
    parser = argparse.ArgumentParser(description="Naver OTC/Search 시계열 백필")
    parser.add_argument("--weeks", type=int, default=56, help="백필 주차 수 (기본 1년+여유)")
    parser.add_argument("--layers", choices=["both", "otc", "search"], default="both")
    parser.add_argument("--regions", choices=["all", "single"], default="all",
                        help="all=17개 시·도 복제, single=서울만")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")

    end = date.today()
    start = end - timedelta(weeks=args.weeks)
    logger.info("백필 범위: %s ~ %s (%d주)", start, end, args.weeks)
    regions = SIDO_ALL if args.regions == "all" else ["서울특별시"]

    with _client() as client:
        if args.layers in ("both", "search"):
            try:
                ser = fetch_search_series(client, start, end)
                logger.info("Search %d주 수집 → %d 지역 복제 적재", len(ser), len(regions))
                n = await backfill_layer("search", ser, "naver_datalab", regions)
                logger.info("search 적재 %d건", n)
            except Exception as exc:
                logger.exception("Search 백필 실패: %s", exc)

        if args.layers in ("both", "otc"):
            try:
                ser = fetch_shopping_series(client, start, end)
                logger.info("OTC %d주 수집 → %d 지역 복제 적재", len(ser), len(regions))
                n = await backfill_layer("otc", ser, "naver_shopping", regions)
                logger.info("otc 적재 %d건", n)
            except Exception as exc:
                logger.exception("OTC 백필 실패: %s", exc)

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
