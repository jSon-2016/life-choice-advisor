"""结构化日志与 request_id。"""

from __future__ import annotations

import logging
import uuid

from app.observability.progress import get_request_id

logger = logging.getLogger("lca.advisory")


class _AdvisoryLogFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for key in ("request_id", "agent", "elapsed_ms", "step"):
            if not hasattr(record, key):
                setattr(record, key, "-")
        return True


def setup_logging(level: int = logging.INFO) -> None:
    root = logging.getLogger()
    if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        return
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s [%(name)s] rid=%(request_id)s step=%(step)s "
            "agent=%(agent)s elapsed_ms=%(elapsed_ms)s %(message)s"
        )
    )
    handler.addFilter(_AdvisoryLogFilter())
    root.addHandler(handler)
    root.setLevel(level)
    logger.setLevel(level)


def new_request_id() -> str:
    return uuid.uuid4().hex[:12]


def log_agent_start(role: str, *, step: str = "agent") -> None:
    logger.info(
        "agent_started",
        extra={"request_id": get_request_id(), "agent": role, "step": step, "elapsed_ms": "-"},
    )


def log_agent_done(role: str, *, elapsed_ms: int, step: str = "agent") -> None:
    logger.info(
        "agent_done",
        extra={
            "request_id": get_request_id(),
            "agent": role,
            "step": step,
            "elapsed_ms": elapsed_ms,
        },
    )


def log_rag_done(*, hits: int, low_confidence: bool, elapsed_ms: int) -> None:
    logger.info(
        "rag_done hits=%s low_confidence=%s",
        hits,
        low_confidence,
        extra={
            "request_id": get_request_id(),
            "agent": "rag",
            "step": "rag",
            "elapsed_ms": elapsed_ms,
        },
    )


def log_advisory_done(*, advisory_type: str, elapsed_ms: int) -> None:
    logger.info(
        "advisory_done type=%s",
        advisory_type,
        extra={
            "request_id": get_request_id(),
            "agent": "-",
            "step": advisory_type,
            "elapsed_ms": elapsed_ms,
        },
    )
