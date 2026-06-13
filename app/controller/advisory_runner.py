"""带客户端断开检测的咨询任务执行。"""

import asyncio
import threading
from collections.abc import Callable
from typing import TypeVar

from fastapi import HTTPException, Request

from app.agents.cancel import AnalysisCancelledError, bind_cancel_event, clear_cancel_event

T = TypeVar("T")


async def run_advisory_with_cancel(request: Request, fn: Callable[..., T], /, *args, **kwargs) -> T:
    """在线程中运行同步咨询逻辑，客户端断开时触发取消。

    流程：后台 watch_disconnect 轮询 → 设置 cancel_event →
    工作线程中 check_cancelled() 抛 AnalysisCancelledError → 返回 499。
    """
    cancel_event = threading.Event()

    async def watch_disconnect() -> None:
        try:
            while not cancel_event.is_set():
                if await request.is_disconnected():
                    cancel_event.set()
                    return
                await asyncio.sleep(0.3)
        except asyncio.CancelledError:
            return

    bind_cancel_event(cancel_event)
    watcher = asyncio.create_task(watch_disconnect())
    try:
        return await asyncio.to_thread(fn, *args, **kwargs)
    except AnalysisCancelledError as exc:
        raise HTTPException(status_code=499, detail=str(exc)) from exc
    finally:
        cancel_event.set()
        watcher.cancel()
        try:
            await watcher
        except asyncio.CancelledError:
            pass
        clear_cancel_event()
