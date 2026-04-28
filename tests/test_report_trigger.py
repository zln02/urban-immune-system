"""pipeline.report_trigger 단위 테스트.

Claude API는 unittest.mock.AsyncMock으로 목킹한다.
alert_level별 분기 로직(GREEN 스킵 / YELLOW·ORANGE·RED 생성)을 검증한다.
감사로그(triggered_by, trigger_source) 및 XAI 메타데이터 컬럼도 검증한다.
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.report_trigger import (
    ALERT_LEVELS_TO_REPORT,
    _build_report_prompt,
    _call_claude_haiku,
    _insert_alert_report,
    generate_latest_alert_report,
    run_nightly_reports,
)


# ---------------------------------------------------------------------------
# _build_report_prompt 테스트
# ---------------------------------------------------------------------------

def test_build_report_prompt_includes_all_signals() -> None:
    """프롬프트에 L1/L2/L3, composite, alert_level이 모두 포함되는지 검증."""
    signals = {
        "time": "2026-04-24 12:00:00+09:00",
        "l1": 45.5,
        "l2": 60.0,
        "l3": 30.2,
        "composite": 48.7,
        "alert_level": "YELLOW",
    }
    prompt = _build_report_prompt("서울특별시", signals)

    assert "서울특별시" in prompt
    assert "45.5" in prompt
    assert "60.0" in prompt
    assert "30.2" in prompt
    assert "48.7" in prompt
    assert "YELLOW" in prompt
    # 의료 진단 문구가 없어야 함
    assert "진단" not in prompt
    assert "처방" not in prompt


def test_build_report_prompt_na_fallback() -> None:
    """신호 값이 없을 때 'N/A'로 채워지는지 검증."""
    prompt = _build_report_prompt("부산광역시", {})
    assert "N/A" in prompt


# ---------------------------------------------------------------------------
# ALERT_LEVELS_TO_REPORT 분기 로직
# ---------------------------------------------------------------------------

def test_alert_levels_to_report_excludes_green() -> None:
    """GREEN이 보고 대상에서 제외되는지 검증."""
    assert "GREEN" not in ALERT_LEVELS_TO_REPORT


def test_alert_levels_to_report_includes_non_green() -> None:
    """YELLOW/ORANGE/RED가 보고 대상에 포함되는지 검증."""
    assert "YELLOW" in ALERT_LEVELS_TO_REPORT
    assert "ORANGE" in ALERT_LEVELS_TO_REPORT
    assert "RED" in ALERT_LEVELS_TO_REPORT


# ---------------------------------------------------------------------------
# _call_claude_haiku 테스트
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_call_claude_haiku_raises_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """ANTHROPIC_API_KEY 미설정 시 RuntimeError 발생을 검증."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        await _call_claude_haiku("테스트 프롬프트")


@pytest.mark.asyncio
async def test_call_claude_haiku_returns_text(monkeypatch: pytest.MonkeyPatch) -> None:
    """Claude API 호출이 성공하면 텍스트가 반환되는지 검증 (Mock 사용)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-mock")

    mock_content = MagicMock()
    mock_content.text = "테스트 경보 리포트 내용입니다."

    mock_response = MagicMock()
    mock_response.content = [mock_content]

    mock_create = AsyncMock(return_value=mock_response)
    mock_client = MagicMock()
    mock_client.messages.create = mock_create

    with patch("anthropic.AsyncAnthropic", return_value=mock_client):
        result = await _call_claude_haiku("테스트 프롬프트")

    assert result == "테스트 경보 리포트 내용입니다."
    mock_create.assert_called_once()
    call_kwargs = mock_create.call_args.kwargs
    assert call_kwargs["model"] == "claude-haiku-4-5-20251001"
    assert call_kwargs["max_tokens"] == 1200


# ---------------------------------------------------------------------------
# generate_latest_alert_report 분기 로직 테스트
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate_skips_when_no_risk_score(monkeypatch: pytest.MonkeyPatch) -> None:
    """risk_scores 데이터가 없으면 None 반환 검증."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-mock")

    with (
        patch("pipeline.report_trigger._get_engine") as mock_engine_fn,
        patch("pipeline.report_trigger._fetch_latest_risk_score", new_callable=AsyncMock, return_value=None),
    ):
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_engine_fn.return_value = mock_engine

        result = await generate_latest_alert_report("서울특별시")

    assert result is None


