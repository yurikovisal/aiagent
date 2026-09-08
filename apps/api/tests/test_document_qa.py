"""Document Q&A and summarization (§18): grounded in retrieved chunks, never invented."""

from __future__ import annotations

import pytest

from meza.services.documents import summarize_text


@pytest.mark.asyncio
async def test_summarize_text_returns_empty_when_llm_unavailable(monkeypatch):
    import meza.services.documents as docs_module

    monkeypatch.setattr(docs_module, "get_llm_provider", lambda: None, raising=False)
    # Patch the lazy import target used inside summarize_text
    import meza.llm.factory as factory_module

    monkeypatch.setattr(factory_module, "get_llm_provider", lambda: None)
    result = await summarize_text("Some contract text.", doc_type="CONTRACT")
    assert result == ""


@pytest.mark.asyncio
async def test_summarize_text_returns_empty_for_blank_input():
    result = await summarize_text("   ", doc_type="CONTRACT")
    assert result == ""
