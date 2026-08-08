"""Лёгкая обёртка Langfuse: no-op, если выключено или пакет недоступен."""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Any, Iterator

from app.core.config import get_settings

logger = logging.getLogger(__name__)


@contextmanager
def trace_generation(*, name: str, model: str, user_id: str, input_text: str) -> Iterator[dict[str, Any]]:
    settings = get_settings()
    ctx: dict[str, Any] = {
        "name": name,
        "model": model,
        "user_id": user_id,
        "input": input_text,
        "started": time.perf_counter(),
    }
    client = None
    if settings.langfuse_enabled and settings.langfuse_public_key:
        try:
            from langfuse import Langfuse  # type: ignore

            client = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            ctx["trace"] = client.trace(name=name, user_id=user_id, input=input_text)
        except Exception as exc:  # noqa: BLE001
            logger.debug("langfuse init skipped: %s", exc)

    try:
        yield ctx
    finally:
        elapsed_ms = int((time.perf_counter() - ctx["started"]) * 1000)
        ctx["latency_ms"] = elapsed_ms
        trace = ctx.get("trace")
        if trace is not None:
            try:
                trace.generation(
                    name=name,
                    model=model,
                    input=input_text,
                    output=ctx.get("output", ""),
                    metadata={"latency_ms": elapsed_ms},
                )
                if client is not None:
                    client.flush()
            except Exception as exc:  # noqa: BLE001
                logger.debug("langfuse flush skipped: %s", exc)
