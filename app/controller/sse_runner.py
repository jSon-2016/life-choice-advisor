"""SSE 流式咨询：进度事件 + 最终结果 + 取消。"""

from __future__ import annotations

import asyncio
import json
import threading
from collections.abc import Callable
from typing import Any, TypeVar

from fastapi import HTTPException, Request
from fastapi.responses import StreamingResponse

from app.agents.cancel import AnalysisCancelledError, bind_cancel_event, clear_cancel_event
from app.observability.callbacks import TokenUsageCallback
from app.observability.progress import ProgressEvent, bind_observability, clear_observability, event_to_dict
from app.observability.tracing import new_request_id

T = TypeVar("T")


def _format_sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def stream_advisory_with_cancel(
    request: Request,
    fn: Callable[..., T],
    /,
    *args: Any,
    **kwargs: Any,
) -> StreamingResponse:
    """在线程中执行同步咨询，经 SSE 推送 progress/result/error。"""
    request_id = new_request_id()
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
    loop = asyncio.get_running_loop()
    cancel_event = threading.Event()

    def emitter(event: ProgressEvent) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, ("progress", event))

    def worker() -> None:
        bind_observability(request_id, emitter, [TokenUsageCallback(request_id)])
        bind_cancel_event(cancel_event)
        try:
            result = fn(*args, **kwargs)
            loop.call_soon_threadsafe(queue.put_nowait, ("result", result))
        except AnalysisCancelledError as exc:
            loop.call_soon_threadsafe(queue.put_nowait, ("cancel", exc))
        except Exception as exc:
            loop.call_soon_threadsafe(queue.put_nowait, ("error", exc))
        finally:
            clear_observability()
            clear_cancel_event()

    async def watch_disconnect() -> None:
        try:
            while not cancel_event.is_set():
                if await request.is_disconnected():
                    cancel_event.set()
                    return
                await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            return

    async def event_generator():
        watcher = asyncio.create_task(watch_disconnect())
        yield _format_sse(
            "progress",
            {"request_id": request_id, "status": "started", "message": "分析任务已启动"},
        )
        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        try:
            while True:
                try:
                    kind, payload = await asyncio.wait_for(queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    if not thread.is_alive() and queue.empty():
                        yield _format_sse("error", {"message": "分析线程意外结束", "code": 500})
                        break
                    continue

                if kind == "progress":
                    yield _format_sse("progress", event_to_dict(payload))
                elif kind == "result":
                    data = payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload
                    yield _format_sse("result", data)
                    break
                elif kind == "cancel":
                    yield _format_sse("error", {"message": str(payload), "code": 499})
                    break
                elif kind == "error":
                    yield _format_sse("error", {"message": str(payload), "code": 500})
                    break
        finally:
            cancel_event.set()
            watcher.cancel()
            try:
                await watcher
            except asyncio.CancelledError:
                pass
            thread.join(timeout=2.0)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
