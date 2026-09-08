"""§21 end-to-end: marketing content is never auto-published — creating a draft, proposing
publication, and only an approved decision flips it to PUBLISHED."""

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
async def test_manager_can_create_draft_content(client, db_session):
    token = await _login_as(client, db_session, Role.MANAGER.value)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/api/v1/marketing/content", json={"title": "Осенняя акция", "channel": "instagram"}, headers=headers)
    assert resp.status_code == 200, resp.text
    item = resp.json()
    assert item["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_viewer_cannot_create_content(client, db_session):
    token = await _login_as(client, db_session, Role.VIEWER.value)
    headers = {"Authorization": f"Bearer {token}"}
    resp = await client.post("/api/v1/marketing/content", json={"title": "X"}, headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_direct_patch_to_published_rejected(client, db_session):
    token = await _login_as(client, db_session, Role.MANAGER.value)
    headers = {"Authorization": f"Bearer {token}"}
    created = (await client.post("/api/v1/marketing/content", json={"title": "Пост"}, headers=headers)).json()
    resp = await client.patch(f"/api/v1/marketing/content/{created['id']}", json={"status": "PUBLISHED"}, headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_propose_and_approve_publish_flow(client, db_session):
    token = await _login_as(client, db_session, Role.MANAGER.value)
    headers = {"Authorization": f"Bearer {token}"}
    created = (await client.post("/api/v1/marketing/content", json={"title": "Новый продукт", "channel": "сайт"}, headers=headers)).json()

    from meza.services.approvals import propose_content_publish

    approval = await propose_content_publish(
        db_session, content_id=created["id"], title=created["title"], channel=created["channel"],
        agent_id="marketing", user_id=None, run_id=None,
    )
    await db_session.commit()
    assert approval.status == "PENDING"
    assert approval.risk == "EXTERNAL_ACTION"

    director_token = await _login_as(client, db_session, Role.DIRECTOR.value)
    dheaders = {"Authorization": f"Bearer {director_token}"}
    decide = await client.post(f"/api/v1/approvals/{approval.id}/decide", json={"decision": "APPROVED"}, headers=dheaders)
    assert decide.status_code == 200, decide.text

    check = await client.get(f"/api/v1/marketing/content/{created['id']}", headers=headers)
    assert check.json()["status"] == "PUBLISHED"


@pytest.mark.asyncio
async def test_human_can_propose_publish_directly(client, db_session):
    token = await _login_as(client, db_session, Role.MANAGER.value)
    headers = {"Authorization": f"Bearer {token}"}
    created = (await client.post("/api/v1/marketing/content", json={"title": "Пост 3", "channel": "сайт"}, headers=headers)).json()

    resp = await client.post(f"/api/v1/marketing/content/{created['id']}/propose-publish", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "PENDING"

    unchanged = await client.get(f"/api/v1/marketing/content/{created['id']}", headers=headers)
    assert unchanged.json()["status"] == "DRAFT"


@pytest.mark.asyncio
async def test_propose_publish_rejects_already_published(client, db_session):
    token = await _login_as(client, db_session, Role.MANAGER.value)
    headers = {"Authorization": f"Bearer {token}"}
    created = (await client.post("/api/v1/marketing/content", json={"title": "Пост 4"}, headers=headers)).json()

    from meza.services.approvals import decide_approval, propose_content_publish

    approval = await propose_content_publish(
        db_session, content_id=created["id"], title=created["title"], channel="сайт",
        agent_id="marketing", user_id=None, run_id=None,
    )
    await db_session.commit()
    director_token = await _login_as(client, db_session, Role.DIRECTOR.value)
    await decide_approval(db_session, approval.id, decision="APPROVED", user_id=1, role=Role.DIRECTOR.value)
    await db_session.commit()

    resp = await client.post(f"/api/v1/marketing/content/{created['id']}/propose-publish", headers=headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_manager_cannot_approve_external_action(client, db_session):
    token = await _login_as(client, db_session, Role.MANAGER.value)
    headers = {"Authorization": f"Bearer {token}"}
    created = (await client.post("/api/v1/marketing/content", json={"title": "Пост 2"}, headers=headers)).json()

    from meza.services.approvals import propose_content_publish

    approval = await propose_content_publish(
        db_session, content_id=created["id"], title=created["title"], channel="сайт",
        agent_id="marketing", user_id=None, run_id=None,
    )
    await db_session.commit()

    resp = await client.post(f"/api/v1/approvals/{approval.id}/decide", json={"decision": "APPROVED"}, headers=headers)
    assert resp.status_code == 403
