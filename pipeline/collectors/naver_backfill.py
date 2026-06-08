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

from pipeline.collectors.db_writer import delete_signal_range, insert_signal

# Note: min_max_normalize 는 backfill_layer 에서 zero-collapse 로 폐기 — naver ratio 그대로 사용

logger = logging.getLogger(__name__)

DATALAB_SEARCH = "https://openapi.naver.com/v1/datalab/search"
DATALAB_SHOPPING = "https://openapi.naver.com/v1/datalab/shopping/categories"

SYMPTOM_KEYWORDS = ["독감 증상", "인플루엔자", "고열 원인", "몸살 원인", "타미플루"]
OTC_CATEGORY_ID = "50000167"  # 일반의약품 - 감기·해열·진통제 카테고리
OTC_PARAM_NAME = "감기약"

# 다질병 L3 검색 키워드 사전 — 2026-06-01 추가
# L3는 키워드 기반이라 pathogen별 확장 자유.
# 노로바이러스 검색량은 매우 낮을 수 있어 일부 주차 응답 빈 가능성 있음 → 별도 검증 필요.
SEARCH_KEYWORDS_BY_PATHOGEN: dict[str, list[str]] = {
    "influenza": SYMPTOM_KEYWORDS,
    "covid": ["코로나 증상", "코로나 검사", "PCR 검사", "자가검사 키트", "코로나 후유증"],
    "norovirus": ["노로바이러스", "장염 증상", "구토 설사", "급성 위장염"],
}

# 다질병 L1 OTC 카테고리 사전 — 2026-06-03 확장
# 네이버 쇼핑인사이트 카테고리 ID 매핑. 의약품(자가검사키트·해열제 등)은 카테고리 미공개라
# 비특이 보조 신호(마스크·손소독제·체온계)로 대체. 인플루엔자 감기약(50000167) 이 가장 직접적.
# COVID/노로 OTC는 보조 피처 — L2·L3와 결합 시 ML 가치 보완.
OTC_CATEGORIES_BY_PATHOGEN: dict[str, list[tuple[str, str]]] = {
    "influenza": [(OTC_CATEGORY_ID, OTC_PARAM_NAME)],
    "covid": [
        ("50003445", "마스크"),       # 생활/건강 > 공구 > 안전용품 > 마스크
        ("50006879", "손소독제"),     # 생활/건강 > 생활용품 > 세제/세정제 > 손소독제
        ("50002047", "체온계"),       # 생활/건강 > 건강측정용품 > 체온계
    ],
    "norovirus": [
        ("50002256", "이온음료"),     # 식품 > 음료 > 청량/탄산음료 > 이온음료 (탈수 보충)
    ],
}


def _search_keywords(pathogen: str) -> list[str]:
    if pathogen not in SEARCH_KEYWORDS_BY_PATHOGEN:
        raise ValueError(
            f"미지원 pathogen='{pathogen}'. 지원: {list(SEARCH_KEYWORDS_BY_PATHOGEN)}"
        )
    return SEARCH_KEYWORDS_BY_PATHOGEN[pathogen]


def _datalab_source(pathogen: str) -> str:
    """pathogen별 source 라벨 — 멱등 DELETE 격리용.

    delete_signal_range가 (layer, source) 기준이라 pathogen을 source에 포함시켜야
    influenza 백필이 covid row를 지우지 않음.
    """
    # 인플루엔자는 기존 호환성 유지 (legacy "naver_datalab")
    return "naver_datalab" if pathogen == "influenza" else f"naver_datalab_{pathogen}"

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


def fetch_search_series(
    client: httpx.Client,
    start: date,
    end: date,
    pathogen: str = "influenza",
) -> list[tuple[date, float]]:
    """Naver DataLab 검색 트렌드 1년치 일괄 조회 (주 단위, pathogen별)."""
    keywords = _search_keywords(pathogen)
    payload = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "keywordGroups": [{"groupName": pathogen, "keywords": keywords}],
    }
    resp = client.post(DATALAB_SEARCH, json=payload)
    resp.raise_for_status()
    data = resp.json().get("results", [{}])[0].get("data", [])
    return [(date.fromisoformat(p["period"]), float(p["ratio"])) for p in data]


