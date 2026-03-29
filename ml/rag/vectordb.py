"""Qdrant 벡터DB — 역학 논문·가이드 임베딩 관리."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "epidemiology_docs")
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_DIM = 384


class EpidemiologyVectorDB:
    """역학 문서 임베딩 저장소."""

    def __init__(self) -> None:
        self.client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.embedder = SentenceTransformer(EMBED_MODEL)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        existing = [c.name for c in self.client.get_collections().collections]
        if COLLECTION_NAME not in existing:
            self.client.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )
            logger.info("Qdrant 컬렉션 생성: %s", COLLECTION_NAME)

    def add_documents(self, docs: list[dict[str, Any]]) -> int:
        """문서 목록을 임베딩해 Qdrant에 저장한다.

        docs: [{"id": int, "text": str, "metadata": dict}, ...]
        """
        texts = [d["text"] for d in docs]
        vectors = self.embedder.encode(texts, show_progress_bar=False).tolist()

        points = [
            PointStruct(id=d["id"], vector=v, payload={"text": d["text"], **d.get("metadata", {})})
            for d, v in zip(docs, vectors)
        ]
        self.client.upsert(collection_name=COLLECTION_NAME, points=points)
        logger.info("Qdrant 임베딩 저장: %d건", len(points))
        return len(points)

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """쿼리와 유사한 역학 문서 top-k를 반환한다."""
        query_vec = self.embedder.encode([query], show_progress_bar=False)[0].tolist()
        results = self.client.search(
            collection_name=COLLECTION_NAME,
            query_vector=query_vec,
            limit=top_k,
        )
        return [
            {"score": r.score, "text": r.payload.get("text", ""), "metadata": r.payload}
            for r in results
        ]
