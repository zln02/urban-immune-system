"""Qdrant 벡터DB — 역학 논문·가이드 임베딩 관리."""
from __future__ import annotations

import logging
import os
from typing import Any

from qdrant_client.models import Distance, PointStruct, VectorParams

logger = logging.getLogger(__name__)

QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION", "epidemiology_docs")
EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
VECTOR_DIM = 384


class EpidemiologyVectorDB:
    """역학 문서 임베딩 저장소."""

    def __init__(self, host: str = QDRANT_HOST, port: int = QDRANT_PORT, model_name: str = EMBED_MODEL) -> None:
        self.client = None
        self.model = None
        self.embedder = None

        try:
            from qdrant_client import QdrantClient

            self.client = QdrantClient(host=host, port=port, timeout=10)
        except Exception as exc:
            logger.warning("Qdrant connection failed: %s", exc)

        try:
            from sentence_transformers import SentenceTransformer

            self.model = SentenceTransformer(model_name)
            self.embedder = self.model
        except Exception as exc:
            logger.warning("SentenceTransformer load failed: %s", exc)

        if self.client is not None:
            try:
                self._ensure_collection()
            except Exception as exc:
                logger.warning("Qdrant collection init failed: %s", exc)

    def _ensure_collection(self) -> None:
        if self.client is None:
            return
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
        if self.client is None or self.embedder is None:
            logger.warning("Qdrant 또는 임베딩 모델이 초기화되지 않아 add_documents를 건너뜁니다")
            return 0

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
        """쿼리와 유사한 역학 문서 top-k를 반환한다.

        qdrant-client 1.10+ 의 query_points API를 사용한다 (구 search는 deprecated).
        """
        if self.client is None or self.embedder is None:
            logger.warning("Qdrant 또는 임베딩 모델이 초기화되지 않아 search 결과를 비웁니다")
            return []

        query_vec = self.embedder.encode([query], show_progress_bar=False)[0].tolist()
        response = self.client.query_points(
            collection_name=COLLECTION_NAME,
            query=query_vec,
            limit=top_k,
        )
        return [
            {
                "score": p.score,
                "text": (p.payload or {}).get("text", ""),
                "metadata": p.payload or {},
            }
            for p in response.points
        ]
