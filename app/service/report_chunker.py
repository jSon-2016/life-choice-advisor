"""测评报告语义分块：结构感知 + 重叠切分，避免固定字数硬切。"""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.config import REPORT_CHUNK_OVERLAP, REPORT_CHUNK_SIZE

TABLE_HINT = re.compile(
    r"(得分|参考标准|常模|维度|标准分|T分|百分位|测评|量表|因子|指标)",
    re.IGNORECASE,
)
SENTENCE_END = re.compile(r"(?<=[。！？；\n])")


@dataclass(frozen=True)
class ReportChunk:
    index: int
    content: str
    section_hint: str


def semantic_chunk_with_overlap(
    text: str,
    *,
    chunk_size: int | None = None,
    overlap: int | None = None,
) -> list[ReportChunk]:
    """按段落/表格结构分块，块间保留 overlap 字符以维持语义连贯。"""
    size = chunk_size or REPORT_CHUNK_SIZE
    ovlp = overlap or REPORT_CHUNK_OVERLAP
    normalized = _normalize(text)
    if not normalized:
        return []

    blocks = _split_structural_blocks(normalized)
    merged = _merge_blocks_into_chunks(blocks, max_size=size)
    overlapped = _apply_overlap(merged, overlap=ovlp)
    return [
        ReportChunk(index=i + 1, content=chunk, section_hint=_hint(chunk))
        for i, chunk in enumerate(overlapped)
        if chunk.strip()
    ]


def format_chunks_markdown(chunks: list[ReportChunk]) -> str:
    """格式化为 Agent 可读的带编号上下文。"""
    if not chunks:
        return ""
    lines = [
        "## 导入测评报告（语义分块，含重叠上下文）",
        "以下片段来自用户上传的 PDF/图片测评报告，请优先引用其中的得分、维度与参考标准，不得编造未出现的数值。",
        "",
    ]
    for c in chunks:
        lines.append(f"### [片段{c.index}] ({c.section_hint})")
        lines.append(c.content.strip())
        lines.append("")
    return "\n".join(lines).strip()


def _normalize(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _split_structural_blocks(text: str) -> list[str]:
    """先按空行分段，再将连续表格行合并为一块。"""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    blocks: list[str] = []
    table_buf: list[str] = []

    def flush_table() -> None:
        if table_buf:
            blocks.append("\n".join(table_buf))
            table_buf.clear()

    for para in paragraphs:
        lines = para.split("\n")
        if _looks_like_table_block(lines):
            table_buf.extend(lines)
        else:
            flush_table()
            if len(para) > REPORT_CHUNK_SIZE * 1.5:
                blocks.extend(_split_long_paragraph(para))
            else:
                blocks.append(para)
    flush_table()
    return blocks


def _looks_like_table_block(lines: list[str]) -> bool:
    if len(lines) < 2:
        return bool(TABLE_HINT.search(lines[0])) if lines else False
    hits = sum(1 for ln in lines if TABLE_HINT.search(ln) or "|" in ln or "\t" in ln)
    return hits >= max(2, len(lines) // 2)


def _split_long_paragraph(para: str) -> list[str]:
    """超长段落按句子边界切分，避免半句截断。"""
    parts = SENTENCE_END.split(para)
    sentences = [p.strip() for p in parts if p.strip()]
    if not sentences:
        return [para]
    chunks: list[str] = []
    buf = ""
    limit = REPORT_CHUNK_SIZE
    for sent in sentences:
        if len(buf) + len(sent) > limit and buf:
            chunks.append(buf.strip())
            buf = sent
        else:
            buf = f"{buf}{sent}" if buf else sent
    if buf.strip():
        chunks.append(buf.strip())
    return chunks


def _merge_blocks_into_chunks(blocks: list[str], *, max_size: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for block in blocks:
        candidate = f"{current}\n\n{block}".strip() if current else block
        if len(candidate) <= max_size:
            current = candidate
            continue
        if current:
            chunks.append(current)
        if len(block) <= max_size:
            current = block
        else:
            chunks.extend(_split_long_paragraph(block))
            current = ""
    if current:
        chunks.append(current)
    return chunks


def _apply_overlap(chunks: list[str], *, overlap: int) -> list[str]:
    if len(chunks) <= 1 or overlap <= 0:
        return chunks
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        tail = chunks[i - 1][-overlap:]
        merged = f"{tail}\n\n---\n\n{chunks[i]}".strip()
        result.append(merged)
    return result


def _hint(chunk: str) -> str:
    if TABLE_HINT.search(chunk):
        return "表格/维度得分"
    if len(chunk) < 120:
        return "短段落"
    return "叙述段落"
