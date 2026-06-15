"""测评报告语义分块单测。"""

from app.service.report_chunker import format_chunks_markdown, semantic_chunk_with_overlap


SAMPLE_REPORT = """
霍兰德职业兴趣测评报告

维度    得分    参考标准
现实型(R)    45    常模 40-55
研究型(I)    78    常模 50-70，高于平均
艺术型(A)    62    常模 45-60

综合解读：研究型与艺术型得分较高，适合需要分析与创造力的岗位。

MBTI：INTJ
"""


def test_semantic_chunk_not_empty():
    chunks = semantic_chunk_with_overlap(SAMPLE_REPORT, chunk_size=200, overlap=80)
    assert len(chunks) >= 1


def test_overlap_preserves_context():
    chunks = semantic_chunk_with_overlap(SAMPLE_REPORT, chunk_size=180, overlap=100)
    if len(chunks) >= 2:
        assert "研究型" in chunks[1].content or "维度" in chunks[1].content


def test_table_block_kept_together_when_small():
    chunks = semantic_chunk_with_overlap(SAMPLE_REPORT, chunk_size=800, overlap=50)
    table_chunk = next((c for c in chunks if "参考标准" in c.content), None)
    assert table_chunk is not None


def test_format_markdown_has_fragment_ids():
    chunks = semantic_chunk_with_overlap(SAMPLE_REPORT)
    md = format_chunks_markdown(chunks)
    assert "[片段1]" in md
    assert "导入测评报告" in md
