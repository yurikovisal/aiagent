import pytest


@pytest.mark.asyncio
async def test_register_login_me(client):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "meza@example.com", "password": "secret123", "full_name": "Meza"},
    )
    assert reg.status_code == 201
    assert reg.json()["email"] == "meza@example.com"

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "meza@example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    me = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["full_name"] == "Meza"


@pytest.mark.asyncio
async def test_chat_stream_mock(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "chat@example.com", "password": "secret123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "chat@example.com", "password": "secret123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    conv = await client.post("/api/v1/chat/conversations", headers=headers, json={"title": "Тест"})
    assert conv.status_code == 201
    conv_id = conv.json()["id"]

    resp = await client.post(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=headers,
        json={"content": "Сколько труб 40x40 на складе?", "stream": False},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "assistant"
    assert "40x40" in body["content"] or "MEZA mock" in body["content"]

    messages = await client.get(
        f"/api/v1/chat/conversations/{conv_id}/messages",
        headers=headers,
    )
    assert messages.status_code == 200
    roles = [m["role"] for m in messages.json()]
    assert roles == ["user", "assistant"]


@pytest.mark.asyncio
async def test_refresh_token(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "refresh@example.com", "password": "secret123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "refresh@example.com", "password": "secret123"},
    )
    refresh = login.json()["refresh_token"]
    renewed = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert renewed.status_code == 200
    assert renewed.json()["access_token"]
