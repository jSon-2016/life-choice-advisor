"""Tool Calling 与 Structured Output 执行器。"""

import json
import time
from typing import Any, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from pydantic import BaseModel, ValidationError

from app.agents.cancel import check_cancelled
from app.llm import create_llm
from app.observability.progress import emit_progress, get_llm_callbacks
from app.observability.tracing import log_agent_done, log_agent_start

SchemaT = TypeVar("SchemaT", bound=BaseModel)

TOOL_SYSTEM_SUFFIX = """

## 工具使用规则（必须遵守）
1. 涉及具体院校、专业、行业、分数段时，**必须先调用可用工具**查询知识库。
2. 工具返回「暂无匹配」时，**不得编造**具体校名、专业名、薪资或公司；仅可给出通用策略并标注「知识库未命中」。
3. 分析中引用的院校/专业/行业事实，须与工具返回一致。
4. 完成必要查询后，输出完整 Markdown 分析报告。"""


def run_agent_with_tools(
    *,
    role: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    prior_context: str = "",
    tools: list[BaseTool],
    temperature: float = 0.3,
    max_tool_rounds: int = 3,
) -> str:
    """带 Tool Calling 的专家 Agent：ReAct 循环，最多 max_tool_rounds 轮工具调用。"""
    check_cancelled()
    emit_progress(step="agent", agent=role, status="started")
    log_agent_start(role)
    start = time.perf_counter()
    config = {"callbacks": get_llm_callbacks()} if get_llm_callbacks() else None
    tool_map = {t.name: t for t in tools}
    llm = create_llm(temperature=temperature).bind_tools(tools)

    context_block = f"\n\n## 前序/参考信息\n{prior_context}" if prior_context.strip() else ""
    user_text = (
        f"请完成你的专业分析。\n\n"
        f"## 用户原始信息\n```json\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}\n```"
        f"{context_block}"
    )
    messages: list = [
        SystemMessage(content=f"你是【{role}】。\n\n{system_prompt}{TOOL_SYSTEM_SUFFIX}"),
        HumanMessage(content=user_text),
    ]

    for _ in range(max_tool_rounds):
        check_cancelled()
        response = llm.invoke(messages, config=config)
        tool_calls = getattr(response, "tool_calls", None) or []
        if not tool_calls:
            content = response.content
            result = content if isinstance(content, str) else str(content)
            elapsed = int((time.perf_counter() - start) * 1000)
            emit_progress(step="agent", agent=role, status="done", elapsed_ms=elapsed)
            log_agent_done(role, elapsed_ms=elapsed)
            return result

        messages.append(response)
        for call in tool_calls:
            check_cancelled()
            name = call["name"]
            tool = tool_map.get(name)
            if tool is None:
                result = f"未知工具: {name}"
            else:
                result = tool.invoke(call.get("args") or {})
            messages.append(
                ToolMessage(
                    content=result if isinstance(result, str) else str(result),
                    tool_call_id=call["id"],
                )
            )

    check_cancelled()
    finalize = create_llm(temperature=temperature).invoke(
        messages + [HumanMessage(content="请基于已查询到的工具结果，输出最终 Markdown 分析报告。")],
        config=config,
    )
    content = finalize.content
    result = content if isinstance(content, str) else str(content)
    elapsed = int((time.perf_counter() - start) * 1000)
    emit_progress(step="agent", agent=role, status="done", elapsed_ms=elapsed)
    log_agent_done(role, elapsed_ms=elapsed)
    return result


def run_structured_coordinator(
    *,
    role: str,
    system_prompt: str,
    user_payload: dict[str, Any],
    prior_context: str,
    schema: type[SchemaT],
    temperature: float = 0.1,
    max_retries: int = 2,
) -> SchemaT:
    """协调员 Structured Output：Pydantic 强类型 + 失败自动 repair。"""
    check_cancelled()
    emit_progress(step="coordinator", agent=role, status="started")
    log_agent_start(role, step="coordinator")
    start = time.perf_counter()
    config = {"callbacks": get_llm_callbacks()} if get_llm_callbacks() else None
    context_block = f"\n\n## 专家分析与知识库\n{prior_context}" if prior_context.strip() else ""
    base_user = (
        f"请综合以下信息输出结构化决策结果。\n\n"
        f"## 用户原始信息\n```json\n{json.dumps(user_payload, ensure_ascii=False, indent=2)}\n```"
        f"{context_block}"
    )
    messages: list = [
        SystemMessage(content=f"你是【{role}】。\n\n{system_prompt}"),
        HumanMessage(content=base_user),
    ]

    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        check_cancelled()
        try:
            llm = create_llm(temperature=temperature).with_structured_output(schema)
            result = llm.invoke(messages, config=config)
            if isinstance(result, schema):
                parsed = result
            else:
                parsed = schema.model_validate(result)
            elapsed = int((time.perf_counter() - start) * 1000)
            emit_progress(step="coordinator", agent=role, status="done", elapsed_ms=elapsed)
            log_agent_done(role, elapsed_ms=elapsed, step="coordinator")
            return parsed
        except (ValidationError, ValueError, TypeError) as exc:
            last_error = exc
            if attempt < max_retries:
                messages.append(
                    HumanMessage(
                        content=(
                            f"上次输出不符合 schema（{exc}）。"
                            "请严格填充所有必填字段；院校/专业/行业不得编造，知识库未命中处用通用表述。"
                        )
                    )
                )
    raise RuntimeError(f"Structured Output 失败（已重试 {max_retries} 次）: {last_error}") from last_error
