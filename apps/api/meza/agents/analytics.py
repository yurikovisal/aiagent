from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget
from meza.services import risk_engine
from meza.tools.base import ToolContext


class AnalyticsAgent(Agent):
    """Combines multiple domains (sales+production+warehouse+finance) for cross-cutting questions
    like 'why did margin drop' (§20)."""

    agent_id = "analytics"
    name = "Analytics Agent"
    description = "Кросс-доменная аналитика: объединяет sales/production/warehouse/finance."
    capabilities = ["cross_domain"]
    allowed_tools = []
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        await risk_engine.run_all_rules(ctx.db)
        risks = await risk_engine.list_open_risks(ctx.db, limit=100)
        by_domain: dict[str, int] = {}
        for r in risks:
            by_domain[r["domain"]] = by_domain.get(r["domain"], 0) + 1
        summary = "Риски по доменам: " + ", ".join(f"{k}: {v}" for k, v in by_domain.items()) if by_domain else "Открытых рисков нет."
        recs = list(dict.fromkeys(r["recommendation"] for r in risks[:5] if r.get("recommendation")))
        return AgentResult(status="success", summary=summary, risks=risks[:20], recommendations=recs,
                            data={"risks_by_domain": by_domain, "risks": risks[:20]})
