"""Finance read/compute helpers — plan vs actual cost breakdown per order."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.models import Cost


async def cost_breakdown(db: AsyncSession, order_id: int) -> tuple[dict[str, float], dict[str, float]]:
    rows = (await db.execute(select(Cost).where(Cost.order_id == order_id))).scalars().all()
    planned: dict[str, float] = {}
    actual: dict[str, float] = {}
    for r in rows:
        target = planned if r.kind == "PLANNED" else actual
        target[r.category] = target.get(r.category, 0) + r.amount
    return planned, actual
