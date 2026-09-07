"""Business Memory API (§26): confirmed ATON+ knowledge a human can manage directly."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import get_current_user, require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import User
from meza.services import business_memory

router = APIRouter(prefix="/api/v1/memory", tags=["memory"])


@router.get("")
async def list_memory(confirmed_only: bool = False, db: AsyncSession = Depends(get_db),
                       _=Depends(require_permission(Permission.USE_MEZA))):
    rows = await business_memory.list_all(db, confirmed_only=confirmed_only)
    return [r.as_dict() for r in rows]


class CreateMemory(BaseModel):
    key: str
    content: str
    category: str = "general"


@router.post("")
async def create_memory(payload: CreateMemory, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """A human directly asserting a fact — confirmed immediately (no approval needed; they are
    typing/confirming it themselves, unlike an agent-proposed fact via remember_business_fact)."""
    from meza.core.rbac import has_permission

    if not has_permission(user.role, Permission.MANAGE_SYSTEM) and not has_permission(user.role, Permission.IMPORT_DATA):
        raise HTTPException(403, "Недостаточно прав для добавления в базу знаний.")
    entry = await business_memory.create_confirmed(db, key=payload.key, content=payload.content, category=payload.category, user_id=user.id)
    await db.commit()
    return entry.as_dict()


@router.delete("/{memory_id}")
async def delete_memory(memory_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from meza.core.rbac import has_permission

    if not has_permission(user.role, Permission.MANAGE_SYSTEM):
        raise HTTPException(403, "Недостаточно прав для удаления записи.")
    ok = await business_memory.delete(db, memory_id)
    if not ok:
        raise HTTPException(404, "Запись не найдена.")
    await db.commit()
    return {"ok": True}
