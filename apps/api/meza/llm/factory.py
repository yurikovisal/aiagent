from __future__ import annotations

from functools import lru_cache

from meza.core.config import get_settings
from meza.llm.base import LLMProvider


@lru_cache
def get_llm_provider() -> LLMProvider | None:
    settings = get_settings()
    if settings.llm_provider == "ollama":
        from meza.llm.ollama_provider import OllamaProvider

        return OllamaProvider()
    return None
