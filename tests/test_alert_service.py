"""alert_service.py 단위 테스트 (8개) — AsyncMock DB 기반."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from backend.app.services.alert_service import (
    get_latest_alert,
    get_latest_risk_score,
    save_alert_report,
)

# ---------------------------------------------------------------------------
# 헬퍼
# ---------------------------------------------------------------------------


def _make_mock_db(fetchone_return=None, mappings_first_return=None) -> AsyncMock:
    """SQLAlchemy AsyncSession mock 생성.

    - execute → result mock
    - result.mappings().first() → mappings_first_return
    - result.first()           → fetchone_return
    """
    mock_result = MagicMock()
    mock_result.first.return_value = fetchone_return

    # .mappings().first() 체인
    mock_mappings = MagicMock()
    mock_mappings.first.return_value = mappings_first_return
    mock_result.mappings.return_value = mock_mappings

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    return mock_db


# ---------------------------------------------------------------------------
# get_latest_alert
# ---------------------------------------------------------------------------


async def test_get_latest_alert_found() -> None:
    """row 존재 → dict 반환."""
    row_data = {
        "region": "서울특별시",
        "alert_level": "YELLOW",
        "summary": "인플루엔자 주의 단계",
        "recommendations": "손 씻기 강화",
        "model_used": "xgboost",
        "created_at": "2026-05-10 09:00:00",
        "triggered_by": "system_scheduler",
        "trigger_source": None,
        "feature_values": None,
        "rag_sources": None,
        "model_metadata": None,
    }
    mock_db = _make_mock_db(mappings_first_return=row_data)

    result = await get_latest_alert("서울특별시", mock_db)
    assert result is not None
    assert result["alert_level"] == "YELLOW"
    assert result["region"] == "서울특별시"


async def test_get_latest_alert_not_found() -> None:
    """row 없음 → None 반환."""
    mock_db = _make_mock_db(mappings_first_return=None)

    result = await get_latest_alert("존재하지않는지역", mock_db)
    assert result is None


# ---------------------------------------------------------------------------
# get_latest_risk_score
# ---------------------------------------------------------------------------


async def test_get_latest_risk_score_found() -> None:
    """row 존재 → dict 반환."""
    row_data = {
        "time": "2026-05-10 09:00:00",
        "region": "부산광역시",
        "composite_score": 45.2,
        "l1_score": 50.0,
        "l2_score": 40.0,
        "l3_score": 42.0,
        "alert_level": "YELLOW",
    }
    mock_db = _make_mock_db(mappings_first_return=row_data)

    result = await get_latest_risk_score("부산광역시", mock_db)
    assert result is not None
    assert result["composite_score"] == 45.2
    assert result["alert_level"] == "YELLOW"


async def test_get_latest_risk_score_not_found() -> None:
    """row 없음 → None 반환."""
    mock_db = _make_mock_db(mappings_first_return=None)

    result = await get_latest_risk_score("없는지역", mock_db)
    assert result is None


# ---------------------------------------------------------------------------
# save_alert_report
# ---------------------------------------------------------------------------


async def test_save_alert_report_with_dicts() -> None:
    """feature_values, rag_sources, model_metadata 모두 dict → insert 호출."""
    data = {
        "region": "서울특별시",
        "alert_level": "RED",
        "summary": "심각 단계 경보",
        "recommendations": "외출 자제",
        "model_used": "xgboost",
        "triggered_by": "api_trigger",
        "trigger_source": "manual",
        "feature_values": {"l1": 82.0, "l2": 78.0},
        "rag_sources": {"doc1": "출처1"},
        "model_metadata": {"version": "v1.2"},
    }
    mock_db = _make_mock_db(fetchone_return=(10,))

    result = await save_alert_report(data, mock_db)
    mock_db.execute.assert_awaited_once()
    mock_db.commit.assert_awaited_once()
    assert result == 10


async def test_save_alert_report_with_nones() -> None:
    """feature_values, rag_sources, model_metadata 모두 None → insert 호출 (json.dumps 없음)."""
    data = {
        "region": "대전광역시",
        "alert_level": "GREEN",
        "summary": "정상",
        "feature_values": None,
        "rag_sources": None,
        "model_metadata": None,
    }
    mock_db = _make_mock_db(fetchone_return=(5,))

    result = await save_alert_report(data, mock_db)
    mock_db.execute.assert_awaited_once()
    mock_db.commit.assert_awaited_once()
    assert result == 5


async def test_save_alert_report_returns_id() -> None:
    """RETURNING id → 정수 id 반환."""
    data = {
        "region": "인천광역시",
        "alert_level": "YELLOW",
        "summary": "주의 단계",
    }
    mock_db = _make_mock_db(fetchone_return=(42,))

    result = await save_alert_report(data, mock_db)
    assert result == 42


async def test_save_alert_report_no_id() -> None:
    """RETURNING id 결과가 None → -1 반환."""
    data = {
        "region": "광주광역시",
        "alert_level": "GREEN",
        "summary": "정상",
    }
    mock_db = _make_mock_db(fetchone_return=None)

    result = await save_alert_report(data, mock_db)
    assert result == -1
