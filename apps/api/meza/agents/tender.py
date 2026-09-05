from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from meza.agents.base import Agent, AgentResult
from meza.core.utils import today
from meza.models import Tender
from meza.tools.base import ToolContext


class TenderAgent(Agent):
    """Internal framework only (§12): stores found tenders, analyzes requirements/deadlines,
    fit with ATON+ capabilities. Does NOT submit bids automatically."""

    agent_id = "tenders"
    name = "Tender Agent"
    description = "Хранение и анализ тендеров: требования, сроки, соответствие возможностям ATON+."
    capabilities = ["list_tenders", "deadline_check"]
    allowed_tools = []
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None) -> AgentResult:
        cutoff = today() + timedelta(days=7)
        q = select(Tender).where(Tender.status.in_(["FOUND", "ANALYZING", "GO"]), Tender.submission_deadline.is_not(None), Tender.submission_deadline <= cutoff)
        rows = (await ctx.db.execute(q)).scalars().all()
        findings = [{"type": "tender_deadline_soon", "id": t.id, "title": t.title, "deadline": t.submission_deadline.isoformat()} for t in rows]
        risks = [{"title": f"Тендер «{t.title}»: срок подачи через {(t.submission_deadline - today()).days} дн.", "severity": "MEDIUM", "entity_type": "tender", "entity_id": t.id} for t in rows]
        summary = f"Тендеров с приближающимся дедлайном: {len(rows)}." if rows else "Нет тендеров с приближающимся дедлайном подачи."
        return AgentResult(status="success", summary=summary, findings=findings, risks=risks, data={"tenders": [t.as_dict() for t in rows]})
