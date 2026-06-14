"""Multi-Agent 通用执行器。"""

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.cancel import check_cancelled
from app.llm import create_llm
"""
run_agent方法参数列表中*表示调用该方法传参时不能按照位置传参必须要给出参数名如：            role="职业能力测评师",
            system_prompt=APTITUDE_ANALYST_PROMPT,
            user_payload=profile,
            prior_context=rag,；不能是： "职业能力测评师",
            APTITUDE_ANALYST_PROMPT,
            profile,
            rag,
"""

def run_agent(
    *,
    role: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    prior_context: str = "",
    temperature: float = 0.3,
) -> str:
    """调用单个专家 Agent，返回 Markdown 分析结果。

    消息结构：SystemMessage(角色+Prompt) + HumanMessage(用户JSON+前序上下文)
    """
    check_cancelled()
    llm = create_llm(temperature=temperature)
    # 前序专家输出 / RAG 知识，拼进 HumanMessage
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
    """并行执行多个 Agent，返回 {state字段名: LLM输出}。

    tasks 示例：[("score_analysis", score_task), ...]
    用 ThreadPoolExecutor 同时调多个 LLM，缩短等待时间。
    """
    check_cancelled()
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_map = {executor.submit(fn): key for key, fn in tasks}
        for future in as_completed(future_map):
            check_cancelled()
            key = future_map[future]
            results[key] = future.result()
    return results
