from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import COOKIE_NAME, get_current_user
from meza.core.config import get_settings
from meza.core.db import get_db
from meza.core.rbac import permissions_for
from meza.core.security import create_access_token, hash_password, verify_password
from meza.core.utils import utcnow
from meza.models import User

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    user: dict


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == payload.email))).scalars().first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Неверный email или пароль.")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Учётная запись деактивирована.")
    token = create_access_token(str(user.id), user.role)
    user.last_login_at = utcnow()
    await db.commit()
    settings = get_settings()
    response.set_cookie(COOKIE_NAME, token, httponly=True, secure=settings.cookie_secure, samesite="lax",
                         max_age=settings.access_token_minutes * 60)
    return LoginResponse(access_token=token, user={
        "id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role,
        "permissions": sorted(p.value for p in permissions_for(user.role)),
    })


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(COOKIE_NAME)
    return {"ok": True}


@router.get("/me")
async def me(user: User = Depends(get_current_user)):
    return {
        "id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role,
        "department": user.department,
        "permissions": sorted(p.value for p in permissions_for(user.role)),
    }


class ChangePassword(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password")
async def change_password(payload: ChangePassword, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Self-service password change — anyone can change their OWN password without needing
    MANAGE_USERS (that permission is for an admin changing someone else's account)."""
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(401, "Текущий пароль неверен.")
    if len(payload.new_password) < 8:
        raise HTTPException(422, "Новый пароль должен быть не короче 8 символов.")
    user.password_hash = hash_password(payload.new_password)
    await db.commit()
    return {"ok": True}
