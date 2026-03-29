"""Layer 3: 네이버 데이터랩 검색어 트렌드 수집기.

네이버 데이터랩 API에서 독감/감기 관련 증상 검색어 트렌드를 수집한다.
- 쇼핑인사이트(L1)와 완전 분리: 쇼핑(구매 행동) vs 검색(증상 정보 탐색)
- 선행 시간: 임상 확진 대비 약 1~2주 (실시간성 가장 높음)
- GFT 교훈: 단독 사용 시 과대추정 위험 → 교차검증 필수
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta

import httpx

from collectors.kafka_producer import TOPIC_L3, send_signal

logger = logging.getLogger(__name__)

NAVER_CLIENT_ID = os.getenv("NAVER_CLIENT_ID", "")
NAVER_CLIENT_SECRET = os.getenv("NAVER_CLIENT_SECRET", "")
DATALAB_URL = "https://openapi.naver.com/v1/datalab/search"

# 증상 기반 검색어 (쇼핑 키워드와 의도적으로 분리)
SYMPTOM_KEYWORDS = ["독감 증상", "인플루엔자", "고열 원인", "몸살 원인", "타미플루"]
TARGET_REGION = "서울특별시"


def _normalize(values: list[float]) -> list[float]:
    lo, hi = min(values), max(values)
    if hi == lo:
        return [50.0] * len(values)
    return [round((v - lo) / (hi - lo) * 100, 2) for v in values]


def collect_search_weekly(end_date: datetime | None = None) -> float | None:
    """최근 12주 검색 트렌드를 수집해 최신값을 Kafka로 전송한다."""
    if not NAVER_CLIENT_ID or not NAVER_CLIENT_SECRET:
        logger.warning("네이버 API 키가 설정되지 않았습니다")
        return None

    end = end_date or datetime.utcnow()
    start = end - timedelta(weeks=12)

    payload = {
        "startDate": start.strftime("%Y-%m-%d"),
        "endDate": end.strftime("%Y-%m-%d"),
        "timeUnit": "week",
        "keywordGroups": [
            {"groupName": "독감증상", "keywords": SYMPTOM_KEYWORDS},
        ],
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
            send_signal(TOPIC_L3, TARGET_REGION, "L3", latest, raw_value=raw_values[-1], source="naver_datalab")
            logger.info("Layer 3 (검색어) 수집 완료: %.2f", latest)
        return latest

    except Exception as exc:
        logger.error("Layer 3 수집 실패: %s", exc)
        return None
