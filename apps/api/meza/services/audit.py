"""Audit log writer (§24). Every AI action and governance decision lands here."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.utils import jsonable, utcnow
from meza.models import AuditLog


async def record(
    db: AsyncSession,
    *,
    action: str,
    user_id: int | None = None,
    user_email: str = "",
    agent: str = "",
    request: str = "",
    tool: str = "",
    parameters: dict | None = None,
    result: dict | None = None,
    approval_id: int | None = None,
    execution_status: str = "",
    duration_ms: int = 0,
    request_id: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        timestamp=utcnow(),
        user_id=user_id,
        user_email=user_email,
        agent=agent,
        action=action,
        request=request,
        tool=tool,
        parameters=jsonable(parameters or {}),
        result=jsonable(result or {}),
        approval_id=approval_id,
        execution_status=execution_status,
        duration_ms=duration_ms,
        request_id=request_id,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
    )
    db.add(entry)
    await db.flush()
    return entry
