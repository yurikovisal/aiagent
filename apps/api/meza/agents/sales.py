from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext


class SalesAgent(Agent):
    agent_id = "sales"
    name = "Sales Agent"
    description = "Сделки, клиенты, зависшие сделки, follow-up, конверсия."
    capabilities = ["deals", "customers", "stalled_deals"]
    allowed_tools = ["search_deals"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None) -> AgentResult:
        params = params or {}
        budget = Budget(8, 10, 1)
        stalled = await execute_tool(ctx.db, tool_name="search_deals", params={"stalled_days": params.get("stalled_days", 14)}, ctx=ctx, budget=budget)
        if not stalled.ok:
            return AgentResult(status="error", summary=stalled.error or "Ошибка получения сделок.", error=stalled.error)
        deals = stalled.data or []
        findings = []
        risks = []
        for d in deals:
            findings.append({"type": "stalled_deal", "deal_id": d["id"], "title": d["title"], "stage": d["stage"], "amount": d["amount"]})
            risks.append({
                "title": f"Сделка «{d['title']}» зависла на стадии {d['stage']}",
                "severity": "MEDIUM", "entity_type": "deal", "entity_id": d["id"],
            })
        summary = f"Зависших сделок: {len(deals)}." if deals else "Зависших сделок не обнаружено."
        return AgentResult(
            status="success", summary=summary, findings=findings, risks=risks,
            recommendations=["Назначить follow-up по зависшим сделкам."] if deals else [],
            sources=stalled.sources, confidence=1.0, data={"stalled_deals": deals},
        )
