"""backend/app/api/alerts.py 단위 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from backend.app.api.alerts import _compute_alert_level


def test_alert_level_green() -> None:
    assert _compute_alert_level(0.0) == "GREEN"
    assert _compute_alert_level(29.9) == "GREEN"


def test_alert_level_yellow() -> None:
    assert _compute_alert_level(30.0) == "YELLOW"
    assert _compute_alert_level(54.9) == "YELLOW"


def test_alert_level_orange() -> None:
    assert _compute_alert_level(55.0) == "ORANGE"
    assert _compute_alert_level(74.9) == "ORANGE"


def test_alert_level_red() -> None:
    assert _compute_alert_level(75.0) == "RED"
    assert _compute_alert_level(100.0) == "RED"


def test_ensemble_weights_sum_to_one() -> None:
    """앙상블 가중치 합이 1.0인지 확인."""
    from backend.app.api.alerts import W1, W2, W3

    assert abs(W1 + W2 + W3 - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# _get_vdb 싱글톤 sentinel 로직
# ---------------------------------------------------------------------------


def test_get_vdb_returns_none_when_failed() -> None:
    """_VDB_FAILED=True이면 즉시 None 반환."""
    import backend.app.api.alerts as alerts_mod

    orig_failed = alerts_mod._VDB_FAILED
    orig_vdb = alerts_mod._VDB
    try:
        alerts_mod._VDB_FAILED = True
        alerts_mod._VDB = None
        result = alerts_mod._get_vdb()
        assert result is None
    finally:
        alerts_mod._VDB_FAILED = orig_failed
        alerts_mod._VDB = orig_vdb


def test_get_vdb_returns_existing_instance() -> None:
    """이미 초기화된 _VDB 인스턴스를 재사용."""
    import backend.app.api.alerts as alerts_mod

    orig_failed = alerts_mod._VDB_FAILED
    orig_vdb = alerts_mod._VDB
    try:
        fake_vdb = MagicMock()
        alerts_mod._VDB_FAILED = False
        alerts_mod._VDB = fake_vdb
        result = alerts_mod._get_vdb()
        assert result is fake_vdb
    finally:
        alerts_mod._VDB_FAILED = orig_failed
        alerts_mod._VDB = orig_vdb


def test_get_vdb_sets_failed_on_import_error() -> None:
    """EpidemiologyVectorDB import 실패 시 _VDB_FAILED=True 세팅."""
    import backend.app.api.alerts as alerts_mod

    orig_failed = alerts_mod._VDB_FAILED
    orig_vdb = alerts_mod._VDB
    try:
        alerts_mod._VDB_FAILED = False
        alerts_mod._VDB = None
        with patch.dict("sys.modules", {"ml.rag.vectordb": None}):
            result = alerts_mod._get_vdb()
        assert result is None
        assert alerts_mod._VDB_FAILED is True
    finally:
        alerts_mod._VDB_FAILED = orig_failed
        alerts_mod._VDB = orig_vdb


# ---------------------------------------------------------------------------
# _retrieve_rag_context
# ---------------------------------------------------------------------------


def test_retrieve_rag_context_no_vdb_returns_empty() -> None:
    """vdb=None이면 빈 문자열·빈 리스트 반환."""
    import backend.app.api.alerts as alerts_mod

    orig_failed = alerts_mod._VDB_FAILED
    orig_vdb = alerts_mod._VDB
    try:
        alerts_mod._VDB_FAILED = True
        alerts_mod._VDB = None
        ctx, citations = alerts_mod._retrieve_rag_context("서울특별시", {})
        assert ctx == ""
        assert citations == []
    finally:
        alerts_mod._VDB_FAILED = orig_failed
        alerts_mod._VDB = orig_vdb


def test_retrieve_rag_context_with_hits() -> None:
    """검색 결과가 있을 때 올바른 RAG 컨텍스트 빌드."""
    import backend.app.api.alerts as alerts_mod

    orig_failed = alerts_mod._VDB_FAILED
    orig_vdb = alerts_mod._VDB
    try:
        fake_vdb = MagicMock()
        fake_vdb.search.return_value = [
            {
                "text": "인플루엔자 감시 지침",
                "metadata": {"source": "KDCA", "topic": "influenza", "url": "http://kdca.go.kr"},
                "score": 0.95,
            }
        ]
        alerts_mod._VDB_FAILED = False
        alerts_mod._VDB = fake_vdb
        ctx, citations = alerts_mod._retrieve_rag_context(
            "서울특별시", {"alert_level": "YELLOW", "l1": 50, "l2": 60, "l3": 40}
        )
        assert "인플루엔자 감시 지침" in ctx
        assert len(citations) == 1
        assert citations[0]["source"] == "KDCA"
        assert citations[0]["score"] == 0.95
    finally:
        alerts_mod._VDB_FAILED = orig_failed
        alerts_mod._VDB = orig_vdb


def test_retrieve_rag_context_search_exception_returns_empty() -> None:
    """search() 예외 발생 시 빈 컨텍스트 반환."""
    import backend.app.api.alerts as alerts_mod

    orig_failed = alerts_mod._VDB_FAILED
    orig_vdb = alerts_mod._VDB
    try:
        fake_vdb = MagicMock()
        fake_vdb.search.side_effect = RuntimeError("Qdrant down")
        alerts_mod._VDB_FAILED = False
        alerts_mod._VDB = fake_vdb
        ctx, citations = alerts_mod._retrieve_rag_context("부산광역시", {})
        assert ctx == ""
        assert citations == []
    finally:
        alerts_mod._VDB_FAILED = orig_failed
        alerts_mod._VDB = orig_vdb
