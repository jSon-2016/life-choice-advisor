"""Tool 注册：绑定知识库并导出各场景工具列表。"""

from langchain_core.tools import StructuredTool

from app.service.knowledge_base_loader import KnowledgeBaseLoader
from app.tools.knowledge_toolkit import KnowledgeToolkit

_toolkit: KnowledgeToolkit | None = None


def init_knowledge_tools(loader: KnowledgeBaseLoader) -> None:
    """应用启动时初始化（见 app/deps.py）。"""
    global _toolkit
    _toolkit = KnowledgeToolkit(loader)


def _get_toolkit() -> KnowledgeToolkit:
    global _toolkit
    if _toolkit is None:
        init_knowledge_tools(KnowledgeBaseLoader())
    return _toolkit


def get_gaokao_tools() -> list[StructuredTool]:
    """高考志愿阶段2专家可用工具。"""
    tk = _get_toolkit()

    def search_schools(province: str, keywords: str = "", score: int = 0) -> str:
        """检索院校层次、地域与分数段参考。province 为高考省份；keywords 可填意向地区或校名；score 为总分（0 表示不限）。"""
        return tk.search_schools(province, keywords, score if score > 0 else None)

    def search_majors(keywords: str) -> str:
        """检索专业就业方向、选科要求与培养特点。keywords 可填兴趣或专业名。"""
        return tk.search_majors(keywords)

    def get_score_segment(province: str, score: int, subject_track: str) -> str:
        """检索省份+科类+总分对应的分数段定位与冲稳保参考。"""
        return tk.get_score_segment(province, score, subject_track)

    return [
        StructuredTool.from_function(search_schools, name="search_schools"),
        StructuredTool.from_function(search_majors, name="search_majors"),
        StructuredTool.from_function(get_score_segment, name="get_score_segment"),
    ]


def get_career_tools() -> list[StructuredTool]:
    """职业选择阶段2专家可用工具。"""
    tk = _get_toolkit()

    def search_industries(keywords: str, major: str = "") -> str:
        """检索行业趋势、就业特点与入门门槛。major 为所学专业，keywords 为技能或意向方向。"""
        return tk.search_industries(keywords, major)

    def search_career_roles(major: str, skills: str = "", keywords: str = "") -> str:
        """检索与专业/技能匹配的岗位类型与成长路径参考。"""
        return tk.search_career_roles(major, skills, keywords)

    def search_majors(keywords: str) -> str:
        """检索专业对应的就业去向与能力要求，辅助岗位匹配。"""
        return tk.search_majors(keywords)

    return [
        StructuredTool.from_function(search_industries, name="search_industries"),
        StructuredTool.from_function(search_career_roles, name="search_career_roles"),
        StructuredTool.from_function(search_majors, name="search_majors"),
    ]
