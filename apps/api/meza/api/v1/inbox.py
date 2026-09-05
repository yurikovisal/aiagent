"""MEZA Inbox (§45): unstructured drops get classified and proposed as structured records —
never inserted without human confirmation."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import get_current_user, require_permission
from meza.core.config import get_settings
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.core.utils import utcnow
from meza.models import InboxItem, User
from meza.services.documents import classify_document, extract_text

router = APIRouter(prefix="/api/v1/inbox", tags=["inbox"])


@router.get("")
async def list_inbox(status: str | None = None, db: AsyncSession = Depends(get_db),
                      _=Depends(require_permission(Permission.READ_DOCUMENTS))):
    q = select(InboxItem)
    if status:
        q = q.where(InboxItem.status == status)
    rows = (await db.execute(q.order_by(InboxItem.created_at.desc()))).scalars().all()
    return [r.as_dict() for r in rows]


@router.post("/drop")
async def drop_file(file: UploadFile = File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    settings.inbox_path.mkdir(parents=True, exist_ok=True)
    content = await file.read()
    stored_path = settings.inbox_path / f"{utcnow().timestamp():.0f}_{file.filename}"
    stored_path.write_bytes(content)
    ext = "." + (file.filename or "").rsplit(".", 1)[-1].lower() if "." in (file.filename or "") else ""
    text = extract_text(stored_path, ext)
    doc_type, confidence = classify_document(file.filename or "", text)
    lower = (file.filename or "").lower() + text[:2000].lower()
    if any(k in lower for k in ("приход", "накладная", "receipt")):
        proposal = {"action": "create_warehouse_receipt", "summary": "Похоже на приход товара.", "confidence": 0.6}
    elif doc_type != "UNCLASSIFIED":
        proposal = {"action": "create_document", "summary": f"Похоже на документ типа {doc_type}.", "confidence": confidence}
    else:
        proposal = {"action": "review_manually", "summary": "Не удалось классифицировать автоматически.", "confidence": 0.0}
    item = InboxItem(
        filename=file.filename or "upload", stored_path=str(stored_path), mime_type=file.content_type or "",
        size_bytes=len(content), classification=doc_type, confidence=confidence, proposal=proposal,
        status="PROPOSED", created_by=user.id, created_at=utcnow(),
    )
    db.add(item)
    await db.commit()
    return item.as_dict()


@router.post("/{item_id}/accept")
async def accept_item(item_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    item = await db.get(InboxItem, item_id)
    if not item:
        raise HTTPException(404, "Не найдено.")
    from meza.models import Document

    doc = Document(
        title=item.filename, filename=item.filename, stored_path=item.stored_path, mime_type=item.mime_type,
        size_bytes=item.size_bytes, sha256="", doc_type=item.classification, classification_confidence=item.confidence,
        status="INGESTED", uploaded_by=user.id,
    )
    db.add(doc)
    await db.flush()
    item.status = "ACCEPTED"
    item.document_id = doc.id
    await db.commit()
    return item.as_dict()


@router.post("/{item_id}/reject")
async def reject_item(item_id: int, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_user)):
    item = await db.get(InboxItem, item_id)
    if not item:
        raise HTTPException(404, "Не найдено.")
    item.status = "REJECTED"
    await db.commit()
    return item.as_dict()
