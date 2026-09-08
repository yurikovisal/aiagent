"""Marketing API: campaigns, leads, content items (§21). Publishing content is never done
directly through this router — it always goes through the Approval Engine (propose_content_publish
/ the publish_content tool), which this router's PATCH endpoint does not bypass.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import get_current_user, require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.core.utils import utcnow
from meza.models import Campaign, ContentItem, Lead, User

router = APIRouter(prefix="/api/v1/marketing", tags=["marketing"])


@router.get("/campaigns")
async def list_campaigns(db: AsyncSession = Depends(get_db),
                          _=Depends(require_permission(Permission.READ_MARKETING))):
    rows = (await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/leads")
async def list_leads(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_MARKETING))):
    rows = (await db.execute(select(Lead).order_by(Lead.created_at.desc()))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/content")
async def list_content(status: str | None = None, db: AsyncSession = Depends(get_db),
                        _=Depends(require_permission(Permission.READ_MARKETING))):
    q = select(ContentItem)
    if status:
        q = q.where(ContentItem.status == status.upper())
    rows = (await db.execute(q.order_by(ContentItem.created_at.desc()))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/content/{content_id}")
async def get_content(content_id: int, db: AsyncSession = Depends(get_db),
                       _=Depends(require_permission(Permission.READ_MARKETING))):
    item = await db.get(ContentItem, content_id)
    if not item:
        raise HTTPException(404, "Материал не найден.")
    return item.as_dict()


class CreateContent(BaseModel):
    title: str
    channel: str = ""
    body: str = ""


@router.post("/content")
async def create_content(payload: CreateContent, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from meza.core.rbac import has_permission

    if not has_permission(user.role, Permission.WRITE_MARKETING):
        raise HTTPException(403, "Недостаточно прав для создания материала.")
    item = ContentItem(title=payload.title, channel=payload.channel, body=payload.body, status="DRAFT")
    db.add(item)
    await db.commit()
    return item.as_dict()


class UpdateContent(BaseModel):
    title: str | None = None
    channel: str | None = None
    body: str | None = None
    status: str | None = None


@router.patch("/content/{content_id}")
async def update_content(content_id: int, payload: UpdateContent, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Editing draft fields and marking REVIEW/APPROVED is allowed here — moving a content item
    to PUBLISHED is NOT: that only ever happens via an executed Approval (§21)."""
    from meza.core.rbac import has_permission

    if not has_permission(user.role, Permission.WRITE_MARKETING):
        raise HTTPException(403, "Недостаточно прав для изменения материала.")
    item = await db.get(ContentItem, content_id)
    if not item:
        raise HTTPException(404, "Материал не найден.")
    if payload.status == "PUBLISHED":
        raise HTTPException(422, "Публикация выполняется только через утверждение (Approval Engine).")
    if payload.title is not None:
        item.title = payload.title
    if payload.channel is not None:
        item.channel = payload.channel
    if payload.body is not None:
        item.body = payload.body
    if payload.status is not None:
        item.status = payload.status
    item.updated_at = utcnow()
    await db.commit()
    return item.as_dict()


@router.post("/content/{content_id}/propose-publish")
async def propose_publish(content_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """A human clicking 'propose publish' in the UI — same Approval Engine path an agent's
    publish_content tool call takes (§21), just triggered directly instead of via chat."""
    from meza.core.rbac import has_permission
    from meza.services.approvals import propose_content_publish

    if not has_permission(user.role, Permission.WRITE_MARKETING):
        raise HTTPException(403, "Недостаточно прав для предложения публикации.")
    item = await db.get(ContentItem, content_id)
    if not item:
        raise HTTPException(404, "Материал не найден.")
    if item.status == "PUBLISHED":
        raise HTTPException(422, "Материал уже опубликован.")
    approval = await propose_content_publish(
        db, content_id=item.id, title=item.title, channel=item.channel or "не указан",
        agent_id="user", user_id=user.id, run_id=None,
    )
    await db.commit()
    return {"approval_id": approval.id, "status": approval.status}
