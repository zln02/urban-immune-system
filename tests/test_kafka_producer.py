"""pipeline/collectors/kafka_producer.py 단위 테스트."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_producer():
    """각 테스트 전후 싱글톤 프로듀서 초기화."""
    import pipeline.collectors.kafka_producer as kp
    kp._producer = None
    yield
    kp._producer = None


# ---------------------------------------------------------------------------
# Case 1: 토픽 상수 값 검증
# ---------------------------------------------------------------------------
def test_topic_constants() -> None:
    """토픽 상수가 정해진 문자열과 일치해야 한다."""
    from pipeline.collectors.kafka_producer import (
        TOPIC_AUX,
        TOPIC_L1,
        TOPIC_L2,
        TOPIC_L3,
    )

    assert TOPIC_L1 == "uis.layer1.otc"
    assert TOPIC_L2 == "uis.layer2.wastewater"
    assert TOPIC_L3 == "uis.layer3.search"
    assert TOPIC_AUX == "uis.aux.weather"


# ---------------------------------------------------------------------------
# Case 2: get_producer 싱글톤 확인
# ---------------------------------------------------------------------------
def test_get_producer_singleton() -> None:
    """get_producer()를 2번 호출하면 동일한 인스턴스를 반환해야 한다."""
    from pipeline.collectors.kafka_producer import get_producer

    with patch("pipeline.collectors.kafka_producer.KafkaProducer") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        first = get_producer()
        second = get_producer()

        assert first is mock_instance
        assert second is mock_instance
        # KafkaProducer 생성자는 1번만 호출되어야 한다
        mock_cls.assert_called_once()


# ---------------------------------------------------------------------------
# Case 3: send_signal → producer.send 1회 호출
# ---------------------------------------------------------------------------
def test_send_signal_calls_send() -> None:
    """send_signal 호출 시 producer.send가 정확히 1회 호출되어야 한다."""
    from pipeline.collectors.kafka_producer import TOPIC_L1, send_signal

    with patch("pipeline.collectors.kafka_producer.KafkaProducer") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        send_signal(TOPIC_L1, region="서울특별시", layer="otc", value=55.0)

        mock_instance.send.assert_called_once()


# ---------------------------------------------------------------------------
# Case 4: send_signal payload 키 검증
# ---------------------------------------------------------------------------
def test_send_signal_payload_keys() -> None:
    """send 호출 시 value dict에 필수 키 6개가 모두 존재해야 한다."""
    from pipeline.collectors.kafka_producer import TOPIC_L1, send_signal

    with patch("pipeline.collectors.kafka_producer.KafkaProducer") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        send_signal(
            TOPIC_L1,
            region="서울특별시",
            layer="otc",
            value=42.0,
            raw_value=88.5,
            source="test_source",
        )

        call_kwargs = mock_instance.send.call_args[1]
        payload = call_kwargs["value"]

        for key in ("time", "layer", "region", "value", "raw_value", "source"):
            assert key in payload, f"payload에 '{key}' 키가 없음"


# ---------------------------------------------------------------------------
# Case 5: send_signal → producer.flush 호출 확인
# ---------------------------------------------------------------------------
def test_send_signal_calls_flush() -> None:
    """send_signal 호출 시 producer.flush가 호출되어야 한다."""
    from pipeline.collectors.kafka_producer import TOPIC_L2, send_signal

    with patch("pipeline.collectors.kafka_producer.KafkaProducer") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        send_signal(TOPIC_L2, region="부산광역시", layer="wastewater", value=30.0)

        mock_instance.flush.assert_called_once()


# ---------------------------------------------------------------------------
# Case 6: send_signal → 올바른 토픽으로 send 호출
# ---------------------------------------------------------------------------
def test_send_signal_topic_routing() -> None:
    """TOPIC_L1을 전달하면 send의 첫 번째 인자가 TOPIC_L1이어야 한다."""
    from pipeline.collectors.kafka_producer import TOPIC_L1, send_signal

    with patch("pipeline.collectors.kafka_producer.KafkaProducer") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        send_signal(TOPIC_L1, region="대구광역시", layer="otc", value=20.0)

        call_args = mock_instance.send.call_args
        # 위치 인자 첫 번째 = topic
        assert call_args[0][0] == TOPIC_L1


# ---------------------------------------------------------------------------
# Case 7: KafkaProducer 초기화 시 bootstrap_servers 파라미터 전달 확인
# ---------------------------------------------------------------------------
def test_get_producer_bootstrap() -> None:
    """get_producer()는 KafkaProducer에 bootstrap_servers를 전달해야 한다."""
    from pipeline.collectors.kafka_producer import get_producer

    with patch("pipeline.collectors.kafka_producer.KafkaProducer") as mock_cls:
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        get_producer()

        _, kwargs = mock_cls.call_args
        assert "bootstrap_servers" in kwargs
