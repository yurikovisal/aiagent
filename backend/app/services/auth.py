from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    refresh_expiry,
    verify_password,
)
from app.models import RefreshSession, User, UserRole
from app.schemas.auth import TokenResponse


async def register_user(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    full_name: str = "",
    role: UserRole = UserRole.viewer,
) -> User:
    existing = await db.execute(select(User).where(User.email == email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
    user = User(
        email=email.lower(),
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def authenticate_user(db: AsyncSession, *, email: str, password: str) -> User:
    result = await db.execute(select(User).where(User.email == email.lower()))
    user = result.scalar_one_or_none()
    if user is None or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User disabled")
    return user


async def issue_tokens(
    db: AsyncSession,
    user: User,
    *,
    user_agent: str | None = None,
) -> TokenResponse:
    settings = get_settings()
    access = create_access_token(user_id=user.id, role=user.role.value, email=user.email)
    refresh = generate_refresh_token()
    session = RefreshSession(
        user_id=user.id,
        token_hash=hash_token(refresh),
        expires_at=refresh_expiry(),
        user_agent=user_agent,
    )
    db.add(session)
    await db.commit()
    return TokenResponse(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.access_token_expire_minutes * 60,
    )


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> TokenResponse:
    token_hash = hash_token(refresh_token)
    result = await db.execute(
        select(RefreshSession).where(
            RefreshSession.token_hash == token_hash,
            RefreshSession.revoked.is_(False),
        )
    )
    session = result.scalar_one_or_none()
    now = datetime.now(UTC)
    if session is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires < now:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    user_result = await db.execute(select(User).where(User.id == session.user_id))
    user = user_result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User inactive")

    session.revoked = True
    await db.commit()
    return await issue_tokens(db, user, user_agent=session.user_agent)


async def revoke_refresh_token(db: AsyncSession, refresh_token: str) -> None:
    token_hash = hash_token(refresh_token)
    result = await db.execute(select(RefreshSession).where(RefreshSession.token_hash == token_hash))
    session = result.scalar_one_or_none()
    if session is not None:
        session.revoked = True
        await db.commit()
