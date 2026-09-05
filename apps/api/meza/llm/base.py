"""LLM provider interface. Ollama is the default/primary implementation; other
providers can be added later without touching agents or tools."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class LLMUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    generation_ms: int = 0

    @property
    def tokens_per_sec(self) -> float:
        if self.generation_ms <= 0:
            return 0.0
        return round(self.completion_tokens / (self.generation_ms / 1000), 2)


@dataclass
class LLMResponse:
    text: str
    usage: LLMUsage = field(default_factory=LLMUsage)
    model: str = ""
    raw: dict | None = None


class LLMProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        json_schema: dict | None = None,
    ) -> LLMResponse: ...

    @abstractmethod
    async def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]: ...

    @abstractmethod
    async def health(self) -> dict: ...
