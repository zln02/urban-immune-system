"""Kafka 프로듀서 유틸리티."""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from kafka import KafkaProducer

logger = logging.getLogger(__name__)

# 토픽 정의
TOPIC_L1 = "uis.layer1.otc"
TOPIC_L2 = "uis.layer2.wastewater"
TOPIC_L3 = "uis.layer3.search"
TOPIC_AUX = "uis.aux.weather"

_producer: KafkaProducer | None = None


def get_producer() -> KafkaProducer:
    global _producer
    if _producer is None:
        _producer = KafkaProducer(
            bootstrap_servers=os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
            value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
            acks="all",
            retries=3,
        )
    return _producer


def send_signal(
    topic: str, region: str, layer: str, value: float,
    raw_value: float | None = None, source: str = "",
) -> None:
    """정규화된 신호를 Kafka에 전송한다."""
    producer = get_producer()
    payload = {
        "time": datetime.now(timezone.utc).isoformat(),
        "layer": layer,
        "region": region,
        "value": round(value, 4),
        "raw_value": raw_value,
        "source": source,
    }
    producer.send(topic, key=region, value=payload)
    producer.flush(timeout=5.0)
    logger.debug("Kafka send → %s | %s | %.2f", topic, region, value)
