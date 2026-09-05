from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import Material
from meza.services import warehouse as warehouse_svc

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])


@router.get("/materials")
async def list_materials(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_WAREHOUSE))):
    rows = (await db.execute(select(Material).order_by(Material.name))).scalars().all()
    out = []
    for m in rows:
        summary = await warehouse_svc.stock_summary(db, m.id)
        out.append({**m.as_dict(), **{k: v for k, v in summary.items() if k not in ("material_id",)}})
    return out


@router.get("/materials/{material_id}")
async def get_material(material_id: int, db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_WAREHOUSE))):
    m = await db.get(Material, material_id)
    if not m:
        return {"error": "not_found"}
    summary = await warehouse_svc.stock_summary(db, m.id)
    incoming = await warehouse_svc.incoming_purchase_orders(db, m.id)
    return {**m.as_dict(), "stock": summary, "incoming": [p.as_dict() for p in incoming]}


@router.get("/low-stock")
async def low_stock(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_WAREHOUSE))):
    return await warehouse_svc.low_stock_materials(db)


@router.get("/slow-moving")
async def slow_moving(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_WAREHOUSE))):
    return await warehouse_svc.slow_moving_materials(db)
