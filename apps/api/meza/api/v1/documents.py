from __future__ import annotations

import hashlib
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import get_current_user, require_permission
from meza.core.config import get_settings
from meza.core.db import get_db
from meza.core.logging import get_logger
from meza.core.rbac import Permission
from meza.core.utils import utcnow
from meza.llm.factory import get_llm_provider
from meza.models import Document, DocumentChunk, User
from meza.services.documents import ALLOWED_EXTENSIONS, chunk_text, classify_document, extract_text

logger = get_logger("meza.documents")

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])


@router.get("")
async def list_documents(doc_type: str | None = None, db: AsyncSession = Depends(get_db),
                          _=Depends(require_permission(Permission.READ_DOCUMENTS))):
    q = select(Document)
    if doc_type:
        q = q.where(Document.doc_type == doc_type)
    rows = (await db.execute(q.order_by(Document.created_at.desc()))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/{document_id}")
async def get_document(document_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_DOCUMENTS))):
    d = await db.get(Document, document_id)
    return d.as_dict() if d else {"error": "not_found"}


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), user: User = Depends(get_current_user),
                           db: AsyncSession = Depends(get_db)):
    from meza.core.rbac import has_permission

    if not has_permission(user.role, Permission.WRITE_DOCUMENTS):
        raise HTTPException(403, "Недостаточно прав для загрузки документов.")
    settings = get_settings()
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(422, f"Недопустимый тип файла: {ext}")
    content = await file.read()
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(422, f"Файл превышает лимит {settings.max_upload_mb} MB.")
    sha = hashlib.sha256(content).hexdigest()
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    stored_name = f"{sha}{ext}"
    stored_path = settings.upload_path / stored_name
    stored_path.write_bytes(content)
    text = extract_text(stored_path, ext)
    doc_type, confidence = classify_document(file.filename or "", text)
    doc = Document(
        title=file.filename or stored_name, filename=file.filename or stored_name,
        stored_path=str(stored_path), mime_type=file.content_type or "", size_bytes=len(content),
        sha256=sha, doc_type=doc_type, classification_confidence=confidence, status="INGESTED",
        text_content=text[:200_000], uploaded_by=user.id,
    )
    db.add(doc)
    await db.flush()

    # Chunk + embed for semantic search (§18/§26 knowledge base). Best-effort: a document is
    # still usable via keyword search even if embedding fails or the local LLM is unreachable.
    settings2 = get_settings()
    provider = get_llm_provider()
    if provider is not None and text.strip():
        chunks = chunk_text(text)
        try:
            vectors = await provider.embed(chunks, model=settings2.embedding_model)
            for i, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False)):
                db.add(DocumentChunk(document_id=doc.id, chunk_index=i, content=chunk, embedding=vector, embedding_model=settings2.embedding_model))
        except Exception as exc:  # noqa: BLE001
            logger.info(f"embedding failed for document {doc.id}: {exc}")

    await db.commit()
    return doc.as_dict()
