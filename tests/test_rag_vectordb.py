"""EpidemiologyVectorDB 단위 테스트.

Qdrant client와 SentenceTransformer를 MagicMock으로 완전히 격리.
실제 네트워크/모델 로드 없이 모든 코드 경로를 커버한다.
"""
from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


# ──────────────────────────────────────────────────────────────────────────────
# 헬퍼: 가짜 Qdrant 응답 객체
# ──────────────────────────────────────────────────────────────────────────────

def _make_scored_point(score: float, text: str, extra: dict | None = None) -> Any:
    """query_points 응답의 ScoredPoint를 흉내내는 SimpleNamespace."""
    payload: dict = {"text": text}
    if extra:
        payload.update(extra)
    return SimpleNamespace(score=score, payload=payload)


def _make_query_response(points: list) -> Any:
    return SimpleNamespace(points=points)


def _make_collections_response(names: list[str]) -> Any:
    collections = [SimpleNamespace(name=n) for n in names]
    return SimpleNamespace(collections=collections)


# ──────────────────────────────────────────────────────────────────────────────
# Fixture: mock Qdrant + SentenceTransformer
# ──────────────────────────────────────────────────────────────────────────────

def _make_vdb(collection_exists: bool = True) -> tuple:
    """EpidemiologyVectorDB 인스턴스와 내부 mock 객체를 반환한다."""
    from ml.rag.vectordb import EpidemiologyVectorDB

    mock_client = MagicMock()
    mock_client.get_collections.return_value = _make_collections_response(
        ["epidemiology_docs"] if collection_exists else []
    )

    mock_embedder = MagicMock()
    # encode는 (n_texts, VECTOR_DIM) 형태의 ndarray 반환
    mock_embedder.encode = MagicMock(
        side_effect=lambda texts, **kw: np.zeros((len(texts), 384), dtype="float32")
    )

    with (
        patch("qdrant_client.QdrantClient", return_value=mock_client),
        patch("sentence_transformers.SentenceTransformer", return_value=mock_embedder),
    ):
        vdb = EpidemiologyVectorDB()

    return vdb, mock_client, mock_embedder


# ──────────────────────────────────────────────────────────────────────────────
# __init__ / _ensure_collection
# ──────────────────────────────────────────────────────────────────────────────

class TestInit:
    def test_init_success(self) -> None:
        """정상 초기화: client·embedder 모두 설정된다."""
        vdb, mock_client, mock_embedder = _make_vdb()
        assert vdb.client is mock_client
        assert vdb.embedder is mock_embedder

    def test_ensure_collection_already_exists(self) -> None:
        """컬렉션이 이미 존재하면 create_collection을 호출하지 않는다."""
        vdb, mock_client, _ = _make_vdb(collection_exists=True)
        mock_client.create_collection.assert_not_called()

    def test_ensure_collection_created_when_missing(self) -> None:
        """컬렉션이 없으면 create_collection을 호출한다."""
        vdb, mock_client, _ = _make_vdb(collection_exists=False)
        mock_client.create_collection.assert_called_once()

    def test_qdrant_connection_failure_sets_client_none(self) -> None:
        """Qdrant 연결 실패 시 client=None, embedder는 정상 설정된다."""
        from ml.rag.vectordb import EpidemiologyVectorDB

        mock_embedder = MagicMock()
        mock_embedder.encode = MagicMock(
            side_effect=lambda texts, **kw: np.zeros((len(texts), 384), dtype="float32")
        )

        with (
            patch("qdrant_client.QdrantClient", side_effect=ConnectionError("refused")),
            patch("sentence_transformers.SentenceTransformer", return_value=mock_embedder),
        ):
            vdb = EpidemiologyVectorDB()

        assert vdb.client is None

    def test_sentence_transformer_failure_sets_embedder_none(self) -> None:
        """SentenceTransformer 로드 실패 시 embedder=None."""
        from ml.rag.vectordb import EpidemiologyVectorDB

        mock_client = MagicMock()
        mock_client.get_collections.return_value = _make_collections_response([])

        with (
            patch("qdrant_client.QdrantClient", return_value=mock_client),
            patch(
                "sentence_transformers.SentenceTransformer",
                side_effect=OSError("model not found"),
            ),
        ):
            vdb = EpidemiologyVectorDB()

        assert vdb.embedder is None

    def test_collection_init_exception_is_caught(self, caplog: pytest.LogCaptureFixture) -> None:
        """_ensure_collection 예외는 warning 로그로 흡수된다."""
        from ml.rag.vectordb import EpidemiologyVectorDB

        mock_client = MagicMock()
        mock_client.get_collections.side_effect = RuntimeError("unexpected")
        mock_embedder = MagicMock()
        mock_embedder.encode = MagicMock(
            side_effect=lambda texts, **kw: np.zeros((len(texts), 384), dtype="float32")
        )

        with (
            patch("qdrant_client.QdrantClient", return_value=mock_client),
            patch("sentence_transformers.SentenceTransformer", return_value=mock_embedder),
            caplog.at_level(logging.WARNING),
        ):
            vdb = EpidemiologyVectorDB()

        # client는 설정되지만 컬렉션 초기화는 skip
        assert vdb.client is not None


# ──────────────────────────────────────────────────────────────────────────────
# add_documents
# ──────────────────────────────────────────────────────────────────────────────

