import ast
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch


def _load_report_helpers() -> dict[str, object]:
    report_generator_path = Path(__file__).resolve().parents[1] / "ml" / "rag" / "report_generator.py"
    source = report_generator_path.read_text(encoding="utf-8")
    module = ast.parse(source)

    selected_nodes = []
    for node in module.body:
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == "MAX_RAG_DOC_CHARS" for target in node.targets):
                selected_nodes.append(node)
        elif isinstance(node, ast.FunctionDef) and node.name in {"_sanitize_doc_text", "_build_prompt"}:
            selected_nodes.append(node)

    helper_module = ast.Module(body=selected_nodes, type_ignores=[])
    namespace: dict[str, object] = {}
    exec(compile(helper_module, str(report_generator_path), "exec"), namespace)
    return namespace


def test_sanitize_doc_text_collapses_whitespace_and_truncates() -> None:
    helpers = _load_report_helpers()
    sanitize = helpers["_sanitize_doc_text"]
    assert callable(sanitize)
    long_text = "A   B\n\nC\t" + ("x" * 400)
    sanitized = sanitize(long_text)
    assert isinstance(sanitized, str)
    assert "  " not in sanitized
    assert "\n" not in sanitized
    assert len(sanitized) == 300


def test_build_prompt_uses_sanitized_rag_docs() -> None:
    helpers = _load_report_helpers()
    build_prompt = helpers["_build_prompt"]
    assert callable(build_prompt)
    prompt = build_prompt(
        {"time": "2026-03-30", "l1": 10, "l2": 20, "l3": 30, "composite": 40, "alert_level": "YELLOW"},
        [{"text": "line1\nline2"}],
        "서울특별시",
    )
    assert isinstance(prompt, str)
    assert "line1 line2" in prompt


# ---------------------------------------------------------------------------
# 직접 import 기반 테스트 — 실제 커버리지 집계용
# ---------------------------------------------------------------------------

def test_sanitize_doc_text_direct() -> None:
    """_sanitize_doc_text 직접 import 테스트."""
    from ml.rag.report_generator import _sanitize_doc_text
    result = _sanitize_doc_text("hello   world\n\nfoo")
    assert result == "hello world foo"


def test_build_prompt_with_author_year_page() -> None:
    """author/year/page 메타 있을 때 인용 포맷 확인."""
    from ml.rag.report_generator import _build_prompt
    prompt = _build_prompt(
        {"l1": 50, "l2": 60, "l3": 40, "composite": 55, "alert_level": "YELLOW"},
        [{"text": "독감 감시 지침", "metadata": {"author": "Kim", "year": "2024", "page": "5", "topic": "influenza"}}],
        "서울특별시",
    )
    assert "Kim(2024)" in prompt
    assert "p.5" in prompt


def test_build_prompt_with_previous_composite_positive_delta() -> None:
    """previous_composite 있을 때 전주 대비 증감 표시 (양수)."""
    from ml.rag.report_generator import _build_prompt
    prompt = _build_prompt(
        {"composite": 60, "previous_composite": 50, "alert_level": "ORANGE"},
        [],
        "부산광역시",
    )
    assert "+10.0%" in prompt


def test_build_prompt_with_previous_composite_negative_delta() -> None:
    """previous_composite 있을 때 전주 대비 증감 표시 (음수)."""
    from ml.rag.report_generator import _build_prompt
    prompt = _build_prompt(
        {"composite": 40, "previous_composite": 55, "alert_level": "YELLOW"},
        [],
        "대구광역시",
    )
    assert "-15.0%" in prompt


def test_system_prompt_exists() -> None:
    """SYSTEM_PROMPT 상수 존재 및 비어있지 않음."""
    from ml.rag.report_generator import SYSTEM_PROMPT
    assert isinstance(SYSTEM_PROMPT, str)
    assert len(SYSTEM_PROMPT) > 0


import pytest


@pytest.mark.asyncio
async def test_generate_alert_report_mock() -> None:
    """generate_alert_report mock 테스트 — 외부 API 호출 없이 구조 검증."""
    fake_vdb = MagicMock()
    fake_vdb.search.return_value = [
        {"text": "독감 가이드라인", "metadata": {"topic": "flu", "source": "KDCA", "author": "Park", "year": "2023", "page": "10"}, "score": 0.9}
    ]

    with patch("ml.rag.report_generator.EpidemiologyVectorDB", return_value=fake_vdb), \
         patch("ml.rag.report_generator._call_claude", new_callable=AsyncMock, return_value="## 1. 요약\n테스트 리포트"):
        from ml.rag.report_generator import generate_alert_report
        result = await generate_alert_report(
            {"alert_level": "YELLOW", "composite": 55, "l1": 50, "l2": 60, "l3": 40},
            region="서울특별시",
        )
    assert result["region"] == "서울특별시"
    assert result["alert_level"] == "YELLOW"
    assert "테스트 리포트" in result["summary"]
    assert result["rag_sources"] == 1


@pytest.mark.asyncio
async def test_call_claude_no_api_key() -> None:
    """ANTHROPIC_API_KEY 미설정 시 RuntimeError 발생."""
    import ml.rag.report_generator as rg_mod
    orig_key = rg_mod.ANTHROPIC_API_KEY
    try:
        rg_mod.ANTHROPIC_API_KEY = ""
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            await rg_mod._call_claude("test prompt")
    finally:
        rg_mod.ANTHROPIC_API_KEY = orig_key
