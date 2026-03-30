"""보조 데이터: 기상청 API 기온·습도 수집기.

저온·저습 환경이 인플루엔자 확산과 상관관계 있음.
인과관계는 없지만 TFT 입력 피처로 활용.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

import httpx

from pipeline.collectors.kafka_producer import TOPIC_AUX, send_signal

logger = logging.getLogger(__name__)

KMA_API_KEY = os.getenv("KMA_API_KEY", "")
KMA_CURRENT_URL = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getUltraSrtNcst"

# 서울 격자 좌표 (기상청 기준)
SEOUL_NX, SEOUL_NY = 60, 127


def collect_weather(region: str = "서울특별시") -> dict | None:
    """기상청 초단기실황 API에서 기온·습도를 수집해 Kafka로 전송한다."""
    if not KMA_API_KEY:
        logger.warning("기상청 API 키가 없습니다 (KMA_API_KEY)")
        return None

    now = datetime.now(timezone.utc)
    params = {
        "serviceKey": KMA_API_KEY,
        "numOfRows": 10,
        "pageNo": 1,
        "dataType": "JSON",
        "base_date": now.strftime("%Y%m%d"),
        "base_time": now.strftime("%H00"),
        "nx": SEOUL_NX,
        "ny": SEOUL_NY,
    }

    try:
        resp = httpx.get(KMA_CURRENT_URL, params=params, timeout=10.0)
        resp.raise_for_status()
        items = resp.json()["response"]["body"]["items"]["item"]

        result = {}
        for item in items:
            if item["category"] == "T1H":   # 기온
                result["temperature"] = float(item["obsrValue"])
            elif item["category"] == "REH":  # 습도
                result["humidity"] = float(item["obsrValue"])

        if "temperature" in result:
            # 기온 정규화: -20°C~40°C → 0~100
            norm_temp = round((result["temperature"] + 20) / 60 * 100, 2)
            send_signal(TOPIC_AUX, region, "AUX", norm_temp,
                        raw_value=result["temperature"], source="kma_temperature")

        return result

    except Exception as exc:
        logger.error("기상청 수집 실패: %s", exc)
        return None
