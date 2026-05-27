from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from core.config import Settings
from core.logging import get_logger
from models.rfp import DocumentChunk

log = get_logger(__name__)


@dataclass
class RetrievedChunk:
    text: str
    score: float
    metadata: dict[str, Any]


class AbstractVectorStore(ABC):
    @abstractmethod
    async def upsert(self, chunks: list[DocumentChunk]) -> None: ...

    @abstractmethod
    async def query(self, query: str, k: int = 5) -> list[RetrievedChunk]: ...


class InMemoryVectorStore(AbstractVectorStore):
    """Lightweight dev store — substring match scoring (no torch)."""

    def __init__(self) -> None:
        self._chunks: list[DocumentChunk] = []

    async def upsert(self, chunks: list[DocumentChunk]) -> None:
        self._chunks.extend(chunks)

    async def query(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        q = query.lower()
        scored: list[tuple[float, DocumentChunk]] = []
        for c in self._chunks:
            text = c.text.lower()
            score = float(text.count(q[:32])) if q else 0.0
            if q and q[:20] in text:
                score += 10.0
            scored.append((score, c))
        scored.sort(key=lambda x: x[0], reverse=True)
        out: list[RetrievedChunk] = []
        for s, c in scored[:k]:
            out.append(RetrievedChunk(text=c.text, score=s, metadata=dict(c.metadata)))
        return out


class ChromaVectorStore(AbstractVectorStore):
    """ChromaDB on disk — install: pip install -r requirements-chroma.txt (Chroma 1.x has Windows wheels)."""

    def __init__(self, persist_dir: str) -> None:
        try:
            import chromadb  # noqa: PLC0415
        except ImportError as e:
            msg = (
                "chromadb is not installed. pip install chromadb or set VECTOR_STORE_BACKEND=memory"
            )
            raise RuntimeError(msg) from e

        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection("rfp_chunks")

    async def upsert(self, chunks: list[DocumentChunk]) -> None:
        if not chunks:
            return
        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        metadatas = [_stringify_metadata(c.metadata) for c in chunks]

        def _upsert() -> None:
            self._collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

        await asyncio.to_thread(_upsert)

    async def query(self, query: str, k: int = 5) -> list[RetrievedChunk]:
        res = self._collection.query(query_texts=[query], n_results=k)
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0] if res.get("distances") else [0.0] * len(docs)
        out: list[RetrievedChunk] = []
        for i, d in enumerate(docs):
            score = -float(dists[i]) if i < len(dists) else 0.0
            meta = metas[i] if i < len(metas) and isinstance(metas[i], dict) else {}
            out.append(RetrievedChunk(text=d, score=score, metadata=dict(meta)))
        return out


def _stringify_metadata(meta: dict[str, Any]) -> dict[str, str]:
    return {str(k): str(v) for k, v in meta.items()}


def make_vector_store(settings: Settings) -> AbstractVectorStore:
    if settings.vector_store_backend != "chroma":
        return InMemoryVectorStore()
    try:
        return ChromaVectorStore(settings.chroma_persist_dir)
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "vector_store.chroma_fallback",
            error=str(exc),
            hint="Using in-memory store for this run. Set VECTOR_STORE_BACKEND=memory or fix Chroma.",
        )
        return InMemoryVectorStore()

