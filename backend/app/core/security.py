"""JWT, пароли, Fernet для секретов коннекторов."""

from __future__ import annotations

import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import bcrypt
import jwt
from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except ValueError:
        return False


def create_access_token(*, user_id: UUID, role: str, email: str) -> str:
    settings = get_settings()
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "email": email,
        "role": role,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(payload, settings.api_secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    return jwt.decode(token, settings.api_secret_key, algorithms=[settings.jwt_algorithm])


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def refresh_expiry() -> datetime:
    settings = get_settings()
    return datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)


def _fernet() -> Fernet | None:
    key = get_settings().fernet_key
    if not key:
        return None
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(plaintext: str) -> str:
    f = _fernet()
    if f is None:
        raise RuntimeError("FERNET_KEY is not configured")
    return f.encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    f = _fernet()
    if f is None:
        raise RuntimeError("FERNET_KEY is not configured")
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken as exc:
        raise ValueError("Invalid encrypted secret") from exc


def generate_fernet_key() -> str:
    return Fernet.generate_key().decode()
