"""End-to-end HTTP tests for user management (§25 RBAC) — the first tests to exercise the
actual FastAPI routing/dependency wiring rather than calling service functions directly."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from meza.app import app
from meza.core.db import get_db
from meza.core.rbac import Role
from meza.core.security import hash_password
from meza.models import User


@pytest_asyncio.fixture
async def client(db_session):
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


async def _login_as(client: AsyncClient, db_session, role: str) -> str:
    user = User(email=f"{role.lower()}@atonplus-test.example.kz", full_name=role.title(), password_hash=hash_password("pw12345"), role=role, is_active=True)
    db_session.add(user)
    await db_session.flush()
    resp = await client.post("/api/v1/auth/login", json={"email": user.email, "password": "pw12345"})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


@pytest.mark.asyncio
async def test_health_endpoint_reachable(client):
    resp = await client.get("/api/v1/system/health")
    assert resp.status_code == 200
    assert resp.json()["status"] in ("ok", "degraded")


@pytest.mark.asyncio
async def test_login_wrong_password_rejected(client, db_session):
    user = User(email="x@atonplus-test.example.kz", full_name="X", password_hash=hash_password("correct"), role=Role.VIEWER.value, is_active=True)
    db_session.add(user)
    await db_session.flush()
    resp = await client.post("/api/v1/auth/login", json={"email": "x@atonplus-test.example.kz", "password": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_viewer_cannot_list_users(client, db_session):
    token = await _login_as(client, db_session, Role.VIEWER.value)
    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_create_and_list_users(client, db_session):
    token = await _login_as(client, db_session, Role.ADMIN.value)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/api/v1/users", json={
        "email": "newhire@atonplus-test.example.kz", "full_name": "New Hire", "password": "pw12345", "role": "EMPLOYEE",
    }, headers=headers)
    assert resp.status_code == 200, resp.text
    created = resp.json()
    assert "password_hash" not in created

    resp = await client.get("/api/v1/users", headers=headers)
    emails = {u["email"] for u in resp.json()}
    assert "newhire@atonplus-test.example.kz" in emails


@pytest.mark.asyncio
async def test_admin_cannot_demote_own_role(client, db_session):
    token = await _login_as(client, db_session, Role.ADMIN.value)
    headers = {"Authorization": f"Bearer {token}"}
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    resp = await client.patch(f"/api/v1/users/{me['id']}", json={"role": "VIEWER"}, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_admin_cannot_deactivate_self(client, db_session):
    token = await _login_as(client, db_session, Role.ADMIN.value)
    headers = {"Authorization": f"Bearer {token}"}
    me = (await client.get("/api/v1/auth/me", headers=headers)).json()
    resp = await client.patch(f"/api/v1/users/{me['id']}", json={"is_active": False}, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_creating_duplicate_email_conflicts(client, db_session):
    token = await _login_as(client, db_session, Role.ADMIN.value)
    headers = {"Authorization": f"Bearer {token}"}
    payload = {"email": "dup@atonplus-test.example.kz", "full_name": "Dup", "password": "pw12345", "role": "VIEWER"}
    first = await client.post("/api/v1/users", json=payload, headers=headers)
    assert first.status_code == 200
    second = await client.post("/api/v1/users", json=payload, headers=headers)
    assert second.status_code == 409


@pytest.mark.asyncio
async def test_unauthenticated_request_rejected(client):
    resp = await client.get("/api/v1/users")
    assert resp.status_code == 401
