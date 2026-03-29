"""Layer 1: 네이버 쇼핑인사이트 OTC 구매 트렌드 수집기.

네이버 데이터랩 쇼핑인사이트 API를 사용해
'감기약', '해열제', '종합감기약' 등 OTC 의약품 카테고리 검색 트렌드를 수집한다.
선행 시간: 임상 확진 대비 약 1~2주.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import httpx

from collectors.kafka_producer import TOPIC_L1, send_signal

logger = logging.getLogger(__name__)

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
DATALAB_URL = "https://openapi.naver.com/v1/datalab/shopping/categories"

# OTC 의약품 카테고리 키워드 (쇼핑인사이트 카테고리 ID 매핑 필요)
OTC_KEYWORDS = ["감기약", "해열제", "종합감기약", "타이레놀", "판콜"]
TARGET_REGION = "서울특별시"


def _normalize(values: list[float]) -> list[float]:
    """Min-Max 정규화 (0~100)."""
    if not values:
        return values
    lo, hi = min(values), max(values)
    if hi == lo:
        return [50.0] * len(values)
    return [round((v - lo) / (hi - lo) * 100, 2) for v in values]


def collect_otc_weekly(end_date: datetime | None = None) -> float | None:
    """최근 1주 OTC 트렌드 지수를 수집해 정규화 후 Kafka로 전송한다."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        logger.warning("네이버 API 키가 설정되지 않았습니다 (NAVER_CLIENT_ID / NAVER_CLIENT_SECRET)")
        return None

    end = end_date or datetime.utcnow()
    start = end - timedelta(weeks=12)

    payload = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "category": [
            # TODO: 네이버 쇼핑인사이트 실제 카테고리 ID로 교체
            {"name": "OTC감기", "param": ["50000008"]},
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
                "X-Naver-Client-Id": NAVER_CLIENT_ID,
                "X-Naver-Client-Secret": NAVER_CLIENT_SECRET,
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
        normalized = _normalize(raw_values)
        latest = normalized[-1] if normalized else None

        if latest is not None:
            send_signal(
                TOPIC_L1, TARGET_REGION, "L1", latest,
                raw_value=raw_values[-1], source="naver_shopping_insight",
            )
            logger.info("Layer 1 (OTC) 수집 완료: %.2f", latest)
        return latest

    except Exception as exc:
        logger.error("Layer 1 수집 실패: %s", exc)
        return None
