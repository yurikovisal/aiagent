"""Ollama-backed LLM provider. Supports chat, structured (JSON-schema) output, and embeddings."""

from __future__ import annotations

import json
import time

import httpx

from meza.core.config import get_settings
from meza.llm.base import LLMProvider, LLMResponse, LLMUsage


class OllamaProvider(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str | None = None, timeout: int | None = None):
        settings = get_settings()
        self.base_url = (base_url or settings.ollama_url).rstrip("/")
        self.timeout = timeout or settings.llm_timeout_seconds

    async def chat(
        self,
        messages: list[dict],
        *,
        model: str | None = None,
        temperature: float = 0.2,
        max_tokens: int | None = None,
        json_schema: dict | None = None,
    ) -> LLMResponse:
        settings = get_settings()
        model_name = model or settings.effective_model
        payload: dict = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if max_tokens:
            payload["options"]["num_predict"] = max_tokens
        if json_schema:
            payload["format"] = json_schema
        started = time.perf_counter()
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        text = data.get("message", {}).get("content", "")
        usage = LLMUsage(
            prompt_tokens=data.get("prompt_eval_count", 0),
            completion_tokens=data.get("eval_count", 0),
            generation_ms=elapsed_ms,
        )
        return LLMResponse(text=text, usage=usage, model=model_name, raw=data)

    async def chat_json(
        self,
        messages: list[dict],
        schema: dict,
        *,
        model: str | None = None,
        temperature: float = 0.1,
    ) -> tuple[dict, LLMResponse]:
        resp = await self.chat(messages, model=model, temperature=temperature, json_schema=schema)
        try:
            return json.loads(resp.text), resp
        except json.JSONDecodeError:
            # local small models occasionally wrap JSON in prose; try to salvage
            start, end = resp.text.find("{"), resp.text.rfind("}")
            if start != -1 and end != -1:
                return json.loads(resp.text[start : end + 1]), resp
            raise

    async def embed(self, texts: list[str], *, model: str | None = None) -> list[list[float]]:
        settings = get_settings()
        model_name = model or settings.embedding_model
        out: list[list[float]] = []
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for text in texts:
                resp = await client.post(f"{self.base_url}/api/embeddings", json={"model": model_name, "prompt": text})
                resp.raise_for_status()
                out.append(resp.json().get("embedding", []))
        return out

    async def health(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                tags = [m["name"] for m in resp.json().get("models", [])]
            return {"status": "ok", "url": self.base_url, "models": tags}
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "url": self.base_url, "error": str(exc)}
