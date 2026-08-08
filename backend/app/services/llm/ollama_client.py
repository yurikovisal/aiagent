from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


async def stream_chat(
    messages: list[dict[str, str]],
    *,
    model: str | None = None,
) -> AsyncIterator[str]:
    """Стримит токены ответа. При недоступности Ollama — mock-ответ."""
    settings = get_settings()
    model_name = model or settings.llm_model

    if settings.llm_mock:
        async for chunk in _mock_stream(messages):
            yield chunk
        return

    payload: dict[str, Any] = {
        "model": model_name,
        "messages": messages,
        "stream": True,
    }
    url = f"{settings.ollama_base_url.rstrip('/')}/api/chat"

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream("POST", url, json=payload) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    logger.warning("ollama error %s: %s", response.status_code, body[:200])
                    async for chunk in _mock_stream(messages, reason="ollama_error"):
                        yield chunk
                    return
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("done"):
                        break
                    content = data.get("message", {}).get("content")
                    if content:
                        yield content
    except (httpx.HTTPError, json.JSONDecodeError) as exc:
        logger.warning("ollama unavailable, using mock: %s", exc)
        async for chunk in _mock_stream(messages, reason="ollama_unavailable"):
            yield chunk


async def _mock_stream(
    messages: list[dict[str, str]],
    *,
    reason: str = "llm_mock",
) -> AsyncIterator[str]:
    last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
    text = (
        f"[MEZA mock · {reason}] Понял запрос: «{last_user[:240]}». "
        "Подключи Ollama с Qwen3 или выставь LLM_MOCK=false на GPU-хосте."
    )
    # имитация стрима по словам
    words = text.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
