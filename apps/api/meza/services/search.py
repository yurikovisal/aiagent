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


async def semantic_search_chunks(db: AsyncSession, query_embedding: list[float], *, limit: int = 8) -> list[dict]:
    rows = (await db.execute(select(DocumentChunk).where(DocumentChunk.embedding.is_not(None)))).scalars().all()
    scored = [(c, _cosine(query_embedding, c.embedding or [])) for c in rows]
    scored.sort(key=lambda t: -t[1])
    out = []
    for chunk, score in scored[:limit]:
        out.append({"document_id": chunk.document_id, "chunk_index": chunk.chunk_index, "content": chunk.content, "score": round(score, 4)})
    return out