def fetch_shopping_series(
    client: httpx.Client,
    start: date,
    end: date,
    category_id: str = OTC_CATEGORY_ID,
    category_name: str = OTC_PARAM_NAME,
) -> list[tuple[date, float]]:
    """Naver 쇼핑인사이트 카테고리 1년치 일괄 조회 (주 단위).

    Args:
        category_id: 네이버 쇼핑인사이트 카테고리 ID (기본 감기약)
        category_name: API payload용 라벨
    """
    payload = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "category": [{"name": category_name, "param": [category_id]}],
    }
    resp = client.post(DATALAB_SHOPPING, json=payload)
    resp.raise_for_status()
    data = resp.json().get("results", [{}])[0].get("data", [])
    return [(date.fromisoformat(p["period"]), float(p["ratio"])) for p in data]


def _avg_series(series_list: list[list[tuple[date, float]]]) -> list[tuple[date, float]]:
    """여러 카테고리 시계열을 (date 정렬 후) 평균. 빈 입력 시 빈 리스트."""
    if not series_list:
        return []
    if len(series_list) == 1:
        return series_list[0]
    from collections import defaultdict
    bucket: dict[date, list[float]] = defaultdict(list)
    for ser in series_list:
        for d, v in ser:
            bucket[d].append(v)
    out = [(d, sum(vs) / len(vs)) for d, vs in sorted(bucket.items())]
    return out


async def backfill_layer(
    layer: str,
    series: list[tuple[date, float]],
    source: str,
    regions: list[str],
    pathogen: str = "influenza",
) -> int:
    """단일 layer 시계열을 17개 region에 복제 적재.

    멱등성: 동일 (layer, source) 의 시계열 시작점 이후 행을 일괄 삭제 후 재적재.
    weekly 잡이 매주 동일 56주 데이터를 INSERT 해도 누적되지 않는다.
    """
    if not series:
        logger.warning("%s: 시계열 비어있음", layer)
        return 0
    start_ts = datetime.combine(series[0][0], datetime.min.time(), tzinfo=timezone.utc)
    await delete_signal_range(layer=layer, source=source, start_ts=start_ts)

    # naver datalab/shopping ratio 는 이미 자체 정규화 (peak=100, 0~100 범위).
    # 슬라이딩 윈도우 안에서 다시 min-max 하면 비수기 마지막 주가 0 으로 박히는
    # zero-collapse 발생. (search_collector.py [DEPRECATED] 주석 + 2026-04-27 사고 참조)
    # → ratio 그대로 0~100 스케일 사용 — otc_collector.collect_otc_weekly 와 동일 정책.
    inserted = 0
    for region in regions:
        for when, raw_v in series:
            ts = datetime.combine(when, datetime.min.time(), tzinfo=timezone.utc)
            value = max(0.0, min(100.0, float(raw_v)))
            try:
                await insert_signal(
                    region=region, layer=layer, value=value,
                    raw_value=raw_v, source=source, ts=ts,
                    pathogen=pathogen,
                )
                inserted += 1
            except Exception as exc:
                logger.error("INSERT 실패 %s/%s/%s: %s", region, layer, when, exc)
    return inserted


