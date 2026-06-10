"""Multi-Agent 通用执行器。"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage

from app.llm import create_llm


def run_agent(
    *,
    role: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    prior_context: str = "",
    temperature: float = 0.3,
) -> str:
    """调用单个专家 Agent，返回 Markdown 分析结果。"""
    llm = create_llm(temperature=temperature)
    context_block = f"\n\n## 前序/参考信息\n{prior_context}" if prior_context.strip() else ""
    user_text = (
        f"请完成你的专业分析。\n\n"
        f"## 用户原始信息\n```json\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}\n```"
        f"{context_block}"
    )
    messages = [
        SystemMessage(content=f"你是【{role}】。\n\n{system_prompt}"),
        HumanMessage(content=user_text),
    ]
    response = llm.invoke(messages)
    content = response.content
    return content if isinstance(content, str) else str(content)


def run_agents_parallel(tasks: list[tuple[str, Callable[[], str]]]) -> dict[str, str]:
    """并行执行多个 Agent，返回 {agent_key: content}。"""
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_map = {executor.submit(fn): key for key, fn in tasks}
        for future in as_completed(future_map):
            key = future_map[future]
            results[key] = future.result()
    return results
