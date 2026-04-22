"""Taskiq 비동기 작업 브로커 및 태스크 정의."""
from __future__ import annotations

import logging

from taskiq_kafka import KafkaBroker

from .config import settings

logger = logging.getLogger(__name__)

broker = KafkaBroker(settings.kafka_bootstrap)


@broker.task
async def generate_report_task(region: str, signals: dict) -> None:
    """ML 서비스로 경보 리포트를 생성하고 DB에 저장한다."""
    from .database import async_session
    from .services.alert_service import save_alert_report
    from .services.prediction_service import generate_alert_report_http

    try:
        report = await generate_alert_report_http(region, signals)
        async with async_session() as db:
            await save_alert_report(report, db)
        logger.info("경보 리포트 생성 완료: region=%s level=%s", region, report.get("alert_level"))
    except Exception:
        logger.exception("경보 리포트 생성 실패: region=%s", region)
