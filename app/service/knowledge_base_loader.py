"""多文件知识库加载（keyword|content，# 开头为注释）。"""

from pathlib import Path

from app.config import KNOWLEDGE_DIR
from app.dto.knowledge_hit import KnowledgeEntry


class KnowledgeBaseLoader:
    def __init__(self, directory: str | None = None) -> None:
        root = Path(__file__).resolve().parents[2]
        self._dir = root / (directory or KNOWLEDGE_DIR)
        self._entries: list[KnowledgeEntry] = []
        self.reload()

    def get_entries(self) -> list[KnowledgeEntry]:
        return list(self._entries)

    def get_by_category(self, category: str) -> list[KnowledgeEntry]:
        return [e for e in self._entries if e.category == category]

    def reload(self) -> None:
        self._entries = []
        if not self._dir.exists():
            return
        for file_path in sorted(self._dir.glob("*.txt")):
            category = file_path.stem
            for raw in file_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if "|" not in line:
                    continue
                keyword, content = line.split("|", 1)
                keyword, content = keyword.strip(), content.strip()
                if keyword and content:
                    self._entries.append(KnowledgeEntry(keyword, content, category))
