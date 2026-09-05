"""Approval Engine (§23). WRITE_LOW_RISK / WRITE_HIGH_RISK / EXTERNAL_ACTION tools never execute
directly — they create an Approval row and stop. A human decides via /approvals/{id}/decide.
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.errors import NotFoundError, ValidationFailedError
from meza.core.rbac import Permission, has_permission
from meza.core.utils import new_id, utcnow
from meza.models import Approval, Material, PurchaseRequest
from meza.tools.base import ToolRisk


async def propose_purchase_request(
    db: AsyncSession,
    *,
    material: Material,
    quantity: float,
    reason: str,
    needed_by: date | None,
    order_id: int | None,
    agent_id: str,
    user_id: int | None,
    run_id: str | None,
) -> Approval:
    approval = Approval(
        title=f"Заявка на закупку: {material.name} — {quantity:g} {material.unit}",
        description=reason,
        tool_name="create_purchase_request",
        parameters={
            "material_id": material.id,
            "material_name": material.name,
            "quantity": quantity,
            "unit": material.unit,
            "needed_by": needed_by.isoformat() if needed_by else None,
            "order_id": order_id,
            "reason": reason,
        },
        risk=ToolRisk.WRITE_LOW_RISK.value,
        status="PENDING",
        proposed_by_agent=agent_id,
        proposed_by_user_id=user_id,
        run_id=run_id,
        evidence=[{"fact": reason, "source": "meza_agent", "confidence": 1.0}],
        created_at=utcnow(),
    )
    db.add(approval)
    await db.flush()
    return approval


async def decide_approval(db: AsyncSession, approval_id: int, *, decision: str, user_id: int, role: str, comment: str = "") -> Approval:
    approval = await db.get(Approval, approval_id)
    if not approval:
        raise NotFoundError(f"Approval {approval_id} not found")
    if approval.status != "PENDING":
        raise ValidationFailedError(f"Approval {approval_id} is already {approval.status}")
    required = Permission.APPROVE_HIGH if approval.risk == ToolRisk.WRITE_HIGH_RISK.value else Permission.APPROVE_LOW
    if not has_permission(role, required):
        from meza.core.errors import PermissionDeniedError

        raise PermissionDeniedError(f"Role {role} cannot decide approvals of risk {approval.risk}")
    if decision not in ("APPROVED", "REJECTED"):
        raise ValidationFailedError("decision must be APPROVED or REJECTED")
    approval.status = decision
    approval.decided_by_user_id = user_id
    approval.decided_at = utcnow()
    approval.decision_comment = comment
    await db.flush()
    if decision == "APPROVED":
        await _execute_approval(db, approval)
    return approval


async def _execute_approval(db: AsyncSession, approval: Approval) -> None:
    """Executes the underlying write now that a human has approved it."""
    if approval.tool_name == "create_purchase_request":
        params = approval.parameters
        count = (await db.execute(select(PurchaseRequest))).scalars().all()
        number = f"PR-{1000 + len(count) + 1}"
        pr = PurchaseRequest(
            number=number,
            material_id=params["material_id"],
            quantity=params["quantity"],
            unit=params.get("unit", "kg"),
            needed_by=date.fromisoformat(params["needed_by"]) if params.get("needed_by") else None,
            reason=params.get("reason", ""),
            status="APPROVED",
            order_id=params.get("order_id"),
            requested_by="MEZA",
            created_by_agent=approval.proposed_by_agent,
            approval_id=approval.id,
        )
        db.add(pr)
        await db.flush()
        approval.execution_result = {"purchase_request_id": pr.id, "number": pr.number}
        approval.status = "EXECUTED"
    else:
        approval.status = "EXECUTED"
        approval.execution_result = {"note": "no-op: unknown tool_name"}
    await db.flush()
