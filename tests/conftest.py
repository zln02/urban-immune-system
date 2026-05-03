"""공통 pytest fixtures.

- db_session : SQLite in-memory (aiosqlite) 기반 SQLAlchemy AsyncSession
- client     : FastAPI TestClient (lifespan 비활성화)
- sample_signal_payload : L1/L2/L3 샘플 dict
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.testclient import TestClient

# ---------------------------------------------------------------------------
# in-memory SQLite engine
# ---------------------------------------------------------------------------
_SQLITE_URL = "sqlite+aiosqlite:///:memory:"

_engine = create_async_engine(_SQLITE_URL, echo=False)
_async_session = async_sessionmaker(_engine, class_=AsyncSession, expire_on_commit=False)


async def _create_tables(engine):
    """테스트용 최소 DDL — 실제 TimescaleDB 없이 SQLite로 흉내.
    SQLite에서는 CURRENT_TIMESTAMP 사용 (datetime('now') 함수는 DEFAULT에 불가).
    """
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS layer_signals (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                time    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                layer   TEXT    NOT NULL,
                region  TEXT    NOT NULL,
                value   REAL    NOT NULL,
                raw_value REAL,
                source  TEXT,
                pathogen TEXT DEFAULT 'influenza',
                meta    TEXT
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS risk_scores (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                time            TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                region          TEXT    NOT NULL,
                composite_score REAL    NOT NULL,
                l1_score        REAL,
                l2_score        REAL,
                l3_score        REAL,
                alert_level     TEXT    NOT NULL DEFAULT 'GREEN'
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS alert_reports (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                time            TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                region          TEXT    NOT NULL,
                alert_level     TEXT    NOT NULL,
                summary         TEXT,
                recommendations TEXT,
                model_used      TEXT,
                triggered_by    TEXT,
                trigger_source  TEXT,
                feature_values  TEXT,
                rag_sources     TEXT,
                model_metadata  TEXT,
                created_at      TEXT    DEFAULT CURRENT_TIMESTAMP
            )
        """))


@pytest_asyncio.fixture(scope="session")
async def db_engine():
    await _create_tables(_engine)
    yield _engine
    await _engine.dispose()


@pytest_asyncio.fixture()
async def db_session(db_engine):
    """각 테스트마다 독립 트랜잭션 → rollback으로 격리."""
    async with _async_session() as session:
        yield session
        await session.rollback()


# ---------------------------------------------------------------------------
# FastAPI TestClient — lifespan(broker)은 mock으로 우회
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def client():
    """동기 TestClient. lifespan broker.startup/shutdown을 mock 처리."""
    from unittest.mock import AsyncMock, patch

    with patch("backend.app.tasks.broker.startup", new_callable=AsyncMock), \
         patch("backend.app.tasks.broker.shutdown", new_callable=AsyncMock):
        from backend.app.main import app
        with TestClient(app, raise_server_exceptions=False) as c:
            yield c


# ---------------------------------------------------------------------------
# Sample payloads
# ---------------------------------------------------------------------------
@pytest.fixture()
def sample_signal_payload() -> dict:
    """3-Layer 신호 샘플 (region=서울특별시, week=2026-W17)."""
    return {
        "region": "서울특별시",
        "week_iso": "2026-W17",
        "l1": {"layer": "otc",        "value": 62.5, "source": "otc_test"},
        "l2": {"layer": "wastewater",  "value": 71.0, "source": "kowas_test"},
        "l3": {"layer": "search",      "value": 48.3, "source": "naver_test"},
    }
