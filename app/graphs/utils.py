"""从协调员输出中解析结构化 JSON。"""

import json
import re
from typing import Any


def extract_json_block(text: str) -> dict[str, Any]:
    """从 Markdown 中提取 ```json ... ``` 或末尾 JSON 对象。"""
    fence = re.search(r"```json\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
    if fence:
        return json.loads(fence.group(1))
    brace = re.search(r"\{[\s\S]*\}\s*$", text.strip())
    if brace:
        return json.loads(brace.group(0))
    return {}


def build_prior_context(sections: list[tuple[str, str]]) -> str:
    """把多段专家输出拼成 Markdown，作为下一节点的 prior_context。"""
    lines: list[str] = []
    for title, body in sections:
        if body.strip():
            lines.append(f"### {title}\n{body.strip()}")
    return "\n\n".join(lines)
