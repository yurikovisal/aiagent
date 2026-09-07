"""Document search: full-text (ILIKE / pg_trgm) primary, embedding similarity as a re-ranker.

RAG scope is deliberately narrow (§7): contracts, specs, regulations, tech docs,
commercial offers — never a substitute for the structured SQL layer.
"""

from __future__ import annotations

import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.models import Document, DocumentChunk


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


async def search_documents(db: AsyncSession, query: str, *, doc_type: str | None = None, limit: int = 10) -> list[dict]:
    q = select(Document).where(
        Document.title.ilike(f"%{query}%") | Document.text_content.ilike(f"%{query}%") | Document.summary.ilike(f"%{query}%")
    )
    if doc_type:
        q = q.where(Document.doc_type == doc_type)
    q = q.limit(limit)
    rows = (await db.execute(q)).scalars().all()
    results = []
    for d in rows:
        results.append(
            {
                "id": d.id,
                "title": d.title,
                "doc_type": d.doc_type,
                "summary": d.summary or (d.text_content[:280] if d.text_content else ""),
                "order_id": d.order_id,
                "supplier_id": d.supplier_id,
                "customer_id": d.customer_id,
                "expires_on": d.expires_on.isoformat() if d.expires_on else None,
            }
        )
    return results


async def semantic_search_chunks(db: AsyncSession, query_embedding: list[float], *, limit: int = 8, min_score: float = 0.5) -> list[dict]:
    rows = (await db.execute(select(DocumentChunk).where(DocumentChunk.embedding.is_not(None)))).scalars().all()
    scored = [(c, _cosine(query_embedding, c.embedding or [])) for c in rows]
    scored = [(c, s) for c, s in scored if s >= min_score]
    scored.sort(key=lambda t: -t[1])
    out = []
    for chunk, score in scored[:limit]:
        out.append({"document_id": chunk.document_id, "chunk_index": chunk.chunk_index, "content": chunk.content, "score": round(score, 4)})
    return out


async def search_documents_hybrid(db: AsyncSession, query: str, *, doc_type: str | None = None, limit: int = 10) -> list[dict]:
    """Keyword search first (fast, exact); if the local embedding model is available, also runs
    a semantic pass over document chunks and folds in documents the keyword search missed
    (paraphrased queries, synonyms) — tagged so the caller can tell how each hit was found."""
    keyword_hits = await search_documents(db, query, doc_type=doc_type, limit=limit)
    for hit in keyword_hits:
        hit["matched_via"] = "keyword"
    if len(keyword_hits) >= limit:
        return keyword_hits

    from meza.core.config import get_settings
    from meza.llm.factory import get_llm_provider

    provider = get_llm_provider()
    if provider is None:
        return keyword_hits

    try:
        settings = get_settings()
        [query_embedding] = await provider.embed([query], model=settings.embedding_model)
    except Exception:  # noqa: BLE001
        return keyword_hits

    seen_ids = {h["id"] for h in keyword_hits}
    semantic_hits = await semantic_search_chunks(db, query_embedding, limit=limit)
    for hit in semantic_hits:
        if hit["document_id"] in seen_ids:
            continue
        doc = await db.get(Document, hit["document_id"])
        if not doc or (doc_type and doc.doc_type != doc_type):
            continue
        seen_ids.add(doc.id)
        keyword_hits.append({
            "id": doc.id, "title": doc.title, "doc_type": doc.doc_type,
            "summary": hit["content"][:280], "order_id": doc.order_id, "supplier_id": doc.supplier_id,
            "customer_id": doc.customer_id, "expires_on": doc.expires_on.isoformat() if doc.expires_on else None,
            "matched_via": "semantic", "relevance": hit["score"],
        })
        if len(keyword_hits) >= limit:
            break
    return keyword_hits
