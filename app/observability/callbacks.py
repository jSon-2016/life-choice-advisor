"""LangChain LLM Token 用量回调。"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.outputs import LLMResult

logger = logging.getLogger("lca.advisory")


class TokenUsageCallback(BaseCallbackHandler):
    """记录每次 LLM 调用的 token 用量。"""

    def __init__(self, request_id: str) -> None:
        self._request_id = request_id

    def on_llm_end(self, response: LLMResult, **kwargs: Any) -> None:
        usage: dict[str, Any] = {}
        if response.llm_output:
            usage = response.llm_output.get("token_usage") or {}
        logger.info(
            "llm_tokens prompt=%s completion=%s total=%s",
            usage.get("prompt_tokens", "-"),
            usage.get("completion_tokens", "-"),
            usage.get("total_tokens", "-"),
            extra={
                "request_id": self._request_id,
                "agent": kwargs.get("tags", ["llm"])[0] if kwargs.get("tags") else "llm",
                "step": "llm",
                "elapsed_ms": "-",
            },
        )

    @property
    def ignore_chain(self) -> bool:
        return True

    @property
    def ignore_agent(self) -> bool:
        return True
