"""pipeline/collectors/wastewater.py _apply_wastewater_fallback() 단위 테스트.

3가지 케이스:
1. 정상: lookback에 이전 주 row 1개 존재 → fallback row 반환
2. 1주 실패: 직전 주는 비어있고 2주 전 row 존재 → 2주 전 데이터로 fallback
3. 연속 실패: lookback 안에 row 없음 → None 반환
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


_SQLITE_URL = "sqlite+aiosqlite:///:memory:"


@pytest_asyncio.fixture(scope="function")
async def fallback_db():
    """Fallback 테스트 전용 in-memory SQLite 엔진."""
    engine = create_async_engine(_SQLITE_URL, echo=False)

    # 테이블 생성
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS layer_signals (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                time    TEXT    NOT NULL,
                layer   TEXT    NOT NULL,
                region  TEXT    NOT NULL,
                value   REAL    NOT NULL,
                raw_value REAL,
                source  TEXT,
                pathogen TEXT DEFAULT 'influenza',
                meta    TEXT
            )
        """))

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture()
async def fallback_session(fallback_db):
    """각 테스트마다 독립 세션."""
    async_session_maker = async_sessionmaker(fallback_db, class_=AsyncSession, expire_on_commit=False)
    async with async_session_maker() as session:
        yield session
        await session.rollback()


@pytest.mark.asyncio
async def test_wastewater_fallback_case1_normal(fallback_session: AsyncSession) -> None:
    """케이스 1: lookback에 이전 주 row 1개 존재 → fallback row 반환."""
    from pipeline.collectors.wastewater import _apply_wastewater_fallback

    region = "서울특별시"
    now = datetime.now(timezone.utc)

    # 이전 주 데이터 INSERT (2주 전)
    await fallback_session.execute(
        text("""
            INSERT INTO layer_signals (time, layer, region, value, raw_value, source, pathogen)
            VALUES (:time, 'wastewater', :region, 65.5, 1200.0, 'kowas:influenza', 'influenza')
        """),
        {"time": (now - timedelta(weeks=2)).isoformat(), "region": region},
    )
    await fallback_session.commit()

    # Fallback 호출
    week_iso = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    fallback_row = await _apply_wastewater_fallback(
        fallback_session, region, week_iso, lookback_weeks=4
    )

    # 검증
    assert fallback_row is not None, "fallback row가 None이 되면 안 됨"
    assert fallback_row["region"] == region
    assert fallback_row["layer"] == "wastewater"
    assert fallback_row["value"] == 65.5
    assert fallback_row["raw_value"] == 1200.0
    assert fallback_row["pathogen"] == "influenza"
    assert fallback_row["meta"]["fallback"] is True
    assert fallback_row["meta"]["source_week"] is not None


@pytest.mark.asyncio
async def test_wastewater_fallback_case2_one_week_gap(fallback_session: AsyncSession) -> None:
    """케이스 2: 직전 주는 비어있고 2주 전 row 존재 → 2주 전 데이터로 fallback."""
    from pipeline.collectors.wastewater import _apply_wastewater_fallback

    region = "부산광역시"
    now = datetime.now(timezone.utc)

    # 2주 전 데이터만 INSERT (직전 주는 없음)
    await fallback_session.execute(
        text("""
            INSERT INTO layer_signals (time, layer, region, value, raw_value, source, pathogen)
            VALUES (:time, 'wastewater', :region, 52.0, 950.0, 'kowas:influenza', 'influenza')
        """),
        {"time": (now - timedelta(weeks=2)).isoformat(), "region": region},
    )
    await fallback_session.commit()

    # Fallback 호출
    week_iso = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    fallback_row = await _apply_wastewater_fallback(
        fallback_session, region, week_iso, lookback_weeks=4
    )

    # 검증: 2주 전 데이터를 fallback으로 사용
    assert fallback_row is not None
    assert fallback_row["value"] == 52.0
    assert fallback_row["raw_value"] == 950.0
    assert fallback_row["meta"]["fallback"] is True


@pytest.mark.asyncio
async def test_wastewater_fallback_case3_continuous_failure(fallback_session: AsyncSession) -> None:
    """케이스 3: lookback_weeks=4 안에 row 없음 → None 반환."""
    from pipeline.collectors.wastewater import _apply_wastewater_fallback

    region = "대구광역시"
    now = datetime.now(timezone.utc)

    # 테이블은 비어있음 (해당 지역에 데이터 없음)

    # Fallback 호출 (lookback_weeks=4)
    week_iso = f"{now.isocalendar()[0]}-W{now.isocalendar()[1]:02d}"
    fallback_row = await _apply_wastewater_fallback(
        fallback_session, region, week_iso, lookback_weeks=4
    )

    # 검증: None 반환 (연속 실패)
    assert fallback_row is None, "조회할 데이터 없으면 None 반환"
