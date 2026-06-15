"""Chroma 持久化向量库：知识库变更时自动重建。"""

import hashlib
import logging
import os
import shutil
from pathlib import Path

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.config import RAG_CHROMA_PATH
from app.dto.knowledge_hit import KnowledgeEntry
from app.service.knowledge_base_loader import KnowledgeBaseLoader

logger = logging.getLogger(__name__)


class PersistentVectorStore:
    """基于 Chroma 的持久化向量索引。"""

    def __init__(self, loader: KnowledgeBaseLoader, *, persist_path: str | None = None) -> None:
        self._loader = loader
        root = Path(__file__).resolve().parents[2]
        self._path = root / (persist_path or RAG_CHROMA_PATH)
        self._hash_file = self._path / ".knowledge_hash"
        self._available = bool(os.getenv("DASHSCOPE_API_KEY"))
        self._store: Chroma | None = None
        if self._available:
            self._ensure_store()

    @property
    def available(self) -> bool:
        return self._available and self._store is not None

    def similarity_search(
        self,
        query: str,
        *,
        category: str | None = None,
        k: int = 10,
    ) -> list[tuple[KnowledgeEntry, float]]:
        """向量检索，返回 (条目, distance)。"""
        if not self.available or self._store is None:
            return []
        filt = {"category": category} if category else None
        try:
            pairs = self._store.similarity_search_with_score(query.strip(), k=k, filter=filt)
        except Exception as exc:
            logger.warning("向量检索失败: %s", exc)
            return []

        hits: list[tuple[KnowledgeEntry, float]] = []
        for doc, distance in pairs:
            hits.append(
                (
                    KnowledgeEntry(
                        keyword=str(doc.metadata.get("keywords", "")),
                        content=doc.page_content,
                        category=str(doc.metadata.get("category", "")),
                        retrieval_source="vector",
                    ),
                    float(distance),
                )
            )
        return hits

    def _ensure_store(self) -> None:
        entries = self._loader.get_entries()
        if not entries:
            self._store = None
            return

        current_hash = _hash_entries(entries)
        if self._hash_file.exists() and self._hash_file.read_text(encoding="utf-8") == current_hash:
            try:
                embeddings = DashScopeEmbeddings(model="text-embedding-v2")
                self._store = Chroma(
                    collection_name="knowledge",
                    embedding_function=embeddings,
                    persist_directory=str(self._path),
                )
                return
            except Exception as exc:
                logger.warning("加载 Chroma 失败，将重建: %s", exc)

        self._rebuild(entries, current_hash)

    def _rebuild(self, entries: list[KnowledgeEntry], content_hash: str) -> None:
        if self._path.exists():
            shutil.rmtree(self._path)
        self._path.mkdir(parents=True, exist_ok=True)

        documents = [
            Document(
                page_content=e.content,
                metadata={"keywords": e.keyword, "category": e.category, "source_id": e.source_id},
            )
            for e in entries
        ]
        embeddings = DashScopeEmbeddings(model="text-embedding-v2")
        self._store = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            collection_name="knowledge",
            persist_directory=str(self._path),
        )
        self._hash_file.write_text(content_hash, encoding="utf-8")
        logger.info("Chroma 向量库已重建，共 %d 条", len(entries))


def _hash_entries(entries: list[KnowledgeEntry]) -> str:
    payload = "\n".join(f"{e.category}|{e.keyword}|{e.content}" for e in entries)
    return hashlib.sha256(payload.encode()).hexdigest()
