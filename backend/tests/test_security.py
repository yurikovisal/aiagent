from uuid import uuid4

from app.core.security import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    hashed = hash_password("correct-horse")
    assert verify_password("correct-horse", hashed)
    assert not verify_password("wrong", hashed)


def test_jwt_access_token():
    uid = uuid4()
    token = create_access_token(user_id=uid, role="admin", email="a@b.c")
    payload = decode_token(token)
    assert payload["sub"] == str(uid)
    assert payload["role"] == "admin"
    assert payload["type"] == "access"