@pytest.mark.asyncio
async def test_generate_skips_green_alert(monkeypatch: pytest.MonkeyPatch) -> None:
    """GREEN 경보일 때 None 반환 (스킵) 검증."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-mock")

    fake_risk = {
        "time": "2026-04-24T12:00:00+09:00",
        "region": "서울특별시",
        "composite_score": 20.0,
        "l1_score": 15.0,
        "l2_score": 18.0,
        "l3_score": 10.0,
        "alert_level": "GREEN",
    }

    with (
        patch("pipeline.report_trigger._get_engine") as mock_engine_fn,
        patch("pipeline.report_trigger._fetch_latest_risk_score", new_callable=AsyncMock, return_value=fake_risk),
    ):
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_engine_fn.return_value = mock_engine

        result = await generate_latest_alert_report("서울특별시")

    assert result is None


@pytest.mark.asyncio
async def test_generate_creates_report_for_yellow(monkeypatch: pytest.MonkeyPatch) -> None:
    """YELLOW 경보일 때 리포트가 생성되고 dict 반환 검증."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-mock")

    fake_risk = {
        "time": "2026-04-24T12:00:00+09:00",
        "region": "서울특별시",
        "composite_score": 42.0,
        "l1_score": 40.0,
        "l2_score": 45.0,
        "l3_score": 35.0,
        "alert_level": "YELLOW",
    }

    with (
        patch("pipeline.report_trigger._get_engine") as mock_engine_fn,
        patch("pipeline.report_trigger._fetch_latest_risk_score", new_callable=AsyncMock, return_value=fake_risk),
        patch("pipeline.report_trigger._call_claude_haiku", new_callable=AsyncMock, return_value="YELLOW 경보 리포트"),
        patch("pipeline.report_trigger._insert_alert_report", new_callable=AsyncMock, return_value=42),
    ):
        # async_sessionmaker context manager 목킹
        mock_session = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)

        mock_session_factory = MagicMock(return_value=mock_cm)
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_engine_fn.return_value = mock_engine

        with patch("pipeline.report_trigger.async_sessionmaker", return_value=mock_session_factory):
            result = await generate_latest_alert_report("서울특별시")

    assert result is not None
    assert result["alert_level"] == "YELLOW"
    assert result["region"] == "서울특별시"
    assert result["summary"] == "YELLOW 경보 리포트"
    assert result["id"] == 42


@pytest.mark.asyncio
async def test_run_nightly_reports_counts_generated(monkeypatch: pytest.MonkeyPatch) -> None:
    """run_nightly_reports가 생성 건수를 올바르게 반환하는지 검증."""
    call_count = 0

    async def fake_generate(region: str, triggered_by: str = "system_scheduler", trigger_source: str | None = None) -> dict | None:
        nonlocal call_count
        # 첫 3개 지역만 성공, 나머지는 스킵(None)
        if call_count < 3:
            call_count += 1
            return {"id": call_count, "region": region, "alert_level": "YELLOW", "summary": "test"}
        return None

    with patch("pipeline.report_trigger.generate_latest_alert_report", side_effect=fake_generate):
        total = await run_nightly_reports()

    assert total == 3


@pytest.mark.asyncio
async def test_run_nightly_reports_continues_on_error() -> None:
    """지역 처리 중 예외가 발생해도 다음 지역으로 계속 진행하는지 검증."""
    call_regions: list[str] = []

    async def fake_generate(region: str, triggered_by: str = "system_scheduler", trigger_source: str | None = None) -> dict | None:
        call_regions.append(region)
        if region == "부산광역시":
            raise RuntimeError("의도적 오류")
        return None

    with patch("pipeline.report_trigger.generate_latest_alert_report", side_effect=fake_generate):
        total = await run_nightly_reports()

    # 오류가 있어도 17개 지역 모두 시도
    assert len(call_regions) == 17
    assert total == 0


