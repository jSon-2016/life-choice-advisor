"""DashScope 文本 Rerank，失败时降级为 RRF 分数。"""

import logging
import os
from http import HTTPStatus

from app.config import RAG_RERANK_MODEL, RAG_RERANK_TOP_N
from app.dto.knowledge_hit import KnowledgeEntry

logger = logging.getLogger(__name__)


class RerankService:
    """对召回结果做语义重排序。"""

    def __init__(self) -> None:
        self._available = bool(os.getenv("DASHSCOPE_API_KEY"))

    def rerank(
        self,
        query: str,
        hits: list[KnowledgeEntry],
        *,
        top_n: int | None = None,
    ) -> list[KnowledgeEntry]:
        if not hits:
            return []
        limit = top_n or RAG_RERANK_TOP_N
        if not self._available:
            return self._fallback_rank(hits, limit)

        try:
            import dashscope

            documents = [f"[{h.category}/{h.keyword}] {h.content}" for h in hits]
            resp = dashscope.TextReRank.call(
                model=RAG_RERANK_MODEL,
                query=query.strip(),
                documents=documents,
                top_n=min(limit, len(documents)),
                return_documents=False,
            )
            if resp.status_code != HTTPStatus.OK:
                logger.warning("Rerank API 失败: %s，降级为 RRF 分数", resp.message)
                return self._fallback_rank(hits, limit)

            ranked: list[KnowledgeEntry] = []
            for item in resp.output.results:
                idx = item.index
                if 0 <= idx < len(hits):
                    ranked.append(hits[idx].with_score(float(item.relevance_score), "rerank"))
            return ranked[:limit]
        except Exception as exc:
            logger.warning("Rerank 异常，降级为 RRF 分数: %s", exc)
            return self._fallback_rank(hits, limit)

    @staticmethod
    def _fallback_rank(hits: list[KnowledgeEntry], top_n: int) -> list[KnowledgeEntry]:
        """无 Rerank API 时，按 RRF 分数归一化排序。"""
        max_score = max((h.score for h in hits), default=0.0)
        if max_score <= 0:
            return [h.with_score(0.5, h.retrieval_source or "rrf") for h in hits[:top_n]]
        normalized = [h.with_score(h.score / max_score, h.retrieval_source or "rrf") for h in hits]
        normalized.sort(key=lambda x: x.score, reverse=True)
        return normalized[:top_n]
