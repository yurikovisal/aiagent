"""Production read/compute helpers. Downstream impact uses meza.rules.production (pure logic)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.models import Order, ProductionOrder, ProductionStage, StageDependency, WorkCenter
from meza.rules.production import ImpactResult, StageNode, propagate_delay


async def find_order(db: AsyncSession, *, order_number: str | None = None, order_id: int | None = None) -> Order | None:
    if order_id:
        return await db.get(Order, order_id)
    if order_number:
        return (await db.execute(select(Order).where(Order.number == order_number))).scalars().first()
    return None


async def get_production_order(db: AsyncSession, order_id: int) -> ProductionOrder | None:
    return (await db.execute(select(ProductionOrder).where(ProductionOrder.order_id == order_id))).scalars().first()


async def get_stages(db: AsyncSession, production_order_id: int) -> list[ProductionStage]:
    q = (
        select(ProductionStage)
        .where(ProductionStage.production_order_id == production_order_id)
        .order_by(ProductionStage.sequence.asc())
    )
    return (await db.execute(q)).scalars().all()


async def get_dependencies(db: AsyncSession, stage_ids: list[int]) -> dict[int, list[int]]:
    if not stage_ids:
        return {}
    q = select(StageDependency).where(StageDependency.stage_id.in_(stage_ids))
    rows = (await db.execute(q)).scalars().all()
    out: dict[int, list[int]] = {}
    for r in rows:
        out.setdefault(r.stage_id, []).append(r.depends_on_stage_id)
    return out


def stages_to_nodes(stages: list[ProductionStage], work_centers: dict[int, WorkCenter] | None = None,
                     deps: dict[int, list[int]] | None = None) -> list[StageNode]:
    work_centers = work_centers or {}
    deps = deps or {}
    nodes = []
    for s in stages:
        wc = work_centers.get(s.work_center_id)
        nodes.append(
            StageNode(
                id=s.id,
                name=s.name,
                work_center=wc.code if wc else str(s.work_center_id),
                sequence=s.sequence,
                duration_days=s.duration_days,
                planned_start=s.planned_start,
                planned_end=s.planned_end,
                status=s.status,
                depends_on=deps.get(s.id, []),
                slot_based=wc.slot_based if wc else False,
                slot_interval_days=wc.slot_interval_days if wc else 0,
            )
        )
    return nodes


async def get_work_centers_map(db: AsyncSession, stages: list[ProductionStage]) -> dict[int, WorkCenter]:
    ids = {s.work_center_id for s in stages}
    if not ids:
        return {}
    rows = (await db.execute(select(WorkCenter).where(WorkCenter.id.in_(ids)))).scalars().all()
    return {wc.id: wc for wc in rows}


async def build_nodes(db: AsyncSession, stages: list[ProductionStage]) -> list[StageNode]:
    """Fetch work centers + explicit dependencies and build fully-informed StageNodes —
    required so slot-based work centers (e.g. powder coating batches) are honoured (§14/§37)."""
    work_centers = await get_work_centers_map(db, stages)
    deps = await get_dependencies(db, [s.id for s in stages])
    return stages_to_nodes(stages, work_centers, deps)


def compute_current_impact(stages: list[ProductionStage], deadline=None,
                            nodes: list[StageNode] | None = None) -> ImpactResult | None:
    """If any stage is delayed past its planned_end (and not done), propagate the delay downstream.
    Pass `nodes` (from `build_nodes`) so work-center metadata (slot-based batching) is honoured;
    without it, a bare linear-sequence fallback is used."""
    if not stages:
        return None
    from meza.core.utils import today

    delayed = None
    max_delay = 0.0
    for s in stages:
        if s.status == "DONE" or not s.planned_end:
            continue
        ref_date = s.actual_end or today()
        overdue = (ref_date - s.planned_end).days
        if s.status in ("IN_PROGRESS", "BLOCKED") and overdue > max_delay:
            max_delay = overdue
            delayed = s
    if not delayed or max_delay <= 0:
        return None
    nodes = nodes if nodes is not None else stages_to_nodes(stages)
    return propagate_delay(nodes, delayed.id, max_delay, deadline=deadline)
