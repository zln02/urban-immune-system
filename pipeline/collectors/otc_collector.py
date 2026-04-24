"""Layer 1: 네이버 쇼핑인사이트 OTC 구매 트렌드 수집기.

네이버 데이터랩 쇼핑인사이트 API를 사용해
'감기약', '해열제', '종합감기약' 등 OTC 의약품 카테고리 검색 트렌드를 수집한다.
선행 시간: 임상 확진 대비 약 1~2주.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone

import httpx

from pipeline.collectors.db_writer import insert_signal_sync
from pipeline.collectors.normalization import min_max_normalize

logger = logging.getLogger(__name__)
DATALAB_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

# OTC 의약품 카테고리 키워드 (쇼핑인사이트 카테고리 ID 매핑 필요)
OTC_KEYWORDS = ["감기약", "해열제", "종합감기약", "타이레놀", "판콜"]
TARGET_REGION = "서울특별시"

def collect_otc_weekly(end_date: datetime | None = None) -> float | None:
    """최근 1주 OTC 트렌드 지수를 수집해 정규화 후 Kafka로 전송한다."""
    client_id = os.getenv("NAVER_CLIENT_ID", "")
    client_secret = os.getenv("NAVER_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        logger.warning("네이버 API 키가 설정되지 않았습니다 (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET)")
        return None

    end = end_date or datetime.now(timezone.utc)
    start = end - timedelta(weeks=12)

    payload = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "category": [
            # 일반의약품 감기약 카테고리 (네이버 쇼핑인사이트)
            {"name": "OTC감기", "param": ["50000167"]},
        ],
        "device": "",
        "ages": [],
        "gender": "",
    }

    try:
        resp = httpx.post(
            DATALAB_URL,
            json=payload,
            headers={
                "X-Naver-Client-Id": client_id,
                "X-Naver-Client-Secret": client_secret,
                "Content-Type": "application/json",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()

        results = data.get("results", [])
        if not results:
            return None

        raw_values = [p["ratio"] for p in results[0].get("data", [])]
        # 네이버 쇼핑인사이트 ratio는 이미 0-100 지수(max=100 기준)
        # 구간 내 min-max 재정규화 시 최신 주가 최솟값이면 0으로 왜곡되므로
        # ratio를 그대로 정규화 지수로 사용한다.
        latest_raw = raw_values[-1] if raw_values else None
        latest = round(latest_raw, 2) if latest_raw is not None else None

        if latest is not None:
            insert_signal_sync(TARGET_REGION, "otc", latest, raw_value=latest_raw, source="naver_shopping_insight")
            logger.info("Layer 1 (OTC) 수집 완료: %.2f", latest)
        return latest

    except Exception as exc:
        logger.error("Layer 1 수집 실패: %s", exc)
        return None
