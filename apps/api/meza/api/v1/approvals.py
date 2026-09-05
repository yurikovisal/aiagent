from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import get_current_user, require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import Approval, User
from meza.services.approvals import decide_approval

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])


@router.get("")
async def list_approvals(status: str | None = None, db: AsyncSession = Depends(get_db),
                          _=Depends(require_permission(Permission.READ_OVERVIEW))):
    q = select(Approval)
    if status:
        q = q.where(Approval.status == status)
    rows = (await db.execute(q.order_by(Approval.created_at.desc()))).scalars().all()
    return [r.as_dict() for r in rows]


class DecisionRequest(BaseModel):
    decision: str  # APPROVED | REJECTED
    comment: str = ""


@router.post("/{approval_id}/decide")
async def decide(approval_id: int, payload: DecisionRequest, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    approval = await decide_approval(db, approval_id, decision=payload.decision, user_id=user.id, role=user.role, comment=payload.comment)
    from meza.services import audit as audit_svc

    await audit_svc.record(
        db, action=f"approval_{payload.decision.lower()}", user_id=user.id, user_email=user.email,
        agent=approval.proposed_by_agent, tool=approval.tool_name, parameters=approval.parameters,
        result=approval.execution_result or {}, approval_id=approval.id, execution_status=approval.status,
        entity_type="approval", entity_id=approval.id,
    )
    await db.commit()
    return approval.as_dict()
