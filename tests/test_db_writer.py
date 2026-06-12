"""pipeline/collectors/db_writer.py 단위 테스트."""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture(autouse=True)
def _reset_pool():
    """각 테스트 전 DB 풀 초기화."""
    import pipeline.collectors.db_writer as dbw

    dbw._pool = None
    yield
    dbw._pool = None


def _make_mock_pool(mock_conn: AsyncMock) -> AsyncMock:
    """asyncpg Pool mock을 올바르게 설정한다."""
    mock_pool = MagicMock()

    @asynccontextmanager
    async def _acquire():
        yield mock_conn

    mock_pool.acquire = _acquire
    return mock_pool


@patch("pipeline.collectors.db_writer.asyncpg.create_pool", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_insert_signal_calls_execute(mock_create_pool: AsyncMock) -> None:
    """insert_signal이 올바른 SQL과 파라미터로 execute를 호출하는지 확인."""
    mock_conn = AsyncMock()
    mock_pool = _make_mock_pool(mock_conn)
    mock_create_pool.return_value = mock_pool

    from pipeline.collectors.db_writer import insert_signal

    await insert_signal("서울특별시", "L1", 72.5, raw_value=85.0, source="test")

    mock_conn.execute.assert_called_once()
    call_args = mock_conn.execute.call_args
    assert "INSERT INTO layer_signals" in call_args[0][0]
    assert call_args[0][2] == "L1"
    assert call_args[0][3] == "서울특별시"
    assert call_args[0][4] == 72.5


@patch("pipeline.collectors.db_writer.asyncpg.create_pool", new_callable=AsyncMock)
@pytest.mark.asyncio
async def test_insert_signal_handles_db_error(mock_create_pool: AsyncMock) -> None:
    """DB 에러 발생 시 예외가 전파되는지 확인."""
    mock_conn = AsyncMock()
    mock_conn.execute.side_effect = Exception("connection refused")
    mock_pool = _make_mock_pool(mock_conn)
    mock_create_pool.return_value = mock_pool

    from pipeline.collectors.db_writer import insert_signal

    with pytest.raises(Exception, match="connection refused"):
        await insert_signal("서울특별시", "L1", 50.0)


def test_insert_signal_sync_wrapper() -> None:
    """insert_signal_sync가 동기 호출에서 정상 동작하는지 확인."""
    with patch("pipeline.collectors.db_writer.insert_signal", new_callable=AsyncMock) as mock_insert:
        from pipeline.collectors.db_writer import insert_signal_sync

        insert_signal_sync("서울특별시", "L2", 45.0, raw_value=1200.0, source="kowas")
        mock_insert.assert_called_once_with("서울특별시", "L2", 45.0, raw_value=1200.0, source="kowas")


# ─── Silent-fail #2 (2026-06-09) regression — Event loop closed ───────────
@pytest.mark.asyncio
async def test_get_pool_recreates_on_new_event_loop(monkeypatch) -> None:
    """이전 잡의 closed event loop pool 을 재사용하지 않고 새 pool 생성.

    Silent-fail #2 (2026-06-09): APScheduler BlockingScheduler 가 매 잡마다
    asyncio.run() 으로 새 event loop 생성. db_writer._pool 싱글톤이 이전 loop 의
    pool 객체를 들고 있으면 "Event loop is closed" 에러로 INSERT 실패.
    """
    import asyncio as _asyncio
    import pipeline.collectors.db_writer as dbw

    # 이전 loop 의 가짜 pool 주입 — closed loop 흉내.
    fake_old_loop = MagicMock()
    fake_old_loop.is_closed.return_value = True
    fake_old_pool = MagicMock()
    fake_old_pool._loop = fake_old_loop
    dbw._pool = fake_old_pool

    # 새 pool 생성 mock — 새 loop 의 pool 이라고 가정.
    mock_new_pool = MagicMock()
    mock_new_pool._loop = _asyncio.get_running_loop()

    async def _fake_create_pool(*args, **kwargs):
        return mock_new_pool

    monkeypatch.setattr(dbw.asyncpg, "create_pool", _fake_create_pool)
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@h/db")

    result = await dbw._get_pool()
    assert result is mock_new_pool, "새 event loop 에서 pool 재생성되어야 함"
    assert dbw._pool is mock_new_pool


@pytest.mark.asyncio
async def test_get_pool_reuses_alive_pool() -> None:
    """같은 event loop 에서 두 번 호출 시 pool 재사용 (싱글톤 유지)."""
    import asyncio as _asyncio
    import pipeline.collectors.db_writer as dbw

    fake_pool = MagicMock()
    fake_pool._loop = _asyncio.get_running_loop()
    dbw._pool = fake_pool

    result = await dbw._get_pool()
    assert result is fake_pool, "살아있는 pool 은 재사용되어야 함 (불필요한 connection 생성 방지)"
