# 3. Local LLM provider and default model

Date: 2026-09-05

## Status
Accepted

## Context
§5/§6 require Ollama as the primary local runtime, model chosen from actual
RAM (15 GiB, 4 CPU cores, no GPU in this container).

## Decision
Default model: `qwen2.5:1.5b` for chat/tool-routing, `nomic-embed-text` for
embeddings. Both configured only via `.env` (`LLM_PROVIDER`, `OLLAMA_MODEL`,
`EMBEDDING_MODEL`) — never hard-coded in `meza/llm/*`. An `LLMProvider`
interface (`meza/llm/base.py`) allows adding a non-Ollama provider later
without touching agents/tools.

## Consequences
On the real Mac mini with more RAM, operators can switch to a larger model
(`qwen2.5:7b`, `llama3.1:8b-instruct`, etc.) by editing `.env` only.