async def run_backfill(
    weeks: int = 56,
    layers: str = "both",
    regions: str = "all",
    pathogen: str = "influenza",
) -> dict[str, int]:
    """scheduler/CLI 양쪽에서 호출 가능한 백필 코어.

    Args:
        weeks: 백필 주차 수
        layers: 'both' | 'otc' | 'search'
        regions: 'all' (17개 시·도) | 'single' (서울만)
        pathogen: 'influenza' | 'covid' | 'norovirus' — 2026-06-01 다질병 도입.
            L1 OTC는 카테고리 ID(감기약)가 influenza 전제 → covid/norovirus 시 'search' 만 적재됨.

    Returns:
        {'search': 적재건수, 'otc': 적재건수}
    """
    end = date.today()
    start = end - timedelta(weeks=weeks)
    logger.info("백필 범위: %s ~ %s (%d주, pathogen=%s)", start, end, weeks, pathogen)
    region_list = SIDO_ALL if regions == "all" else ["서울특별시"]
    counts: dict[str, int] = {}
    search_source = _datalab_source(pathogen)

    # L1 OTC: 다질병 카테고리 사전(OTC_CATEGORIES_BY_PATHOGEN)에 정의된 pathogen만 적재.
    do_otc = layers in ("both", "otc") and pathogen in OTC_CATEGORIES_BY_PATHOGEN
    if layers in ("both", "otc") and pathogen not in OTC_CATEGORIES_BY_PATHOGEN:
        logger.info("OTC skip: pathogen=%s는 L1 카테고리 미정의", pathogen)
    otc_source = "naver_shopping_insight" if pathogen == "influenza" else f"naver_shopping_insight_{pathogen}"

    with _client() as client:
        if layers in ("both", "search"):
            try:
                ser = fetch_search_series(client, start, end, pathogen=pathogen)
                if not ser:
                    logger.warning("Search %s: 빈 응답 (키워드 검색량 너무 낮을 수 있음)", pathogen)
                logger.info("Search %d주 수집 → %d 지역 복제 적재 (pathogen=%s)",
                            len(ser), len(region_list), pathogen)
                counts["search"] = await backfill_layer(
                    "search", ser, search_source, region_list, pathogen=pathogen,
                )
                logger.info("search 적재 %d건", counts["search"])
            except Exception as exc:
                logger.exception("Search 백필 실패: %s", exc)
                counts["search"] = 0

        if do_otc:
            try:
                # 다질병 OTC: pathogen별 1~3개 카테고리 평균 (단일 카테고리도 평균 함수 통과)
                cats = OTC_CATEGORIES_BY_PATHOGEN[pathogen]
                series_per_cat = []
                for cat_id, cat_name in cats:
                    s = fetch_shopping_series(client, start, end, cat_id, cat_name)
                    series_per_cat.append(s)
                    logger.info("OTC %s/%s (%s): %d주", pathogen, cat_name, cat_id, len(s))
                ser = _avg_series(series_per_cat)
                logger.info("OTC %s 평균 %d주 → %d 지역 복제 적재 (cats=%d)",
                            pathogen, len(ser), len(region_list), len(cats))
                # source: influenza는 'naver_shopping_insight' 유지 (호환성),
                # 다질병은 pathogen별 분리: 'naver_shopping_insight_{pathogen}'
                counts["otc"] = await backfill_layer(
                    "otc", ser, otc_source, region_list,
                    pathogen=pathogen,
                )
                logger.info("otc 적재 %d건", counts["otc"])
            except Exception as exc:
                logger.exception("OTC 백필 실패: %s", exc)
                counts["otc"] = 0

    return counts


async def main() -> int:
    parser = argparse.ArgumentParser(description="Naver OTC/Search 시계열 백필")
    parser.add_argument("--weeks", type=int, default=56, help="백필 주차 수 (기본 1년+여유)")
    parser.add_argument("--layers", choices=["both", "otc", "search"], default="both")
    parser.add_argument("--regions", choices=["all", "single"], default="all",
                        help="all=17개 시·도 복제, single=서울만")
    parser.add_argument("--pathogen", choices=["influenza", "covid", "norovirus"],
                        default="influenza",
                        help="병원체 (L3만 분기; L1 OTC는 influenza 전용)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s",
                        datefmt="%H:%M:%S")

    await run_backfill(weeks=args.weeks, layers=args.layers, regions=args.regions,
                       pathogen=args.pathogen)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
