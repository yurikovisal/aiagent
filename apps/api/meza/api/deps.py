"""FastAPI dependencies: current user, permission enforcement, request-scoped logging context."""

from __future__ import annotations

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.db import get_db
from meza.core.logging import request_id_var, user_id_var
from meza.core.rbac import Permission, has_permission
from meza.core.security import decode_token
from meza.models import User

COOKIE_NAME = "meza_session"


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: str | None = Header(default=None),
    session_cookie: str | None = Cookie(default=None, alias=COOKIE_NAME),
) -> User:
    token = None
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1]
    elif session_cookie:
        token = session_cookie
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Не авторизовано.")
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Недействительный токен.")
    user = await db.get(User, int(payload["sub"]))
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Пользователь не найден или деактивирован.")
    user_id_var.set(user.id)
    return user


def require_permission(permission: Permission):
    async def checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"Недостаточно прав: требуется {permission.value}.")
        return user

    return checker
