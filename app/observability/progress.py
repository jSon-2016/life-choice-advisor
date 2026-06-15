"""SSE / 日志共用的进度事件（ContextVar）。"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

ProgressEmitter = Callable[["ProgressEvent"], None]

_request_id: ContextVar[str] = ContextVar("request_id", default="")
_progress_emitter: ContextVar[ProgressEmitter | None] = ContextVar("progress_emitter", default=None)
_llm_callbacks: ContextVar[list[Any]] = ContextVar("llm_callbacks", default=[])


@dataclass
class ProgressEvent:
    event: str = "progress"
    step: str = ""
    agent: str = ""
    status: str = ""  # started | done | rag
    elapsed_ms: int = 0
    request_id: str = ""
    message: str = ""


def get_request_id() -> str:
    return _request_id.get()


def get_llm_callbacks() -> list[Any]:
    return list(_llm_callbacks.get())


def bind_observability(
    request_id: str,
    emitter: ProgressEmitter | None,
    callbacks: list[Any] | None = None,
) -> None:
    _request_id.set(request_id)
    _progress_emitter.set(emitter)
    _llm_callbacks.set(callbacks or [])


def clear_observability() -> None:
    _request_id.set("")
    _progress_emitter.set(None)
    _llm_callbacks.set([])


def emit_progress(
    *,
    step: str = "",
    agent: str = "",
    status: str = "",
    elapsed_ms: int = 0,
    message: str = "",
) -> None:
    emitter = _progress_emitter.get()
    event = ProgressEvent(
        step=step,
        agent=agent,
        status=status,
        elapsed_ms=elapsed_ms,
        request_id=get_request_id(),
        message=message,
    )
    if emitter is not None:
        emitter(event)


def event_to_dict(event: ProgressEvent) -> dict[str, Any]:
    return asdict(event)
