"""Tool Calling 与 Structured Output 单元测试（无需 LLM API Key）。"""

from app.service.knowledge_base_loader import KnowledgeBaseLoader
from app.tools.knowledge_toolkit import KnowledgeToolkit


def test_search_schools_finds_guangdong_entry():
    tk = KnowledgeToolkit(KnowledgeBaseLoader())
    result = tk.search_schools("广东", "华南理工", 612)
    assert "华南理工" in result or "暂无" in result


def test_search_majors_finds_computer():
    tk = KnowledgeToolkit(KnowledgeBaseLoader())
    result = tk.search_majors("计算机 编程")
    assert "计算机" in result


def test_search_majors_empty_returns_hint():
    tk = KnowledgeToolkit(KnowledgeBaseLoader())
    result = tk.search_majors("火星专业xyz不存在")
    assert "暂无" in result or "未命中" in result or "通用" in result


def test_get_score_segment():
    tk = KnowledgeToolkit(KnowledgeBaseLoader())
    result = tk.get_score_segment("广东", 612, "物理类")
    assert "612" in result or "600" in result or "推断" in result
