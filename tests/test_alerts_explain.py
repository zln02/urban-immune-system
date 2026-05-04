"""GET /api/v1/alerts/explain/{report_id} 단위 테스트.

경보 리포트 XAI 설명 엔드포인트 동작 검증.
- 존재하는 report_id → 모든 필수 키 포함
- 존재하지 않는 report_id → 404
- JSONB 컬럼이 NULL 인 행도 빈 객체/빈 배열로 정상 응답
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from backend.app.api.alerts import explain_alert_report


def _make_db_mock(row_data: dict | None) -> AsyncMock:
    """MappingResult 를 반환하는 AsyncSession mock 생성."""
    mock_result = MagicMock()
    if row_data is not None:
        mapping = MagicMock()
        mapping.get = row_data.get
        mapping.__getitem__ = lambda self, k: row_data[k]
        mock_result.mappings.return_value.first.return_value = mapping
    else:
        mock_result.mappings.return_value.first.return_value = None
    db = AsyncMock()
    db.execute = AsyncMock(return_value=mock_result)
    return db


# 정상 row fixture
_FULL_ROW = {
    "id": 42,
    "region": "서울특별시",
    "alert_level": "YELLOW",
    "summary": "독감 지수 상승 감지",
    "triggered_by": "system_scheduler",
    "trigger_source": "apscheduler_weekly",
    "created_at": datetime(2026, 4, 26, 12, 0, 0, tzinfo=timezone.utc),
    "feature_values": json.dumps({
        "l1_otc": 35.2,
        "l2_wastewater": 42.1,
        "l3_search": 28.9,
        "composite": 36.7,
    }),
    "rag_sources": json.dumps([
        {"topic": "multi_signal_cross_validation", "score": 0.45, "source": "ECDC 2024"},
    ]),
    "model_metadata": json.dumps({"model": "TFT", "version": "tft_synth_v2"}),
}

# JSONB 컬럼이 NULL 인 row fixture
_NULL_JSONB_ROW = {
    "id": 99,
    "region": "부산광역시",
    "alert_level": "GREEN",
    "summary": None,
    "triggered_by": "manual",
    "trigger_source": None,
    "created_at": None,
    "feature_values": None,
    "rag_sources": None,
    "model_metadata": None,
}


@pytest.mark.asyncio
async def test_explain_existing_report_all_keys() -> None:
    """존재하는 report_id 호출 시 필수 키가 모두 포함되어야 한다."""
    db = _make_db_mock(_FULL_ROW)
    response = await explain_alert_report(report_id=42, db=db)

    required = {
        "report_id", "region", "alert_level", "summary",
        "decision_factors", "feature_values", "rag_citations",
        "model_metadata", "audit",
    }
    assert required.issubset(response.keys()), (
        f"누락된 키: {required - response.keys()}"
    )


@pytest.mark.asyncio
async def test_explain_existing_report_values() -> None:
    """응답 값이 DB row 내용과 일치해야 한다."""
    db = _make_db_mock(_FULL_ROW)
    response = await explain_alert_report(report_id=42, db=db)

    assert response["report_id"] == 42
    assert response["region"] == "서울특별시"
    assert response["alert_level"] == "YELLOW"


@pytest.mark.asyncio
async def test_explain_decision_factors_extracted() -> None:
    """feature_values 에서 4개 핵심 지표가 decision_factors 로 추출되어야 한다."""
    db = _make_db_mock(_FULL_ROW)
    response = await explain_alert_report(report_id=42, db=db)

    df = response["decision_factors"]
    assert "l1_otc" in df
    assert "l2_wastewater" in df
    assert "l3_search" in df
    assert "composite" in df
    assert abs(df["l1_otc"] - 35.2) < 0.01


@pytest.mark.asyncio
async def test_explain_rag_citations_list() -> None:
    """rag_sources JSONB 가 list 로 파싱되어 rag_citations 에 반환되어야 한다."""
    db = _make_db_mock(_FULL_ROW)
    response = await explain_alert_report(report_id=42, db=db)

    citations = response["rag_citations"]
    assert isinstance(citations, list)
    assert len(citations) == 1
    assert citations[0]["topic"] == "multi_signal_cross_validation"


@pytest.mark.asyncio
async def test_explain_audit_block() -> None:
    """audit 블록에 triggered_by, trigger_source, created_at 이 포함되어야 한다."""
    db = _make_db_mock(_FULL_ROW)
    response = await explain_alert_report(report_id=42, db=db)

    audit = response["audit"]
    assert audit["triggered_by"] == "system_scheduler"
    assert audit["trigger_source"] == "apscheduler_weekly"
    assert "2026" in audit["created_at"]


@pytest.mark.asyncio
async def test_explain_not_found_raises_404() -> None:
    """존재하지 않는 report_id 는 HTTP 404 를 반환해야 한다."""
    db = _make_db_mock(None)
    with pytest.raises(HTTPException) as exc_info:
        await explain_alert_report(report_id=99999, db=db)
    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_explain_null_jsonb_returns_empty_defaults() -> None:
    """feature_values, rag_sources, model_metadata 가 NULL 이면 빈 객체/빈 배열로 응답해야 한다."""
    db = _make_db_mock(_NULL_JSONB_ROW)
    response = await explain_alert_report(report_id=99, db=db)

    assert response["feature_values"] == {}
    assert response["rag_citations"] == []
    assert response["model_metadata"] == {}
    assert response["decision_factors"] == {}


@pytest.mark.asyncio
async def test_explain_null_jsonb_no_exception() -> None:
    """NULL JSONB 컬럼이 있어도 예외 없이 200 응답해야 한다 (404 아님)."""
    db = _make_db_mock(_NULL_JSONB_ROW)
    response = await explain_alert_report(report_id=99, db=db)
    assert response["report_id"] == 99
    assert response["region"] == "부산광역시"
    assert response["alert_level"] == "GREEN"


@pytest.mark.asyncio
async def test_explain_model_metadata_parsed() -> None:
    """model_metadata JSONB 가 dict 로 파싱되어야 한다."""
    db = _make_db_mock(_FULL_ROW)
    response = await explain_alert_report(report_id=42, db=db)

    mm = response["model_metadata"]
    assert isinstance(mm, dict)
    assert mm.get("model") == "TFT"
    assert mm.get("version") == "tft_synth_v2"
