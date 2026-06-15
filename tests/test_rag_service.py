"""RAG 流水线单元测试（无需 DashScope API Key）。"""

from app.dto.knowledge_hit import KnowledgeEntry
from app.service.knowledge_base_loader import KnowledgeBaseLoader
from app.service.rag_service import RAGService


def _make_rag() -> RAGService:
    return RAGService(KnowledgeBaseLoader())


def test_rrf_fuse_merges_keyword_and_vector():
    rag = _make_rag()
    a = KnowledgeEntry("浙大", "浙江大学985", "schools", retrieval_source="keyword")
    b = KnowledgeEntry("计算机", "计算机专业", "majors", retrieval_source="keyword")
    fused = rag._rrf_fuse([a], [b])
    assert len(fused) == 2
    assert fused[0].retrieval_source == "rrf"


def test_search_keyword_finds_guangdong():
    rag = _make_rag()
    hits = rag._search_keyword("广东 华南", "schools")
    assert any("华南" in h.keyword or "广东" in h.keyword for h in hits)


def test_low_confidence_when_no_hits():
    rag = _make_rag()
    result = rag.search_with_meta("完全不存在的火星院校xyz123", category="schools")
    assert result.low_confidence is True
    assert "未命中" in result.context


def test_citation_format_when_confident(monkeypatch):
    rag = _make_rag()

    def fake_rerank(query, hits, top_n=None):
        return [h.with_score(0.9, "rerank") for h in hits[: (top_n or 5)]]

    monkeypatch.setattr(rag._rerank, "rerank", fake_rerank)
    result = rag.search_with_meta("计算机 编程", category="majors")
    if not result.low_confidence:
        assert "[1]" in result.context
        assert "相关度" in result.context


def test_dedupe():
    rag = _make_rag()
    e = KnowledgeEntry("a", "content", "majors")
    deduped = rag._dedupe([e, e])
    assert len(deduped) == 1
