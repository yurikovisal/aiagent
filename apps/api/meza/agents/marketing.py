from __future__ import annotations

from sqlalchemy import select

from meza.agents.base import Agent, AgentResult
from meza.models import Campaign, Lead
from meza.tools.base import ToolContext


class MarketingAgent(Agent):
    """Internal analytics only (§21). No automatic publication without approval."""

    agent_id = "marketing"
    name = "Marketing Agent"
    description = "Контент, кампании, обращения, источники лидов, эффективность."
    capabilities = ["campaign_performance", "lead_sources"]
    allowed_tools = []
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None) -> AgentResult:
        campaigns = (await ctx.db.execute(select(Campaign).where(Campaign.status == "ACTIVE"))).scalars().all()
        leads = (await ctx.db.execute(select(Lead))).scalars().all()
        by_source: dict[str, int] = {}
        for lead in leads:
            by_source[lead.source or "unknown"] = by_source.get(lead.source or "unknown", 0) + 1
        data = {"active_campaigns": [c.as_dict() for c in campaigns], "leads_by_source": by_source, "total_leads": len(leads)}
        return AgentResult(status="success", summary=f"Активных кампаний: {len(campaigns)}. Лидов всего: {len(leads)}.", data=data)
