"""知识库查询工具包：供 Tool Calling 读取事实，减少幻觉。"""

import re

from app.dto.knowledge_hit import KnowledgeEntry
from app.service.knowledge_base_loader import KnowledgeBaseLoader


class KnowledgeToolkit:
    """基于 data/knowledge/*.txt 的结构化查询，不依赖 LLM 编造。"""

    def __init__(self, loader: KnowledgeBaseLoader) -> None:
        self._loader = loader

    def search_entries(
        self,
        query: str,
        *,
        category: str | None = None,
        limit: int = 5,
    ) -> list[KnowledgeEntry]:
        if not query or not query.strip():
            return []
        entries = self._loader.get_entries()
        if category:
            entries = [e for e in entries if e.category == category]
        matched = [e for e in entries if self._matches(query, e.keyword) or self._matches(query, e.content)]
        if not matched:
            q = query.lower()
            matched = [
                e for e in entries
                if any(part in e.content.lower() or part in e.keyword.lower()
                       for part in re.split(r"[\s,，、/]+", q) if len(part) >= 2)
            ]
        return self._dedupe(matched)[:limit]

    def search_schools(self, province: str, keywords: str = "", score: int | None = None) -> str:
        """按省份、关键词、分数检索院校知识库条目。"""
        parts = [province, keywords]
        if score is not None:
            parts.append(str(score))
        query = " ".join(p for p in parts if p.strip())
        hits = self.search_entries(query, category="schools", limit=8)
        if score is not None:
            hits = self._dedupe(hits + self.search_entries(f"{score} {province}", category="schools", limit=5))
        return self._format_hits(hits, empty_hint="知识库暂无匹配院校，请勿编造校名，仅给出通用填报策略。")

    def search_majors(self, keywords: str) -> str:
        """按关键词检索专业就业与选科信息。"""
        hits = self.search_entries(keywords, category="majors", limit=8)
        return self._format_hits(hits, empty_hint="知识库暂无匹配专业，请勿编造专业细节，仅给出通用选专业原则。")

    def get_score_segment(self, province: str, score: int, subject_track: str) -> str:
        """检索分数段定位参考（省份+分数+科类）。"""
        queries = [
            f"{province} {score} {subject_track}",
            f"{score} {province}",
            str(score),
            province,
        ]
        hits: list[KnowledgeEntry] = []
        for q in queries:
            hits.extend(self.search_entries(q, category="schools", limit=3))
        hits = self._dedupe(hits)[:6]
        header = f"## 分数段参考（{province} / {subject_track} / {score}分）"
        body = self._format_hits(hits, empty_hint="知识库无该分数段精确数据，请基于前序分析做区间推断并明确标注为推断。")
        return f"{header}\n{body}"

    def search_industries(self, keywords: str, major: str = "") -> str:
        """检索行业趋势与就业信息。"""
        query = " ".join(p for p in [major, keywords] if p.strip())
        hits = self.search_entries(query, category="industries", limit=8)
        return self._format_hits(hits, empty_hint="知识库暂无匹配行业，请勿编造薪资或头部公司，仅给出通用分析框架。")

    def search_career_roles(self, major: str, skills: str = "", keywords: str = "") -> str:
        """检索与专业/技能相关的岗位与行业信息。"""
        query = " ".join(p for p in [major, skills, keywords] if p.strip())
        industry_hits = self.search_entries(query, category="industries", limit=5)
        major_hits = self.search_entries(query, category="majors", limit=5)
        hits = self._dedupe(industry_hits + major_hits)[:8]
        return self._format_hits(hits, empty_hint="知识库暂无匹配岗位信息，请勿编造具体公司与薪资，仅给出通用岗位类型建议。")

    def _format_hits(self, hits: list[KnowledgeEntry], *, empty_hint: str) -> str:
        if not hits:
            return empty_hint
        lines = [f"- [{h.category}/{h.keyword}] {h.content}" for h in hits]
        return "\n".join(lines)

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
            key = f"{h.category}:{h.keyword}:{h.content[:40]}"
            if key not in seen:
                seen.add(key)
                result.append(h)
        return result
