"""Заготовка безопасности: Fernet для секретов коннекторов, JWT — фаза 1."""

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings


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
