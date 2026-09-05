from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import Order
from meza.rules.finance import compute_margin
from meza.services.finance import cost_breakdown

router = APIRouter(prefix="/api/v1/finance", tags=["finance"])


@router.get("/orders/{order_id}/margin")
async def order_margin(order_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_FINANCE))):
    order = await db.get(Order, order_id)
    if not order:
        return {"error": "not_found"}
    planned, actual = await cost_breakdown(db, order_id)
    result = compute_margin(order.revenue, planned, actual)
    return {"order_number": order.number, **result.as_dict()}


@router.get("/overview")
async def finance_overview(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_FINANCE))):
    from sqlalchemy import select

    orders = (await db.execute(select(Order).where(Order.status.notin_(["CANCELLED"])))).scalars().all()
    rows = []
    total_revenue = 0.0
    total_actual = 0.0
    for order in orders:
        planned, actual = await cost_breakdown(db, order.id)
        if not planned and not actual:
            continue
        result = compute_margin(order.revenue, planned, actual)
        total_revenue += result.revenue
        total_actual += result.actual_total
        rows.append({"order_id": order.id, "order_number": order.number, **result.as_dict()})
    return {"orders": rows, "total_revenue": round(total_revenue, 2), "total_actual_cost": round(total_actual, 2)}
