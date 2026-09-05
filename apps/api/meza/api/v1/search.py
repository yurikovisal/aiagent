from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.api.deps import get_current_user
from meza.core.db import get_db
from meza.models import Customer, Document, Employee, Material, Order, Project, Supplier, User

router = APIRouter(prefix="/api/v1/search", tags=["search"])


@router.get("")
async def global_search(q: str, limit: int = 5, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if not q or len(q) < 2:
        return {"results": []}
    like = f"%{q}%"
    results = []

    async def _add(model, field, kind, label_fn):
        rows = (await db.execute(select(model).where(field.ilike(like)).limit(limit))).scalars().all()
        for r in rows:
            results.append({"type": kind, "id": r.id, "label": label_fn(r)})

    await _add(Order, Order.number, "order", lambda r: f"{r.number} — {r.title}")
    await _add(Order, Order.title, "order", lambda r: f"{r.number} — {r.title}")
    await _add(Project, Project.name, "project", lambda r: r.name)
    await _add(Customer, Customer.name, "customer", lambda r: r.name)
    await _add(Material, Material.name, "material", lambda r: f"{r.sku} — {r.name}")
    await _add(Employee, Employee.full_name, "employee", lambda r: r.full_name)
    await _add(Document, Document.title, "document", lambda r: r.title)
    await _add(Supplier, Supplier.name, "supplier", lambda r: r.name)

    return {"results": results[:30]}