# ---------------------------------------------------------------------------
# 감사로그 + XAI 메타데이터 신규 테스트 (ISMS-P 2.9 대응)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_insert_alert_report_includes_audit_and_xai_columns() -> None:
    """_insert_alert_report가 감사로그·XAI 컬럼을 INSERT 쿼리에 올바르게 전달하는지 검증."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (99,)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    feature_values = {"l1": 40.0, "l2": 55.0, "l3": 32.0, "composite": 44.3}
    rag_sources = [{"topic": "influenza_guideline", "score": 0.87, "source": "KCDC"}]
    model_metadata = {"model": "claude-haiku-4-5-20251001", "max_tokens": 1200, "system_prompt_hash": "abc123ef", "prompt_version": "v2"}

    result_id = await _insert_alert_report(
        region="서울특별시",
        alert_level="YELLOW",
        summary="테스트 리포트",
        session=mock_session,
        triggered_by="manual_cli",
        trigger_source="--region 서울특별시",
        feature_values=feature_values,
        rag_sources=rag_sources,
        model_metadata=model_metadata,
    )

    assert result_id == 99
    mock_session.execute.assert_called_once()
    call_args = mock_session.execute.call_args

    # INSERT 쿼리에 새 컬럼 포함 확인
    query_str = str(call_args[0][0])
    assert "triggered_by" in query_str
    assert "trigger_source" in query_str
    assert "feature_values" in query_str
    assert "rag_sources" in query_str
    assert "model_metadata" in query_str

    # 파라미터 딕셔너리 확인
    params = call_args[0][1]
    assert params["triggered_by"] == "manual_cli"
    assert params["trigger_source"] == "--region 서울특별시"

    # JSON 직렬화 검증 — feature_values
    fv_parsed = json.loads(params["feature_values"])
    assert fv_parsed["l1"] == 40.0
    assert fv_parsed["composite"] == 44.3

    # JSON 직렬화 검증 — rag_sources
    rs_parsed = json.loads(params["rag_sources"])
    assert isinstance(rs_parsed, list)
    assert rs_parsed[0]["topic"] == "influenza_guideline"
    assert rs_parsed[0]["score"] == 0.87

    # JSON 직렬화 검증 — model_metadata
    mm_parsed = json.loads(params["model_metadata"])
    assert mm_parsed["model"] == "claude-haiku-4-5-20251001"
    assert mm_parsed["max_tokens"] == 1200


@pytest.mark.asyncio
async def test_insert_alert_report_null_xai_when_not_provided() -> None:
    """XAI 컬럼 미전달 시 None(NULL)으로 INSERT 되는지 검증 (이전 row 호환성)."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (10,)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    result_id = await _insert_alert_report(
        region="부산광역시",
        alert_level="RED",
        summary="긴급 리포트",
        session=mock_session,
        # feature_values, rag_sources, model_metadata 미전달
    )

    assert result_id == 10
    params = mock_session.execute.call_args[0][1]
    assert params["feature_values"] is None
    assert params["rag_sources"] is None
    assert params["model_metadata"] is None


