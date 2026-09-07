from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import RiskRule
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


@router.get("/rules")
async def list_rules(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_OVERVIEW))):
    """Risk Engine rule thresholds — configuration, not code (§38)."""
    await risk_engine.ensure_default_rules(db)
    await db.commit()
    rows = (await db.execute(select(RiskRule).order_by(RiskRule.domain, RiskRule.rule_key))).scalars().all()
    return [r.as_dict() for r in rows]


class RuleUpdate(BaseModel):
    enabled: bool | None = None
    params: dict | None = None


@router.patch("/rules/{rule_key}")
async def update_rule(rule_key: str, payload: RuleUpdate, db: AsyncSession = Depends(get_db),
                       _=Depends(require_permission(Permission.MANAGE_SYSTEM))):
    row = (await db.execute(select(RiskRule).where(RiskRule.rule_key == rule_key))).scalars().first()
    if not row:
        raise HTTPException(404, f"Правило '{rule_key}' не найдено.")
    if payload.enabled is not None:
        row.enabled = payload.enabled
    if payload.params is not None:
        row.params = {**(row.params or {}), **payload.params}
    await db.commit()
    return row.as_dict()
