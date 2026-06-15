"""RAG 检索结果封装。"""

from dataclasses import dataclass, field

from app.dto.knowledge_hit import KnowledgeEntry


@dataclass
class RAGContextResult:
    """混合检索 + Rerank + 拒答判定后的上下文。"""

    context: str
    low_confidence: bool = False
    top_score: float = 0.0
    hits: list[KnowledgeEntry] = field(default_factory=list)
