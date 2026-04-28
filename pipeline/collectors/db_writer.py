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
        # asyncpg는 'postgresql://' 또는 'postgres://' 만 지원
        # SQLAlchemy용 'postgresql+asyncpg://' scheme을 변환
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        elif db_url.startswith("postgres+asyncpg://"):
            db_url = db_url.replace("postgres+asyncpg://", "postgresql://", 1)
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
    ts: datetime | None = None,
    pathogen: str = "influenza",
) -> None:
    """layer_signals 테이블에 정규화된 신호를 직접 INSERT한다.

    Args:
        region: 지역명 (예: '서울특별시')
        layer: 계층 코드 ('otc' | 'wastewater' | 'search' | 'weather')
        value: 정규화 지수 (0-100)
        raw_value: 원시 측정값 (선택)
        source: 데이터 출처 식별자 (선택)
        ts: 측정 타임스탬프 (None이면 현재 UTC). 과거 데이터 적재 시 명시.
        pathogen: 병원체 라벨 ('influenza' | 'covid' | 'norovirus'). 기본 인플루엔자.
            L1 OTC, L3 검색, AUX 기상은 인플루엔자 전제이며 L2 KOWAS만 3종 분리 적재.
    """
    pool = await _get_pool()
    when = ts if ts is not None else datetime.now(timezone.utc)
    try:
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO layer_signals (time, layer, region, value, raw_value, source, pathogen)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                """,
                when,
                layer,
                region,
                round(value, 4),
                raw_value,
                source,
                pathogen,
            )
        logger.debug("DB INSERT 완료 → %s/%s | %s | %.2f", layer, pathogen, region, value)
    except Exception as exc:
        logger.error(
            "layer_signals INSERT 실패 (layer=%s pathogen=%s region=%s): %s",
            layer, pathogen, region, exc,
        )
        raise


async def delete_signal_range(
    layer: str,
    source: str,
    start_ts: datetime,
) -> int:
    """layer_signals 에서 (layer, source, time >= start_ts) 범위를 삭제한다.

    백필 잡의 멱등성 보장용. source로 한정해 다른 출처(예: kowas:* )는 영향 없음.

    Returns:
        삭제된 행 수
    """
    pool = await _get_pool()
    async with pool.acquire() as conn:
        result = await conn.execute(
            """
            DELETE FROM layer_signals
            WHERE layer = $1 AND source = $2 AND time >= $3
            """,
            layer,
            source,
            start_ts,
        )
    deleted = int(result.split()[-1]) if result else 0
    if deleted:
        logger.info("멱등성 DELETE: layer=%s source=%s ≥%s → %d행 제거",
                    layer, source, start_ts.date(), deleted)
    return deleted


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
        layer: 계층 코드 ('otc' | 'wastewater' | 'search' | 'weather')
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