@pytest.mark.asyncio
async def test_insert_alert_report_empty_rag_sources() -> None:
    """rag_sources가 빈 리스트일 때 JSON '[]'로 직렬화되는지 검증 (Qdrant 미작동 시)."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = (5,)
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.commit = AsyncMock()

    await _insert_alert_report(
        region="대구광역시",
        alert_level="YELLOW",
        summary="RAG 없는 리포트",
        session=mock_session,
        rag_sources=[],  # Qdrant 미작동 시 빈 리스트
    )

    params = mock_session.execute.call_args[0][1]
    rs_parsed = json.loads(params["rag_sources"])
    assert rs_parsed == []


@pytest.mark.asyncio
async def test_generate_returns_xai_metadata_in_result(monkeypatch: pytest.MonkeyPatch) -> None:
    """generate_latest_alert_report 반환값에 XAI 메타데이터가 포함되는지 검증."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-mock")

    fake_risk = {
        "time": "2026-04-27T09:00:00+09:00",
        "region": "서울특별시",
        "composite_score": 42.0,
        "l1_score": 40.0,
        "l2_score": 45.0,
        "l3_score": 35.0,
        "alert_level": "YELLOW",
    }

    with (
        patch("pipeline.report_trigger._get_engine") as mock_engine_fn,
        patch("pipeline.report_trigger._fetch_latest_risk_score", new_callable=AsyncMock, return_value=fake_risk),
        patch("pipeline.report_trigger._fetch_rag_context", return_value=[
            {"metadata": {"topic": "flu_guideline", "source": "KCDC"}, "score": 0.91, "text": "테스트 가이드라인"},
        ]),
        patch("pipeline.report_trigger._call_claude_haiku", new_callable=AsyncMock, return_value="YELLOW 경보 리포트"),
        patch("pipeline.report_trigger._insert_alert_report", new_callable=AsyncMock, return_value=77),
    ):
        mock_session = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session_factory = MagicMock(return_value=mock_cm)
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_engine_fn.return_value = mock_engine

        with patch("pipeline.report_trigger.async_sessionmaker", return_value=mock_session_factory):
            result = await generate_latest_alert_report("서울특별시", triggered_by="manual_cli")

    assert result is not None
    assert result["triggered_by"] == "manual_cli"

    # feature_values 구조 확인
    fv = result["feature_values"]
    assert fv["l1"] == 40.0
    assert fv["l2"] == 45.0
    assert fv["composite"] == 42.0

    # rag_sources 구조 확인
    rs = result["rag_sources"]
    assert len(rs) == 1
    assert rs[0]["topic"] == "flu_guideline"
    assert rs[0]["score"] == 0.91

    # model_metadata 구조 확인
    mm = result["model_metadata"]
    assert mm["model"] == "claude-haiku-4-5-20251001"
    assert mm["max_tokens"] == 1200
    assert "system_prompt_hash" in mm
    assert mm["prompt_version"] == "v2"


@pytest.mark.asyncio
async def test_generate_passes_triggered_by_to_insert(monkeypatch: pytest.MonkeyPatch) -> None:
    """triggered_by 파라미터가 _insert_alert_report로 올바르게 전달되는지 검증."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-mock")

    fake_risk = {
        "time": "2026-04-27T09:00:00+09:00",
        "region": "인천광역시",
        "composite_score": 60.0,
        "l1_score": 55.0,
        "l2_score": 65.0,
        "l3_score": 50.0,
        "alert_level": "ORANGE",
    }

    captured_kwargs: dict = {}

    async def fake_insert(region, alert_level, summary, session, **kwargs):
        captured_kwargs.update(kwargs)
        return 88

    with (
        patch("pipeline.report_trigger._get_engine") as mock_engine_fn,
        patch("pipeline.report_trigger._fetch_latest_risk_score", new_callable=AsyncMock, return_value=fake_risk),
        patch("pipeline.report_trigger._fetch_rag_context", return_value=[]),
        patch("pipeline.report_trigger._call_claude_haiku", new_callable=AsyncMock, return_value="ORANGE 경보"),
        patch("pipeline.report_trigger._insert_alert_report", side_effect=fake_insert),
    ):
        mock_session = AsyncMock()
        mock_cm = AsyncMock()
        mock_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_cm.__aexit__ = AsyncMock(return_value=False)
        mock_session_factory = MagicMock(return_value=mock_cm)
        mock_engine = MagicMock()
        mock_engine.dispose = AsyncMock()
        mock_engine_fn.return_value = mock_engine

        with patch("pipeline.report_trigger.async_sessionmaker", return_value=mock_session_factory):
            await generate_latest_alert_report(
                "인천광역시",
                triggered_by="api_request",
                trigger_source="POST /api/v1/alerts/generate ip=10.0.0.1",
            )

    assert captured_kwargs["triggered_by"] == "api_request"
    assert captured_kwargs["trigger_source"] == "POST /api/v1/alerts/generate ip=10.0.0.1"
    # rag_sources가 빈 리스트여도 전달됨
    assert captured_kwargs["rag_sources"] == []
