"""从协调员输出中解析结构化 JSON。"""

import json
import re
from typing import Any


def extract_json_block(text: str) -> dict[str, Any]:
    """从 Markdown 中提取 ```json ... ``` 或末尾 JSON 对象（兼容旧报告）。"""
    fence = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1))
        except json.JSONDecodeError:
            return {}
    brace = re.search(r"\{[\s\S]*\}\s*$", text.strip())
    if brace:
        try:
            return json.loads(brace.group(0))
        except json.JSONDecodeError:
            return {}
    return {}


def append_structured_summary(full_report: str, structured: dict[str, Any]) -> str:
    """在 Markdown 报告末尾附加 JSON 摘要，便于历史报告与前端兼容。"""
    payload = {k: v for k, v in structured.items() if k != "full_report"}
    json_block = json.dumps(payload, ensure_ascii=False, indent=2)
    return f"{full_report.rstrip()}\n\n## 结构化摘要\n\n```json\n{json_block}\n```"


def build_prior_context(sections: list[tuple[str, str]]) -> str:
    """把多段专家输出拼成 Markdown，作为下一节点的 prior_context。"""
    lines: list[str] = []
    for title, body in sections:
        if body.strip():
            lines.append(f"### {title}\n{body.strip()}")
    return "\n\n".join(lines)
