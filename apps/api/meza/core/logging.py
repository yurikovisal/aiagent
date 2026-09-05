"""Structured JSON logging.

Every record carries: timestamp, level, service, request_id, user_id, agent, tool,
duration_ms, message. Secrets are scrubbed from the message and extras.
"""

from __future__ import annotations

import contextvars
import json
import logging
import re
import sys
from datetime import UTC, datetime

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
user_id_var: contextvars.ContextVar[int | None] = contextvars.ContextVar("user_id", default=None)

_SECRET_KEYS = re.compile(r"(password|passwd|secret|token|authorization|api[_-]?key|cookie)", re.I)
_SECRET_VALUE = re.compile(r"(?i)(password|token|secret|api_key|authorization)\s*[=:]\s*\S+")

STANDARD_ATTRS = set(logging.LogRecord("x", 0, "x", 0, "", (), None).__dict__.keys()) | {"message", "asctime"}


def scrub(value):
    """Recursively remove secret-looking values from dicts/lists/strings."""
    if isinstance(value, dict):
        return {k: ("***" if _SECRET_KEYS.search(str(k)) else scrub(v)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [scrub(v) for v in value]
    if isinstance(value, str):
        return _SECRET_VALUE.sub(lambda m: f"{m.group(1)}=***", value)
    return value


class JsonFormatter(logging.Formatter):
    def __init__(self, service: str = "meza-api"):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "service": self.service,
            "logger": record.name,
            "request_id": request_id_var.get(),
            "user_id": user_id_var.get(),
            "agent": getattr(record, "agent", None),
            "tool": getattr(record, "tool", None),
            "duration_ms": getattr(record, "duration_ms", None),
            "message": scrub(record.getMessage()),
        }
        for key, val in record.__dict__.items():
            if key not in STANDARD_ATTRS and key not in payload:
                payload[key] = scrub(val)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


def configure_logging(level: str = "INFO", service: str = "meza-api") -> None:
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter(service))
    root.addHandler(handler)
    root.setLevel(level)
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
