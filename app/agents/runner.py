"""Multi-Agent 通用执行器。"""

import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable

from langchain_core.messages import HumanMessage, SystemMessage

from app.agents.cancel import check_cancelled
from app.llm import create_llm
from app.observability.progress import emit_progress, get_llm_callbacks
from app.observability.tracing import log_agent_done, log_agent_start


def run_agent(
    *,
    role: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    prior_context: str = "",
    temperature: float = 0.3,
) -> str:
    """调用单个专家 Agent，返回 Markdown 分析结果。"""
    check_cancelled()
    emit_progress(step="agent", agent=role, status="started")
    log_agent_start(role)
    start = time.perf_counter()

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
    config = {"callbacks": get_llm_callbacks()} if get_llm_callbacks() else None
    response = llm.invoke(messages, config=config)
    content = response.content
    result = content if isinstance(content, str) else str(content)

    elapsed = int((time.perf_counter() - start) * 1000)
    emit_progress(step="agent", agent=role, status="done", elapsed_ms=elapsed)
    log_agent_done(role, elapsed_ms=elapsed)
    return result


def run_agents_parallel(tasks: list[tuple[str, Callable[[], str]]]) -> dict[str, str]:
    """并行执行多个 Agent，返回 {state字段名: LLM输出}。"""
    check_cancelled()
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
        future_map = {executor.submit(fn): key for key, fn in tasks}
        for future in as_completed(future_map):
            check_cancelled()
            key = future_map[future]
            results[key] = future.result()
    return results
