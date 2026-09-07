from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext


class SalesAgent(Agent):
    agent_id = "sales"
    name = "Sales Agent"
    description = "Сделки, клиенты, зависшие сделки, follow-up, конверсия."
    capabilities = ["deals", "customers", "stalled_deals"]
    allowed_tools = ["search_deals", "get_business_memory"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        params = params or {}
        budget = budget or Budget(8, 10, 1)

        # A targeted question ("покажи сделки на стадии переговоров", "что со сделкой
        # СтройИнвест") — let the LLM pick the right filter instead of always running the
        # generic stalled-deal scan.
        if _looks_targeted(request):
            reasoned = await self.reason(ctx, request, budget, params_hint=params or None)
            if reasoned is not None:
                return reasoned

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


def _looks_targeted(request: str) -> bool:
    lowered = request.lower()
    return any(w in lowered for w in ("стади", "клиент", "заказчик", "сделка по", "покажи сделк"))
