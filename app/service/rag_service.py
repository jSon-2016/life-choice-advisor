"""院校/专业/行业 RAG 检索。"""

import os
import re

from langchain_community.embeddings import DashScopeEmbeddings
from langchain_core.vectorstores import InMemoryVectorStore

from app.config import RAG_VECTOR_TOP_K
from app.dto.knowledge_hit import KnowledgeEntry
from app.service.knowledge_base_loader import KnowledgeBaseLoader


class RAGService:
    def __init__(self, loader: KnowledgeBaseLoader) -> None:
        self._loader = loader
        self._vector_store: InMemoryVectorStore | None = None
        self._vector_available = bool(os.getenv("DASHSCOPE_API_KEY"))
        if self._vector_available:
            self._rebuild_vector_store()

    def search(self, question: str, *, category: str | None = None) -> str:
        hits = self.search_hits(question, category=category)
        if not hits:
            return "暂无相关知识库条目。"
        return "\n".join(f"- [{h.category}] {h.content}" for h in hits)

    def search_hits(self, question: str, *, category: str | None = None) -> list[KnowledgeEntry]:
        if not question or not question.strip():
            return []
        keyword_hits = self._search_keyword(question, category)
        vector_hits = self._search_vector(question, category)
        return self._dedupe(keyword_hits + vector_hits)

    def build_context_for_gaokao(self, profile: dict) -> str:
        queries = [
            profile.get("province", ""),
            profile.get("subject_track", ""),
            str(profile.get("total_score", "")),
            " ".join(profile.get("interests", [])),
            " ".join(profile.get("preferred_regions", [])),
        ]
        hits: list[KnowledgeEntry] = []
        for q in queries:
            if q.strip():
                hits.extend(self.search_hits(q, category="majors"))
                hits.extend(self.search_hits(q, category="schools"))
        hits = self._dedupe(hits)[: RAG_VECTOR_TOP_K * 3]
        if not hits:
            return ""
        lines = ["## 知识库参考（院校/专业）"]
        lines.extend(f"- [{h.category}/{h.keyword}] {h.content}" for h in hits)
        return "\n".join(lines)

    def build_context_for_career(self, profile: dict) -> str:
        queries = [
            profile.get("major", ""),
            profile.get("university", ""),
            " ".join(profile.get("skills", [])),
            " ".join(profile.get("preferred_cities", [])),
        ]
        hits: list[KnowledgeEntry] = []
        for q in queries:
            if q.strip():
                hits.extend(self.search_hits(q, category="industries"))
                hits.extend(self.search_hits(q, category="majors"))
        hits = self._dedupe(hits)[: RAG_VECTOR_TOP_K * 3]
        if not hits:
            return ""
        lines = ["## 知识库参考（行业/专业就业）"]
        lines.extend(f"- [{h.category}/{h.keyword}] {h.content}" for h in hits)
        return "\n".join(lines)

    def _search_keyword(self, question: str, category: str | None) -> list[KnowledgeEntry]:
        entries = self._loader.get_entries()
        if category:
            entries = [e for e in entries if e.category == category]
        return [e for e in entries if self._matches(question, e.keyword)]

    def _search_vector(self, question: str, category: str | None) -> list[KnowledgeEntry]:
        if not self._vector_available or self._vector_store is None:
            return []
        docs = self._vector_store.similarity_search(question.strip(), k=RAG_VECTOR_TOP_K * 2)
        hits: list[KnowledgeEntry] = []
        for doc in docs:
            cat = str(doc.metadata.get("category", ""))
            if category and cat != category:
                continue
            hits.append(
                KnowledgeEntry(
                    keyword=str(doc.metadata.get("keywords", "")),
                    content=doc.page_content,
                    category=cat,
                )
            )
        return hits[:RAG_VECTOR_TOP_K]

    def _matches(self, question: str, keyword: str) -> bool:
        q = question.lower()
        for part in re.split(r"[\s,，、/]+", keyword.lower()):
            if part and part in q:
                return True
        return keyword.lower() in q

    def _dedupe(self, hits: list[KnowledgeEntry]) -> list[KnowledgeEntry]:
        seen: set[str] = set()
        result: list[KnowledgeEntry] = []
        for h in hits:
            key = f"{h.category}:{h.keyword}:{h.content[:40]}"
            if key not in seen:
                seen.add(key)
                result.append(h)
        return result

    def _rebuild_vector_store(self) -> None:
        entries = self._loader.get_entries()
        if not entries:
            self._vector_store = None
            return
        embeddings = DashScopeEmbeddings(model="text-embedding-v2")
        texts = [e.content for e in entries]
        metadatas = [{"keywords": e.keyword, "category": e.category} for e in entries]
        self._vector_store = InMemoryVectorStore.from_texts(texts, embedding=embeddings, metadatas=metadatas)
