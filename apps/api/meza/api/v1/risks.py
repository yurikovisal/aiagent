from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.services import risk_engine

router = APIRouter(prefix="/api/v1/risks", tags=["risks"])


@router.get("")
async def list_risks(domain: str | None = None, min_severity: str | None = None, limit: int = 50,
                      db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_OVERVIEW))):
    return await risk_engine.list_open_risks(db, domain=domain, min_severity=min_severity, limit=limit)


@router.post("/evaluate")
async def evaluate_risks(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_OVERVIEW))):
    """Manually trigger the rule-based Risk Engine (normally run by the scheduler/orchestrator)."""
    risks = await risk_engine.run_all_rules(db)
    await db.commit()
    return {"evaluated": len(risks)}
