from __future__ import annotations

from sqlalchemy import select

from meza.agents.base import Agent, AgentResult
from meza.models import Campaign, Lead
from meza.orchestrator.executor import Budget
from meza.rules.marketing import compute_campaign_performance
from meza.tools.base import ToolContext


class MarketingAgent(Agent):
    """Internal analytics only (§21). No automatic publication without approval."""

    agent_id = "marketing"
    name = "Marketing Agent"
    description = "Контент, кампании, обращения, источники лидов, эффективность (CPL, конверсия)."
    capabilities = ["campaign_performance", "lead_sources", "content_publish_proposal"]
    allowed_tools = ["list_content_items", "publish_content", "get_business_memory"]
    risk_level = "LOW"
    requires_approval = True

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        budget = budget or Budget(8, 10, 1)
        if _looks_publish_related(request):
            reasoned = await self.reason(ctx, request, budget, params_hint=params or None)
            if reasoned is not None:
                return reasoned

        campaigns = (await ctx.db.execute(select(Campaign).where(Campaign.status == "ACTIVE"))).scalars().all()
        leads = (await ctx.db.execute(select(Lead))).scalars().all()
        by_source: dict[str, int] = {}
        for lead in leads:
            by_source[lead.source or "unknown"] = by_source.get(lead.source or "unknown", 0) + 1

        performance = []
        for c in campaigns:
            converted = sum(1 for lead in leads if lead.campaign_id == c.id and lead.status == "CONVERTED")
            perf = compute_campaign_performance(
                campaign_id=c.id, name=c.name, budget=c.budget, spent=c.spent,
                leads_generated=c.leads_generated, leads_converted=converted,
            )
            performance.append(perf.as_dict())

        overspent = [p for p in performance if p["budget_utilization"] and p["budget_utilization"] > 1.0]
        risks = [
            {"title": f"Кампания «{p['name']}» превысила бюджет ({p['budget_utilization'] * 100:.0f}%)",
             "severity": "LOW", "entity_type": "campaign", "entity_id": p["campaign_id"]}
            for p in overspent
        ]
        data = {"active_campaigns": performance, "leads_by_source": by_source, "total_leads": len(leads)}
        return AgentResult(
            status="success", risks=risks,
            summary=f"Активных кампаний: {len(campaigns)}. Лидов всего: {len(leads)}.",
            data=data,
        )


def _looks_publish_related(request: str) -> bool:
    lowered = request.lower()
    return any(w in lowered for w in ("публик", "опублик", "разместить", "выложи", "контент", "рассылк"))
