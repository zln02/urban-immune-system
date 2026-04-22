"""TimescaleDB 직접 INSERT 유틸리티.

Kafka Consumer 없이 layer_signals 테이블에 직접 비동기 INSERT한다.
발표 데모 단순화 옵션 (pipeline/CLAUDE.md 참조):
  cron + DB INSERT 방식으로 Kafka 파이프라인을 대체.
"""
from __future__ import annotations

import asyncio
import logging
import os
import warnings
from datetime import datetime, timezone

import asyncpg

logger = logging.getLogger(__name__)

_DEFAULT_DB_URL = "postgresql://uis_user:changeme_local@localhost:5432/urban_immune"

_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    """asyncpg 커넥션 풀 싱글톤을 반환한다."""
    global _pool
    if _pool is None:
        db_url = os.getenv("DATABASE_URL", _DEFAULT_DB_URL)
        if "changeme" in db_url:
            warnings.warn(
                "DATABASE_URL에 플레이스홀더 자격증명(changeme)이 포함되어 있습니다. "
                "프로덕션 환경에서는 반드시 실제 자격증명으로 교체하세요.",
                UserWarning,
                stacklevel=2,
            )
        try:
            _pool = await asyncpg.create_pool(
                dsn=db_url,
                min_size=1,
                max_size=5,
            )
            logger.info("TimescaleDB 커넥션 풀 생성 완료")
        except Exception as exc:
            logger.error("TimescaleDB 커넥션 풀 생성 실패: %s", exc)
            raise
    return _pool


async def insert_signal(
    region: str,
    layer: str,
    value: float,
    raw_value: float | None = None,
    source: str = "",
) -> None:
    """layer_signals 테이블에 정규화된 신호를 직접 INSERT한다.

    Args:
        region: 지역명 (예: '서울특별시')
        layer: 계층 코드 ('L1' | 'L2' | 'L3' | 'AUX')
        value: 정규화 지수 (0-100)
        raw_value: 원시 측정값 (선택)
        source: 데이터 출처 식별자 (선택)
    """
    pool = await _get_pool()
    now = datetime.now(timezone.utc)
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO layer_signals (time, layer, region, value, raw_value, source)
                VALUES ($1, $2, $3, $4, $5, $6)
                """,
                now,
                layer,
                region,
                round(value, 4),
                raw_value,
                source,
            )
        logger.debug("DB INSERT 완료 → %s | %s | %.2f", layer, region, value)
    except Exception as exc:
        logger.error("layer_signals INSERT 실패 (layer=%s region=%s): %s", layer, region, exc)
        raise


def insert_signal_sync(
    region: str,
    layer: str,
    value: float,
    raw_value: float | None = None,
    source: str = "",
) -> None:
    """insert_signal()의 동기 래퍼. 비동기 루프가 없는 수집기에서 호출한다.

    이미 실행 중인 이벤트 루프가 있으면 run_until_complete,
    없으면 asyncio.run()을 사용한다.

    Args:
        region: 지역명
        layer: 계층 코드
        value: 정규화 지수 (0-100)
        raw_value: 원시 측정값 (선택)
        source: 데이터 출처 식별자 (선택)
    """
    coro = insert_signal(region, layer, value, raw_value=raw_value, source=source)
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 이미 실행 중인 루프 안에서 호출된 경우 (드문 케이스)
            loop.run_until_complete(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        # 이벤트 루프가 없거나 닫힌 경우
        asyncio.run(coro)
