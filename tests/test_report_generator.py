import ast
from pathlib import Path


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
