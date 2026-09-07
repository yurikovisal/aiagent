from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from meza.agents.base import Agent, AgentResult
from meza.core.utils import today
from meza.models import Tender, WorkCenter
from meza.orchestrator.executor import Budget
from meza.rules.tenders import analyze_fit
from meza.tools.base import ToolContext


class TenderAgent(Agent):
    """Internal framework only (§12): stores found tenders, analyzes requirements/deadlines,
    fit with ATON+ capabilities. Does NOT submit bids automatically."""

    agent_id = "tenders"
    name = "Tender Agent"
    description = (
        "Хранение и анализ тендеров: требования, сроки, соответствие производственным "
        "возможностям ATON+ (analyze_tender_fit). Никогда не подаёт заявки автоматически."
    )
    capabilities = ["list_tenders", "deadline_check", "fit_analysis"]
    allowed_tools = ["list_tenders", "analyze_tender_fit"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        params = params or {}
        budget = budget or Budget(8, 10, 1)

        if params.get("tender_id"):
            reasoned = await self.reason(ctx, request, budget, params_hint=params)
            if reasoned is not None:
                return reasoned

        cutoff = today() + timedelta(days=7)
        q = select(Tender).where(Tender.status.in_(["FOUND", "ANALYZING", "GO"]), Tender.submission_deadline.is_not(None), Tender.submission_deadline <= cutoff)
        rows = (await ctx.db.execute(q)).scalars().all()
        work_centers = list((await ctx.db.execute(select(WorkCenter.code).where(WorkCenter.status == "ACTIVE"))).scalars().all())

        findings = []
        risks = []
        for t in rows:
            fit = analyze_fit(
                required_work_centers=t.required_work_centers or [],
                available_work_centers=work_centers,
                submission_deadline=t.submission_deadline,
                today=today(),
            )
            t.fit_score = fit.fit_score
            t.analysis = fit.as_dict()
            findings.append({"type": "tender_deadline_soon", "id": t.id, "title": t.title, "deadline": t.submission_deadline.isoformat(), "fit": fit.as_dict()})
            severity = "HIGH" if fit.verdict == "GO_CANDIDATE" else "MEDIUM"
            risks.append({
                "title": f"Тендер «{t.title}»: срок подачи через {(t.submission_deadline - today()).days} дн. ({fit.verdict})",
                "severity": severity, "entity_type": "tender", "entity_id": t.id,
            })
        await ctx.db.flush()
        summary = f"Тендеров с приближающимся дедлайном: {len(rows)}." if rows else "Нет тендеров с приближающимся дедлайном подачи."
        return AgentResult(status="success", summary=summary, findings=findings, risks=risks, data={"tenders": [t.as_dict() for t in rows]})
