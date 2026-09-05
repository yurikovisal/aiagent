from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import PurchaseOrder, PurchaseRequest, Supplier

router = APIRouter(prefix="/api/v1/procurement", tags=["procurement"])


@router.get("/requests")
async def list_requests(status: str | None = None, db: AsyncSession = Depends(get_db),
                         _=Depends(require_permission(Permission.READ_PROCUREMENT))):
    q = select(PurchaseRequest)
    if status:
        q = q.where(PurchaseRequest.status == status)
    rows = (await db.execute(q.order_by(PurchaseRequest.created_at.desc()))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/orders")
async def list_purchase_orders(status: str | None = None, db: AsyncSession = Depends(get_db),
                                _=Depends(require_permission(Permission.READ_PROCUREMENT))):
    q = select(PurchaseOrder)
    if status:
        q = q.where(PurchaseOrder.status == status)
    rows = (await db.execute(q.order_by(PurchaseOrder.expected_at))).scalars().all()
    return [r.as_dict() for r in rows]


@router.get("/suppliers")
async def list_suppliers(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_PROCUREMENT))):
    rows = (await db.execute(select(Supplier).order_by(Supplier.name))).scalars().all()
    return [r.as_dict() for r in rows]
