from meza.core.security import create_access_token, decode_token, hash_password, verify_password


def test_password_hash_roundtrip():
    h = hash_password("s3cret!")
    assert verify_password("s3cret!", h)
    assert not verify_password("wrong", h)


def test_password_hash_is_not_plaintext():
    h = hash_password("s3cret!")
    assert h != "s3cret!"
    assert h.startswith("$2b$")


def test_token_roundtrip():
    token = create_access_token("42", "ADMIN")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "ADMIN"


def test_expired_token_rejected():
    import jwt
    import pytest

    token = create_access_token("42", "ADMIN", minutes=-1)
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)
