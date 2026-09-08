"""User management (§25 RBAC): create/list/edit users and roles. All server-side gated by
MANAGE_USERS — never relying on the frontend to hide a button."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import get_current_user, require_permission
from meza.core.rbac import Permission, Role
from meza.core.db import get_db
from meza.core.security import hash_password
from meza.core.utils import utcnow
from meza.models import User
from meza.services import audit as audit_svc

router = APIRouter(prefix="/api/v1/users", tags=["users"])


def _safe(u: User) -> dict:
    d = u.as_dict()
    d.pop("password_hash", None)
    return d


@router.get("")
async def list_users(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.MANAGE_USERS))):
    rows = (await db.execute(select(User).order_by(User.created_at))).scalars().all()
    return [_safe(u) for u in rows]


@router.get("/roles")
async def list_roles(_=Depends(require_permission(Permission.MANAGE_USERS))):
    from meza.core.rbac import permissions_for

    return [{"role": r.value, "permissions": sorted(p.value for p in permissions_for(r))} for r in Role]


class CreateUser(BaseModel):
    email: EmailStr
    full_name: str = ""
    password: str
    role: str = Role.VIEWER.value
    department: str | None = None


@router.post("")
async def create_user(payload: CreateUser, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if payload.role not in {r.value for r in Role}:
        raise HTTPException(422, f"Неизвестная роль: {payload.role}")
    existing = (await db.execute(select(User).where(User.email == payload.email))).scalars().first()
    if existing:
        raise HTTPException(409, "Пользователь с таким email уже существует.")
    new_user = User(
        email=payload.email, full_name=payload.full_name, password_hash=hash_password(payload.password),
        role=payload.role, department=payload.department, is_active=True,
    )
    db.add(new_user)
    await db.flush()
    await audit_svc.record(db, action="user_created", user_id=user.id, user_email=user.email,
                            result={"created_user_id": new_user.id, "role": new_user.role}, entity_type="user", entity_id=new_user.id)
    await db.commit()
    return _safe(new_user)


class UpdateUser(BaseModel):
    full_name: str | None = None
    role: str | None = None
    department: str | None = None
    is_active: bool | None = None
    password: str | None = None


@router.patch("/{user_id}")
async def update_user(user_id: int, payload: UpdateUser, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from meza.core.rbac import has_permission

    if not has_permission(user.role, Permission.MANAGE_USERS):
        raise HTTPException(403, "Недостаточно прав.")
    target = await db.get(User, user_id)
    if not target:
        raise HTTPException(404, "Пользователь не найден.")
    if payload.role is not None:
        if payload.role not in {r.value for r in Role}:
            raise HTTPException(422, f"Неизвестная роль: {payload.role}")
        if target.id == user.id and payload.role != user.role:
            raise HTTPException(422, "Нельзя изменить собственную роль.")
        target.role = payload.role
    if payload.full_name is not None:
        target.full_name = payload.full_name
    if payload.department is not None:
        target.department = payload.department
    if payload.is_active is not None:
        if target.id == user.id and not payload.is_active:
            raise HTTPException(422, "Нельзя деактивировать собственную учётную запись.")
        target.is_active = payload.is_active
    if payload.password:
        target.password_hash = hash_password(payload.password)
    await audit_svc.record(db, action="user_updated", user_id=user.id, user_email=user.email,
                            result={"target_user_id": target.id, "changes": payload.model_dump(exclude_none=True, exclude={"password"})},
                            entity_type="user", entity_id=target.id)
    await db.commit()
    return _safe(target)
