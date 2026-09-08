from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import get_current_user, require_permission
from meza.core.db import get_db
from meza.core.rbac import Permission
from meza.models import InventoryMovement, Material, User, Warehouse
from meza.services import audit as audit_svc
from meza.services import warehouse as warehouse_svc

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])

MOVEMENT_TYPES = {"RECEIPT", "CONSUMPTION", "TRANSFER_IN", "TRANSFER_OUT", "ADJUSTMENT"}


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


@router.get("/warehouses")
async def list_warehouses(db: AsyncSession = Depends(get_db), _=Depends(require_permission(Permission.READ_WAREHOUSE))):
    rows = (await db.execute(select(Warehouse))).scalars().all()
    return [w.as_dict() for w in rows]


@router.get("/materials/{material_id}/movements")
async def list_movements(material_id: int, limit: int = 50, db: AsyncSession = Depends(get_db),
                          _=Depends(require_permission(Permission.READ_WAREHOUSE))):
    q = (
        select(InventoryMovement)
        .where(InventoryMovement.material_id == material_id)
        .order_by(InventoryMovement.occurred_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(q)).scalars().all()
    return [r.as_dict() for r in rows]


class RecordMovement(BaseModel):
    warehouse_id: int
    movement_type: str
    quantity: float
    note: str = ""


@router.post("/materials/{material_id}/movements")
async def record_movement(material_id: int, payload: RecordMovement, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Manually record what physically happened at the warehouse (a receipt, consumption,
    adjustment, or transfer). This is a person recording a fact that already occurred — unlike
    an agent PROPOSING a purchase, it's not gated by the Approval Engine, only by RBAC."""
    from meza.core.rbac import has_permission

    if not has_permission(user.role, Permission.WRITE_WAREHOUSE):
        raise HTTPException(403, "Недостаточно прав для записи движения склада.")
    if payload.movement_type not in MOVEMENT_TYPES:
        raise HTTPException(422, f"Недопустимый тип движения. Разрешены: {sorted(MOVEMENT_TYPES)}")
    if payload.quantity <= 0:
        raise HTTPException(422, "Количество должно быть положительным.")
    material = await db.get(Material, material_id)
    if not material:
        raise HTTPException(404, "Материал не найден.")
    warehouse = await db.get(Warehouse, payload.warehouse_id)
    if not warehouse:
        raise HTTPException(404, "Склад не найден.")

    mv = await warehouse_svc.record_movement(
        db, material_id=material_id, warehouse_id=payload.warehouse_id, movement_type=payload.movement_type,
        quantity=payload.quantity, performed_by=user.email, note=payload.note,
    )
    await audit_svc.record(
        db, action="warehouse_movement_recorded", user_id=user.id, user_email=user.email,
        parameters=payload.model_dump(), result={"movement_id": mv.id}, entity_type="material", entity_id=material_id,
    )
    await db.commit()
    return mv.as_dict()
