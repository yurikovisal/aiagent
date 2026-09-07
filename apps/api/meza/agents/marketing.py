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
    capabilities = ["campaign_performance", "lead_sources"]
    allowed_tools = []
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
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
