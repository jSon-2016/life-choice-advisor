"""LangGraph 节点进度包装。"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from app.observability.progress import emit_progress

StateT = TypeVar("StateT")
NodeFn = Callable[[StateT], dict]


def with_node_progress(step: str, fn: NodeFn[StateT]) -> NodeFn[StateT]:
    """节点开始/结束推送 SSE 进度。"""

    def wrapper(state: StateT) -> dict:
        emit_progress(step=step, status="started")
        start = time.perf_counter()
        try:
            return fn(state)
        finally:
            elapsed = int((time.perf_counter() - start) * 1000)
            emit_progress(step=step, status="done", elapsed_ms=elapsed)

    return wrapper
