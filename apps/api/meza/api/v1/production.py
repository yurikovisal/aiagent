from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import Order, ProductionOrder, ProductionStage, WorkCenter
from meza.rules.production import propagate_delay
from meza.services import production as production_svc

router = APIRouter(prefix="/api/v1/production", tags=["production"])


@router.get("/work-centers")
async def list_work_centers(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_PRODUCTION))):
    rows = (await db.execute(select(WorkCenter).order_by(WorkCenter.sequence))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/orders")
async def list_production_orders(status: str | None = None, db: AsyncSession = Depends(get_db),
                                  _=Depends(require_permission(Permission.READ_PRODUCTION))):
    q = select(ProductionOrder)
    if status:
        q = q.where(ProductionOrder.status == status)
    rows = (await db.execute(q.order_by(ProductionOrder.planned_start))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/orders/{production_order_id}")
async def get_production_order(production_order_id: int, db: AsyncSession = Depends(get_db),
                                _=Depends(require_permission(Permission.READ_PRODUCTION))):
    po = await db.get(ProductionOrder, production_order_id)
    if not po:
        return {"error": "not_found"}
    stages = await production_svc.get_stages(db, po.id)
    order = await db.get(Order, po.order_id)
    nodes = await production_svc.build_nodes(db, stages)
    impact = production_svc.compute_current_impact(stages, deadline=order.deadline if order else None, nodes=nodes)
    return {"production_order": po.as_dict(), "order": order.as_dict() if order else None,
            "stages": [s.as_dict() for s in stages], "impact": impact.as_dict() if impact else None}


class SimulateDelayRequest(BaseModel):
    stage_id: int | None = None
    extra_delay_days: float


@router.post("/orders/{production_order_id}/simulate-delay")
async def simulate_delay(production_order_id: int, payload: SimulateDelayRequest, db: AsyncSession = Depends(get_db),
                          _=Depends(require_permission(Permission.READ_PRODUCTION))):
    """§37/§54: 'what happens if this stage is delayed by N more days' — causal-chain preview.
    Deterministic (meza.rules.production), never left to the LLM to estimate."""
    po = await db.get(ProductionOrder, production_order_id)
    if not po:
        return {"error": "not_found"}
    stages = await production_svc.get_stages(db, po.id)
    if not stages:
        return {"error": "no_stages"}
    order = await db.get(Order, po.order_id)
    origin = payload.stage_id or next((s.id for s in stages if s.status in ("IN_PROGRESS", "BLOCKED")), stages[0].id)
    nodes = await production_svc.build_nodes(db, stages)
    result = propagate_delay(nodes, origin, payload.extra_delay_days, deadline=order.deadline if order else None)
    return result.as_dict()
