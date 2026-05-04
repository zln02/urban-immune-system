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
