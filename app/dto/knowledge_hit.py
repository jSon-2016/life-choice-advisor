"""知识库条目。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeEntry:
    keyword: str
    content: str
    category: str
