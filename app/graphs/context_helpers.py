"""合并 RAG / 导入报告等上下文。"""


def merge_context(*parts: str) -> str:
    return "\n\n".join(p.strip() for p in parts if p and p.strip())


def imported_prefix(state: dict) -> str:
    return str(state.get("imported_report_context") or "").strip()
