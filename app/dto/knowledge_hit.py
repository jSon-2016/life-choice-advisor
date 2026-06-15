"""知识库条目。"""

import hashlib
from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeEntry:
    keyword: str
    content: str
    category: str
    score: float = 0.0
    source_id: str = ""
    retrieval_source: str = ""  # keyword | vector | rrf | rerank

    def __post_init__(self) -> None:
        if not self.source_id:
            object.__setattr__(
                self,
                "source_id",
                hashlib.md5(f"{self.category}:{self.keyword}:{self.content[:64]}".encode()).hexdigest()[:10],
            )

    def dedupe_key(self) -> str:
        return f"{self.category}:{self.keyword}:{self.content[:40]}"

    def with_score(self, score: float, retrieval_source: str | None = None) -> "KnowledgeEntry":
        return KnowledgeEntry(
            keyword=self.keyword,
            content=self.content,
            category=self.category,
            score=score,
            source_id=self.source_id,
            retrieval_source=retrieval_source or self.retrieval_source,
        )
