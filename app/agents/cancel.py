"""分析任务取消：前端断开连接时停止后续 Agent 调用。

通过 ContextVar 把 cancel_event 传入 asyncio.to_thread 工作线程，
各 graph 节点和 run_agent 在关键点调用 check_cancelled()。
"""

import threading
from contextvars import ContextVar

# 线程安全的取消信号，绑定到当前请求上下文
_cancel_event: ContextVar[threading.Event | None] = ContextVar("cancel_event", default=None)


class AnalysisCancelledError(Exception):
    """用户取消或客户端断开连接。"""


def bind_cancel_event(event: threading.Event | None) -> None:
    _cancel_event.set(event)


def clear_cancel_event() -> None:
    _cancel_event.set(None)

"""" None相当于 Java 的 void """
def check_cancelled() -> None:
    event = _cancel_event.get()
    if event is not None and event.is_set():
        raise AnalysisCancelledError("分析已取消")
