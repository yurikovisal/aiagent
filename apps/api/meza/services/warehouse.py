"""Warehouse read helpers backing tools/agents. Stock table is the source of truth for on-hand quantity."""

from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.utils import today, utcnow
from meza.models import InventoryMovement, Material, PurchaseOrder, Stock


async def find_material(db: AsyncSession, *, sku: str | None = None, name: str | None = None) -> Material | None:
    if sku:
        row = (await db.execute(select(Material).where(Material.sku == sku))).scalars().first()
        if row:
            return row
    if name:
        row = (await db.execute(select(Material).where(Material.name.ilike(f"%{name}%")))).scalars().first()
        if row:
            return row
    return None


async def stock_summary(db: AsyncSession, material_id: int) -> dict:
    rows = (await db.execute(select(Stock).where(Stock.material_id == material_id))).scalars().all()
    on_hand = sum(r.quantity for r in rows)
    reserved = sum(r.reserved for r in rows)
    last_movement = max((r.last_movement_at for r in rows if r.last_movement_at), default=None)
    material = await db.get(Material, material_id)
    last_movement_days = (utcnow() - last_movement).days if last_movement else None
    return {
        "material_id": material_id,
        "material_name": material.name if material else None,
        "sku": material.sku if material else None,
        "unit": material.unit if material else "",
        "on_hand": round(on_hand, 3),
        "reserved": round(reserved, 3),
        "available": round(max(0.0, on_hand - reserved), 3),
        "min_stock": material.min_stock if material else 0,
        "last_movement_at": last_movement.isoformat() if last_movement else None,
        "last_movement_days": last_movement_days,
    }


async def incoming_purchase_orders(db: AsyncSession, material_id: int) -> list[PurchaseOrder]:
    q = (
        select(PurchaseOrder)
        .where(PurchaseOrder.material_id == material_id, PurchaseOrder.status.in_(["ORDERED", "IN_TRANSIT", "PARTIAL"]))
        .order_by(PurchaseOrder.expected_at.asc())
    )
    return (await db.execute(q)).scalars().all()


async def low_stock_materials(db: AsyncSession) -> list[dict]:
    q = select(Material)
    materials = (await db.execute(q)).scalars().all()
    out = []
    for m in materials:
        summary = await stock_summary(db, m.id)
        if summary["available"] < m.min_stock:
            out.append({**summary, "shortage_below_min": round(m.min_stock - summary["available"], 3)})
    return out


async def slow_moving_materials(db: AsyncSession, threshold_days: int = 90) -> list[dict]:
    q = select(Material)
    materials = (await db.execute(q)).scalars().all()
    out = []
    for m in materials:
        summary = await stock_summary(db, m.id)
        if summary["on_hand"] <= 0:
            continue
        days = summary["last_movement_days"]
        if days is None or days >= threshold_days:
            out.append({**summary, "days_since_movement": days})
    return out


async def record_movement(
    db: AsyncSession,
    *,
    material_id: int,
    warehouse_id: int,
    movement_type: str,
    quantity: float,
    reference_type: str | None = None,
    reference_id: int | None = None,
    performed_by: str = "",
    note: str = "",
    occurred_at: date | None = None,
) -> InventoryMovement:
    mv = InventoryMovement(
        material_id=material_id,
        warehouse_id=warehouse_id,
        movement_type=movement_type,
        quantity=quantity,
        occurred_at=occurred_at or utcnow(),
        reference_type=reference_type,
        reference_id=reference_id,
        performed_by=performed_by,
        note=note,
    )
    db.add(mv)
    stock = (
        await db.execute(select(Stock).where(Stock.material_id == material_id, Stock.warehouse_id == warehouse_id))
    ).scalars().first()
    if not stock:
        stock = Stock(material_id=material_id, warehouse_id=warehouse_id, quantity=0, reserved=0)
        db.add(stock)
    delta = {
        "RECEIPT": quantity,
        "TRANSFER_IN": quantity,
        "CONSUMPTION": -quantity,
        "TRANSFER_OUT": -quantity,
        "ADJUSTMENT": quantity,
    }.get(movement_type, 0)
    stock.quantity = max(0.0, stock.quantity + delta)
    if movement_type == "RESERVATION":
        stock.reserved += quantity
    elif movement_type == "RELEASE":
        stock.reserved = max(0.0, stock.reserved - quantity)
    stock.last_movement_at = mv.occurred_at
    await db.flush()
    return mv
