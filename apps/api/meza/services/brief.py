"""ExecutiveBriefService (§35). Structured brief with sections that are hidden when empty."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from meza.core.utils import today, utcnow
from meza.models import Approval, Order
from meza.services import events as events_svc
from meza.services import risk_engine
from meza.services import warehouse as warehouse_svc


async def build_executive_brief(db: AsyncSession, hours: int = 24) -> dict:
    await risk_engine.run_all_rules(db)
    risks = await risk_engine.list_open_risks(db, limit=200)
    changes = await events_svc.summarize_changes(db, hours=hours)

    critical = [r for r in risks if r["severity"] == "CRITICAL"]
    high = [r for r in risks if r["severity"] == "HIGH"]

    by_domain: dict[str, list[dict]] = {}
    for r in risks:
        by_domain.setdefault(r["domain"], []).append(r)

    low_stock = await warehouse_svc.low_stock_materials(db)

    pending_approvals = (await db.execute(select(Approval).where(Approval.status == "PENDING"))).scalars().all()

    at_risk_orders_q = select(Order).where(Order.deadline.is_not(None), Order.deadline <= today(),
                                            Order.status.notin_(["DELIVERED", "INSTALLED", "CLOSED", "CANCELLED"]))
    overdue_orders = (await db.execute(at_risk_orders_q)).scalars().all()

    sections = {}
    if critical or high:
        sections["critical"] = [r for r in critical]
        sections["high_priority"] = [r for r in high]
    if by_domain.get("production"):
        sections["production"] = by_domain["production"]
    if by_domain.get("finance"):
        sections["finance"] = by_domain["finance"]
    if low_stock:
        sections["warehouse"] = [{"type": "low_stock", **m} for m in low_stock]
    if by_domain.get("sales"):
        sections["sales"] = by_domain["sales"]
    if by_domain.get("projects"):
        sections["projects"] = by_domain["projects"]
    if changes["total"]:
        sections["changes"] = changes
    if pending_approvals:
        sections["decisions_required"] = [
            {"id": a.id, "title": a.title, "risk": a.risk, "created_at": a.created_at.isoformat()} for a in pending_approvals
        ]

    total_attention = len(critical) + len(high) + len(pending_approvals) + len(overdue_orders)
    exec_summary = (
        f"MEZA обнаружила {total_attention} событий, требующих внимания: "
        f"{len(critical)} критических, {len(high)} высокого приоритета, "
        f"{len(pending_approvals)} решений ожидают утверждения."
    )

    return {
        "generated_at": utcnow().isoformat(),
        "executive_summary": exec_summary,
        "attention_count": total_attention,
        "sections": sections,
        "overdue_orders": [o.as_dict() for o in overdue_orders],
    }