class TestAddDocuments:
    def test_add_documents_normal(self) -> None:
        """문서 3건 upsert 정상 경로: 반환값 == len(docs)."""
        vdb, mock_client, _ = _make_vdb()
        docs = [
            {"id": i, "text": f"텍스트 {i}", "metadata": {"topic": f"topic_{i}"}}
            for i in range(3)
        ]
        result = vdb.add_documents(docs)
        assert result == 3
        mock_client.upsert.assert_called_once()

    def test_add_documents_returns_0_when_client_none(self) -> None:
        """client가 None이면 0 반환, upsert 미호출."""
        vdb, mock_client, _ = _make_vdb()
        vdb.client = None
        result = vdb.add_documents([{"id": 1, "text": "test", "metadata": {}}])
        assert result == 0
        mock_client.upsert.assert_not_called()

    def test_add_documents_returns_0_when_embedder_none(self) -> None:
        """embedder가 None이면 0 반환."""
        vdb, mock_client, _ = _make_vdb()
        vdb.embedder = None
        result = vdb.add_documents([{"id": 1, "text": "test", "metadata": {}}])
        assert result == 0

    def test_add_documents_empty_list(self) -> None:
        """빈 docs 리스트: upsert 호출은 되지만 반환값 0."""
        vdb, mock_client, _ = _make_vdb()
        result = vdb.add_documents([])
        assert result == 0

    def test_add_documents_metadata_optional(self) -> None:
        """metadata 키가 없는 문서도 처리 가능해야 한다."""
        vdb, mock_client, _ = _make_vdb()
        docs = [{"id": 99, "text": "no metadata doc"}]
        result = vdb.add_documents(docs)
        assert result == 1

    def test_add_documents_multiple_docs(self) -> None:
        """20건 대량 upsert: 반환값 == 20."""
        vdb, mock_client, _ = _make_vdb()
        docs = [{"id": i, "text": f"doc {i}", "metadata": {}} for i in range(20)]
        result = vdb.add_documents(docs)
        assert result == 20


# ──────────────────────────────────────────────────────────────────────────────
# search
# ──────────────────────────────────────────────────────────────────────────────

class TestSearch:
    def test_search_returns_results(self) -> None:
        """정상 검색: score / text / metadata 포함된 결과 반환."""
        vdb, mock_client, _ = _make_vdb()
        mock_client.query_points.return_value = _make_query_response([
            _make_scored_point(0.95, "독감 유행 경고"),
            _make_scored_point(0.80, "하수 바이오마커"),
        ])

        results = vdb.search("독감 경보", top_k=5)
        assert len(results) == 2
        assert results[0]["score"] == pytest.approx(0.95)
        assert results[0]["text"] == "독감 유행 경고"

    def test_search_empty_results(self) -> None:
        """검색 결과가 0건일 때 빈 리스트 반환."""
        vdb, mock_client, _ = _make_vdb()
        mock_client.query_points.return_value = _make_query_response([])
        results = vdb.search("nothing", top_k=5)
        assert results == []

    def test_search_returns_empty_when_client_none(self) -> None:
        """client가 None이면 빈 리스트 반환."""
        vdb, mock_client, _ = _make_vdb()
        vdb.client = None
        results = vdb.search("query", top_k=5)
        assert results == []
        mock_client.query_points.assert_not_called()

    def test_search_returns_empty_when_embedder_none(self) -> None:
        """embedder가 None이면 빈 리스트 반환."""
        vdb, mock_client, _ = _make_vdb()
        vdb.embedder = None
        results = vdb.search("query", top_k=5)
        assert results == []

    def test_search_top_k_1(self) -> None:
        """top_k=1: query_points에 limit=1 전달."""
        vdb, mock_client, _ = _make_vdb()
        mock_client.query_points.return_value = _make_query_response([
            _make_scored_point(0.99, "최고 유사 문서"),
        ])
        results = vdb.search("독감", top_k=1)
        assert len(results) == 1
        _, kwargs = mock_client.query_points.call_args
        assert kwargs.get("limit") == 1 or mock_client.query_points.call_args[1].get("limit") == 1

    def test_search_top_k_100(self) -> None:
        """top_k=100 경계값: 오류 없이 처리."""
        vdb, mock_client, _ = _make_vdb()
        mock_client.query_points.return_value = _make_query_response([])
        results = vdb.search("query", top_k=100)
        assert isinstance(results, list)

    def test_search_payload_none_handled(self) -> None:
        """payload가 None인 ScoredPoint도 빈 text로 처리된다."""
        vdb, mock_client, _ = _make_vdb()
        point = SimpleNamespace(score=0.5, payload=None)
        mock_client.query_points.return_value = _make_query_response([point])
        results = vdb.search("query")
        assert results[0]["text"] == ""
        assert results[0]["metadata"] == {}

    def test_search_metadata_extra_fields(self) -> None:
        """payload에 topic, source 등 추가 필드가 metadata에 포함된다."""
        vdb, mock_client, _ = _make_vdb()
        mock_client.query_points.return_value = _make_query_response([
            _make_scored_point(0.7, "문서 본문", {"topic": "flu", "source": "WHO"}),
        ])
        results = vdb.search("독감")
        assert results[0]["metadata"]["topic"] == "flu"

    def test_search_default_top_k(self) -> None:
        """top_k 미지정 시 기본값(5)으로 호출된다."""
        vdb, mock_client, _ = _make_vdb()
        mock_client.query_points.return_value = _make_query_response([])
        vdb.search("query")
        call_kwargs = mock_client.query_points.call_args[1]
        assert call_kwargs.get("limit") == 5
