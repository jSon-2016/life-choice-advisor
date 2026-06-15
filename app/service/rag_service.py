"""院校/专业/行业 RAG 检索：Hybrid + RRF + Rerank + 拒答 + 引用。"""

import re

from app.config import (
    RAG_RECALL_TOP_K,
    RAG_RERANK_THRESHOLD,
    RAG_RERANK_TOP_N,
    RAG_RRF_K,
    RAG_VECTOR_TOP_K,
)
from app.dto.knowledge_hit import KnowledgeEntry
from app.dto.rag_context import RAGContextResult
from app.service.knowledge_base_loader import KnowledgeBaseLoader
from app.service.rerank_service import RerankService
from app.service.vector_store import PersistentVectorStore


class RAGService:
    """Hybrid RAG：关键词 + 向量(Chroma) → RRF 融合 → Rerank → 阈值拒答。"""

    def __init__(self, loader: KnowledgeBaseLoader) -> None:
        self._loader = loader
        self._vector_store = PersistentVectorStore(loader)
        self._rerank = RerankService()

    def search(self, question: str, *, category: str | None = None) -> str:
        result = self.search_with_meta(question, category=category)
        return result.context or "暂无相关知识库条目。"

    def search_hits(self, question: str, *, category: str | None = None) -> list[KnowledgeEntry]:
        return self.search_with_meta(question, category=category).hits

    def search_with_meta(self, question: str, *, category: str | None = None) -> RAGContextResult:
        """单查询完整流水线。"""
        if not question or not question.strip():
            return RAGContextResult(context="", low_confidence=True, top_score=0.0, hits=[])

        keyword_hits = self._search_keyword(question, category)
        vector_hits = self._search_vector(question, category)
        fused = self._rrf_fuse(keyword_hits, vector_hits)[: max(RAG_RECALL_TOP_K, RAG_RERANK_TOP_N)]
        if not fused:
            return self._low_confidence_result([], query=question.strip())

        reranked = self._rerank.rerank(question, fused, top_n=RAG_RERANK_TOP_N)
        return self._build_result(reranked, header="## 知识库参考")

    def build_context_for_gaokao(self, profile: dict) -> RAGContextResult:
        """按省份、科类、分数、兴趣等维度检索 majors/schools。"""
        queries = [
            profile.get("province", ""),
            profile.get("subject_track", ""),
            str(profile.get("total_score", "")),
            " ".join(profile.get("interests", [])),
            " ".join(profile.get("preferred_regions", [])),
        ]
        composite_query = " ".join(q.strip() for q in queries if q and str(q).strip())
        return self._build_multi_query_context(
            queries,
            categories=["majors", "schools"],
            header="## 知识库参考（院校/专业）",
            composite_query=composite_query,
        )

    def build_context_for_career(self, profile: dict) -> RAGContextResult:
        """按专业、院校、技能、意向城市检索 industries/majors。"""
        queries = [
            profile.get("major", ""),
            profile.get("university", ""),
            " ".join(profile.get("skills", [])),
            " ".join(profile.get("preferred_cities", [])),
        ]
        composite_query = " ".join(q.strip() for q in queries if q and str(q).strip())
        return self._build_multi_query_context(
            queries,
            categories=["industries", "majors"],
            header="## 知识库参考（行业/专业就业）",
            composite_query=composite_query,
        )

    def _build_multi_query_context(
        self,
        queries: list[str],
        *,
        categories: list[str],
        header: str,
        composite_query: str,
    ) -> RAGContextResult:
        pooled: list[KnowledgeEntry] = []
        for q in queries:
            if not q or not str(q).strip():
                continue
            for cat in categories:
                keyword_hits = self._search_keyword(str(q), cat)
                vector_hits = self._search_vector(str(q), cat)
                pooled.extend(self._rrf_fuse(keyword_hits, vector_hits))

        fused = self._dedupe(pooled)[: max(RAG_RECALL_TOP_K * 2, RAG_RERANK_TOP_N * 2)]
        if not fused:
            return self._low_confidence_result([], query=composite_query)

        reranked = self._rerank.rerank(composite_query or queries[0], fused, top_n=RAG_RERANK_TOP_N)
        return self._build_result(reranked, header=header)

    def _build_result(self, hits: list[KnowledgeEntry], *, header: str) -> RAGContextResult:
        top_score = hits[0].score if hits else 0.0
        if not hits or top_score < RAG_RERANK_THRESHOLD:
            return self._low_confidence_result(hits, top_score=top_score)

        lines = [
            header,
            "以下片段已通过混合检索与重排序验证，分析时请引用编号 [1][2]…：",
            "",
        ]
        for i, h in enumerate(hits, start=1):
            lines.append(f"[{i}] [{h.category}/{h.keyword}] {h.content} （相关度 {h.score:.2f}）")
        return RAGContextResult(
            context="\n".join(lines),
            low_confidence=False,
            top_score=top_score,
            hits=hits,
        )

    def _low_confidence_result(
        self,
        hits: list[KnowledgeEntry],
        *,
        query: str = "",
        top_score: float = 0.0,
    ) -> RAGContextResult:
        score = top_score or (hits[0].score if hits else 0.0)
        context = (
            "## 知识库检索说明\n"
            f"⚠️ 知识库未命中可靠依据（最高相关度 {score:.2f} < 阈值 {RAG_RERANK_THRESHOLD}）。\n"
            "请勿编造具体院校名、分数线、专业细节或薪资数据；仅提供通用策略，"
            "并建议用户查阅省考试院、阳光高考等官方渠道。"
        )
        if query:
            context += f"\n\n检索查询：{query}"
        return RAGContextResult(
            context=context,
            low_confidence=True,
            top_score=score,
            hits=hits,
        )

    def _search_keyword(self, question: str, category: str | None) -> list[KnowledgeEntry]:
        entries = self._loader.get_entries()
        if category:
            entries = [e for e in entries if e.category == category]
        matched = [e.with_score(1.0, "keyword") for e in entries if self._matches(question, e.keyword)]
        return matched[:RAG_RECALL_TOP_K]

    def _search_vector(self, question: str, category: str | None) -> list[KnowledgeEntry]:
        if not self._vector_store.available:
            return []
        raw = self._vector_store.similarity_search(question.strip(), category=category, k=RAG_RECALL_TOP_K)
        hits: list[KnowledgeEntry] = []
        for entry, distance in raw:
            # 距离越小越相似，转为 0~1 参考分供 RRF 使用
            sim = 1.0 / (1.0 + distance)
            hits.append(entry.with_score(sim, "vector"))
        return hits

    def _rrf_fuse(self, *lists: list[KnowledgeEntry]) -> list[KnowledgeEntry]:
        """Reciprocal Rank Fusion 融合多路召回。"""
        scores: dict[str, float] = {}
        entry_map: dict[str, KnowledgeEntry] = {}
        for lst in lists:
            for rank, entry in enumerate(lst, start=1):
                key = entry.dedupe_key()
                entry_map[key] = entry
                scores[key] = scores.get(key, 0.0) + 1.0 / (RAG_RRF_K + rank)
        ordered = sorted(scores.keys(), key=lambda k: scores[k], reverse=True)
        return [entry_map[k].with_score(scores[k], "rrf") for k in ordered]

    def _matches(self, question: str, keyword: str) -> bool:
        q = question.lower()
        for part in re.split(r"[\s,，、/]+", keyword.lower()):
            if len(part) >= 2 and part in q:
                return True
        return keyword.lower() in q

    def _dedupe(self, hits: list[KnowledgeEntry]) -> list[KnowledgeEntry]:
        seen: set[str] = set()
        result: list[KnowledgeEntry] = []
        for h in hits:
            key = h.dedupe_key()
            if key not in seen:
                seen.add(key)
                result.append(h)
        return result
