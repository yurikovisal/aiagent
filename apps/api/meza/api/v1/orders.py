from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import Order, ProductionOrder

router = APIRouter(prefix="/api/v1/orders", tags=["orders"])


@router.get("")
async def list_orders(status: str | None = None, limit: int = 50, offset: int = 0,
                       db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_SALES))):
    q = select(Order)
    if status:
        q = q.where(Order.status == status)
    q = q.order_by(Order.created_at.desc()).offset(offset).limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/{order_id}")
async def get_order(order_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_SALES))):
    order = await db.get(Order, order_id)
    if not order:
        return {"error": "not_found"}
    po = (await db.execute(select(ProductionOrder).where(ProductionOrder.order_id == order_id))).scalars().first()
    data = order.as_dict()
    data["production_order"] = po.as_dict() if po else None
    return data
