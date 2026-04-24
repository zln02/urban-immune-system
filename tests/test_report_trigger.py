"""pipeline.report_trigger 단위 테스트.

Claude API는 unittest.mock.AsyncMock으로 목킹한다.
alert_level별 분기 로직(GREEN 스킵 / YELLOW·ORANGE·RED 생성)을 검증한다.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pipeline.report_trigger import (
    ALERT_LEVELS_TO_REPORT,
    _build_report_prompt,
    _call_claude_haiku,
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

    async def fake_generate(region: str) -> dict | None:
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

    async def fake_generate(region: str) -> dict | None:
        call_regions.append(region)
        if region == "부산광역시":
            raise RuntimeError("의도적 오류")
        return None

    with patch("pipeline.report_trigger.generate_latest_alert_report", side_effect=fake_generate):
        total = await run_nightly_reports()

    # 오류가 있어도 17개 지역 모두 시도
    assert len(call_regions) == 17
    assert total == 0
