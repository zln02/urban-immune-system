"""seed_docs.py runtime 커버리지 테스트.

main() 함수의 --dry-run, 정상 실행, 실패 경로 등
실제 임베딩/Qdrant 없이 mock으로 검증한다.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest


# ──────────────────────────────────────────────────────────────────────────────
# SEED_DOCS 임포트 경로
# ──────────────────────────────────────────────────────────────────────────────

def test_seed_docs_import() -> None:
    """SEED_DOCS가 리스트로 임포트된다."""
    from ml.rag.seed_docs import SEED_DOCS
    assert isinstance(SEED_DOCS, list)
    assert len(SEED_DOCS) >= 10


def test_seed_docs_ids_sequential_from_1() -> None:
    """id는 1부터 순차 증가해야 한다."""
    from ml.rag.seed_docs import SEED_DOCS
    ids = [d["id"] for d in SEED_DOCS]
    assert ids == list(range(1, len(SEED_DOCS) + 1))


def test_seed_docs_all_have_year() -> None:
    """모든 문서에 metadata.year(int)가 있어야 한다."""
    from ml.rag.seed_docs import SEED_DOCS
    for doc in SEED_DOCS:
        year = doc.get("metadata", {}).get("year")
        assert isinstance(year, int), f"id={doc['id']} year 없거나 int 아님: {year!r}"


# ──────────────────────────────────────────────────────────────────────────────
# main() --dry-run
# ──────────────────────────────────────────────────────────────────────────────

def test_main_dry_run(capsys: pytest.CaptureFixture) -> None:
    """--dry-run 플래그: 임베딩 없이 문서 목록 출력 후 0 반환."""
    from ml.rag.seed_docs import main

    with patch("sys.argv", ["seed_docs.py", "--dry-run"]):
        rc = main()

    assert rc == 0
    captured = capsys.readouterr()
    assert "#1" in captured.out


def test_main_dry_run_prints_all_docs(capsys: pytest.CaptureFixture) -> None:
    """--dry-run 시 SEED_DOCS 개수만큼 줄이 출력된다."""
    from ml.rag.seed_docs import SEED_DOCS, main

    with patch("sys.argv", ["seed_docs.py", "--dry-run"]):
        main()

    captured = capsys.readouterr()
    lines = [l for l in captured.out.strip().splitlines() if l.startswith("#")]
    assert len(lines) == len(SEED_DOCS)


# ──────────────────────────────────────────────────────────────────────────────
# main() 정상 실행 (mock VDB)
# ──────────────────────────────────────────────────────────────────────────────

def _make_mock_vdb(add_n: int = 20) -> MagicMock:
    """EpidemiologyVectorDB mock 반환."""
    mock_vdb = MagicMock()
    mock_vdb.client = MagicMock()
    mock_vdb.embedder = MagicMock()
    mock_vdb.add_documents.return_value = add_n
    mock_vdb.search.return_value = [
        {"score": 0.9, "text": "테스트 문서", "metadata": {"topic": "test"}},
    ]
    return mock_vdb


def test_main_normal_run_returns_0() -> None:
    """정상 실행(mock VDB): 반환값 0."""
    from ml.rag.seed_docs import main

    mock_vdb = _make_mock_vdb()
    with (
        patch("sys.argv", ["seed_docs.py"]),
        patch("ml.rag.seed_docs.EpidemiologyVectorDB", return_value=mock_vdb),
    ):
        rc = main()

    assert rc == 0


def test_main_normal_run_calls_add_documents() -> None:
    """정상 실행: add_documents가 SEED_DOCS 전체로 호출된다."""
    from ml.rag.seed_docs import SEED_DOCS, main

    mock_vdb = _make_mock_vdb(len(SEED_DOCS))
    with (
        patch("sys.argv", ["seed_docs.py"]),
        patch("ml.rag.seed_docs.EpidemiologyVectorDB", return_value=mock_vdb),
    ):
        main()

    mock_vdb.add_documents.assert_called_once_with(SEED_DOCS)


def test_main_normal_run_calls_search() -> None:
    """정상 실행: 검색 검증 루프에서 search를 여러 번 호출한다."""
    from ml.rag.seed_docs import main

    mock_vdb = _make_mock_vdb()
    with (
        patch("sys.argv", ["seed_docs.py"]),
        patch("ml.rag.seed_docs.EpidemiologyVectorDB", return_value=mock_vdb),
    ):
        main()

    assert mock_vdb.search.call_count >= 1


# ──────────────────────────────────────────────────────────────────────────────
# main() 실패 경로
# ──────────────────────────────────────────────────────────────────────────────

def test_main_returns_1_when_client_none() -> None:
    """VDB client=None: 반환값 1 (임베딩 불가)."""
    from ml.rag.seed_docs import main

    mock_vdb = MagicMock()
    mock_vdb.client = None
    mock_vdb.embedder = MagicMock()

    with (
        patch("sys.argv", ["seed_docs.py"]),
        patch("ml.rag.seed_docs.EpidemiologyVectorDB", return_value=mock_vdb),
    ):
        rc = main()

    assert rc == 1


def test_main_returns_1_when_embedder_none() -> None:
    """VDB embedder=None: 반환값 1."""
    from ml.rag.seed_docs import main

    mock_vdb = MagicMock()
    mock_vdb.client = MagicMock()
    mock_vdb.embedder = None

    with (
        patch("sys.argv", ["seed_docs.py"]),
        patch("ml.rag.seed_docs.EpidemiologyVectorDB", return_value=mock_vdb),
    ):
        rc = main()

    assert rc == 1
