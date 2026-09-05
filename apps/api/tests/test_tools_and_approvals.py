"""Tool-permission and Approval-Engine tests (§50 Security: unauthorized tool calls,
approval bypass attempts)."""

from __future__ import annotations

import pytest

from meza.core.errors import PermissionDeniedError, ValidationFailedError
from meza.core.rbac import Role
from meza.core.utils import utcnow
from meza.models import Material, Warehouse, Stock
from meza.orchestrator.executor import Budget, execute_tool
from meza.services.approvals import decide_approval, propose_purchase_request
from meza.tools.base import ToolContext


async def _seed_material(db_session):
    wh = Warehouse(code="MAIN", name="Main")
    db_session.add(wh)
    await db_session.flush()
    mat = Material(sku="X-1", name="Test Material", unit="kg", min_stock=10)
    db_session.add(mat)
    await db_session.flush()
    db_session.add(Stock(material_id=mat.id, warehouse_id=wh.id, quantity=100, reserved=0))
    await db_session.flush()
    return mat


@pytest.mark.asyncio
async def test_viewer_cannot_call_write_tool(db_session):
    mat = await _seed_material(db_session)
    ctx = ToolContext(db=db_session, user_id=1, role=Role.VIEWER.value, run_id="r1", agent_id="test")
    budget = Budget(10, 10, 3)
    result = await execute_tool(db_session, tool_name="create_purchase_request", params={
        "material_sku": mat.sku, "quantity": 10, "reason": "test",
    }, ctx=ctx, budget=budget)
    assert result.ok is False
    assert "прав" in result.error.lower()


@pytest.mark.asyncio
async def test_read_tool_available_to_employee(db_session):
    mat = await _seed_material(db_session)
    ctx = ToolContext(db=db_session, user_id=1, role=Role.EMPLOYEE.value, run_id="r2", agent_id="test")
    budget = Budget(10, 10, 3)
    result = await execute_tool(db_session, tool_name="get_inventory", params={"material_sku": mat.sku}, ctx=ctx, budget=budget)
    assert result.ok is True


@pytest.mark.asyncio
async def test_budget_exhaustion_blocks_further_tool_calls(db_session):
    mat = await _seed_material(db_session)
    ctx = ToolContext(db=db_session, user_id=1, role=Role.ADMIN.value, run_id="r3", agent_id="test")
    budget = Budget(10, 1, 3)  # only 1 tool call allowed
    first = await execute_tool(db_session, tool_name="get_inventory", params={"material_sku": mat.sku}, ctx=ctx, budget=budget)
    second = await execute_tool(db_session, tool_name="get_inventory", params={"material_sku": mat.sku}, ctx=ctx, budget=budget)
    assert first.ok is True
    assert second.ok is False
    assert "лимит" in second.error.lower()


@pytest.mark.asyncio
async def test_write_tool_creates_pending_approval_not_direct_write(db_session):
    mat = await _seed_material(db_session)
    approval = await propose_purchase_request(
        db_session, material=mat, quantity=50, reason="test shortage", needed_by=None,
        order_id=None, agent_id="procurement", user_id=1, run_id="r4",
    )
    assert approval.status == "PENDING"
    from meza.models import PurchaseRequest
    from sqlalchemy import select

    existing = (await db_session.execute(select(PurchaseRequest))).scalars().all()
    assert existing == []  # nothing was actually created yet — awaiting human approval


@pytest.mark.asyncio
async def test_manager_cannot_approve_write_low_risk_without_permission(db_session):
    mat = await _seed_material(db_session)
    approval = await propose_purchase_request(
        db_session, material=mat, quantity=50, reason="test", needed_by=None,
        order_id=None, agent_id="procurement", user_id=1, run_id="r5",
    )
    with pytest.raises(PermissionDeniedError):
        await decide_approval(db_session, approval.id, decision="APPROVED", user_id=2, role=Role.VIEWER.value)


@pytest.mark.asyncio
async def test_approving_twice_is_rejected(db_session):
    mat = await _seed_material(db_session)
    approval = await propose_purchase_request(
        db_session, material=mat, quantity=50, reason="test", needed_by=None,
        order_id=None, agent_id="procurement", user_id=1, run_id="r6",
    )
    await decide_approval(db_session, approval.id, decision="APPROVED", user_id=1, role=Role.DIRECTOR.value)
    with pytest.raises(ValidationFailedError):
        await decide_approval(db_session, approval.id, decision="APPROVED", user_id=1, role=Role.DIRECTOR.value)


@pytest.mark.asyncio
async def test_approval_executes_purchase_request_on_approve(db_session):
    mat = await _seed_material(db_session)
    approval = await propose_purchase_request(
        db_session, material=mat, quantity=50, reason="test", needed_by=None,
        order_id=None, agent_id="procurement", user_id=1, run_id="r7",
    )
    result = await decide_approval(db_session, approval.id, decision="APPROVED", user_id=1, role=Role.DIRECTOR.value)
    assert result.status == "EXECUTED"
    assert result.execution_result["number"].startswith("PR-")


@pytest.mark.asyncio
async def test_rejected_approval_never_creates_purchase_request(db_session):
    mat = await _seed_material(db_session)
    approval = await propose_purchase_request(
        db_session, material=mat, quantity=50, reason="test", needed_by=None,
        order_id=None, agent_id="procurement", user_id=1, run_id="r8",
    )
    result = await decide_approval(db_session, approval.id, decision="REJECTED", user_id=1, role=Role.DIRECTOR.value)
    assert result.status == "REJECTED"
    from meza.models import PurchaseRequest
    from sqlalchemy import select

    existing = (await db_session.execute(select(PurchaseRequest))).scalars().all()
    assert existing == []
