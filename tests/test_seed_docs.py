"""SEED_DOCS 구조 단위 테스트.

임베딩 실행 없이 문서 목록의 정합성(길이, id 유니크, 필수 메타데이터)만 검증한다.
"""
from __future__ import annotations

import ast
from pathlib import Path


def _load_seed_docs() -> list[dict]:
    """seed_docs.py 에서 SEED_DOCS 리스트를 AST 파싱으로 로드.

    외부 의존성(Qdrant, 임베딩 모델) 없이 순수 정적 검증을 수행한다.
    `SEED_DOCS: list[dict] = [...]` 형태(AnnAssign) + `SEED_DOCS = [...]`
    형태(Assign) 둘 다 지원.
    """
    seed_docs_path = Path(__file__).resolve().parents[1] / "ml" / "rag" / "seed_docs.py"
    source = seed_docs_path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    namespace: dict[str, object] = {}
    for node in tree.body:
        target_name: str | None = None
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "SEED_DOCS":
                    target_name = target.id
                    break
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            if node.target.id == "SEED_DOCS":
                target_name = node.target.id
        if target_name == "SEED_DOCS":
            exec(  # noqa: S102
                compile(ast.Module(body=[node], type_ignores=[]), str(seed_docs_path), "exec"),
                namespace,
            )
    return namespace["SEED_DOCS"]  # type: ignore[return-value]


def test_seed_docs_length_at_least_10() -> None:
    """SEED_DOCS 길이가 10 이상이어야 한다 (ml/CLAUDE.md 10~20편 목표)."""
    docs = _load_seed_docs()
    assert len(docs) >= 10, f"SEED_DOCS 길이 {len(docs)} < 10 — ml/CLAUDE.md 목표 미달"


def test_seed_docs_ids_unique() -> None:
    """각 문서의 id 값이 중복 없이 유니크해야 한다."""
    docs = _load_seed_docs()
    ids = [d["id"] for d in docs]
    assert len(ids) == len(set(ids)), f"중복 id 존재: {[x for x in ids if ids.count(x) > 1]}"


def test_seed_docs_required_metadata_fields() -> None:
    """모든 문서에 metadata.source, metadata.url, metadata.topic 이 존재해야 한다."""
    docs = _load_seed_docs()
    required = {"source", "url", "topic"}
    for doc in docs:
        metadata = doc.get("metadata", {})
        missing = required - set(metadata.keys())
        assert not missing, (
            f"id={doc['id']} metadata 누락 필드: {missing}"
        )


def test_seed_docs_text_not_empty() -> None:
    """모든 문서의 text 가 비어있지 않아야 한다."""
    docs = _load_seed_docs()
    for doc in docs:
        assert doc.get("text", "").strip(), f"id={doc['id']} text 비어있음"


def test_seed_docs_metadata_url_starts_with_https() -> None:
    """모든 문서의 metadata.url 이 https:// 로 시작해야 한다."""
    docs = _load_seed_docs()
    for doc in docs:
        url = doc.get("metadata", {}).get("url", "")
        assert url.startswith("https://"), (
            f"id={doc['id']} url이 https:// 아님: {url!r}"
        )


def test_seed_docs_topic_snake_case() -> None:
    """metadata.topic 이 공백·대문자 없는 snake_case 여야 한다."""
    docs = _load_seed_docs()
    for doc in docs:
        topic = doc.get("metadata", {}).get("topic", "")
        assert topic == topic.lower(), f"id={doc['id']} topic에 대문자 포함: {topic!r}"
        assert " " not in topic, f"id={doc['id']} topic에 공백 포함: {topic!r}"
