from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext


class ProductionAgent(Agent):
    agent_id = "production"
    name = "Production Planner"
    description = "Производственные заказы, этапы, зависимости, downstream-влияние задержек."
    capabilities = ["production_status", "delay_impact"]
    allowed_tools = ["get_production_status", "simulate_delay_impact", "get_order", "search_orders"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        params = params or {}
        budget = budget or Budget(8, 10, 1)
        order_number = params.get("order_number")
        if order_number:
            result = await execute_tool(ctx.db, tool_name="get_production_status", params={"order_number": order_number}, ctx=ctx, budget=budget)
            if not result.ok:
                return AgentResult(status="insufficient_data", summary=result.error or "Нет данных.", error=result.error)
            data = result.data
            impact = data.get("impact")
            findings = [{"type": "production_status", "order": order_number, "status": data["production_order"]["status"]}]
            risks = []
            recs = []
            if impact and impact.get("deadline_missed_by_days"):
                risks.append({
                    "title": f"Заказ {order_number}: срыв дедлайна на {impact['deadline_missed_by_days']:.0f} дн.",
                    "severity": "CRITICAL" if impact["deadline_missed_by_days"] > 2 else "HIGH",
                    "entity_type": "order", "entity_id": data["order"]["id"],
                })
                recs.append("Рассмотреть ускорение критического этапа или уведомить клиента.")
            return AgentResult(
                status="success", summary=result.summary, findings=findings, risks=risks,
                recommendations=recs, sources=result.sources, data=data,
            )
        # No order number caught by regex — e.g. "что будет, если производство задержится ещё
        # на 2 дня?" or a request naming the customer/title instead of the order code. Let the
        # LLM find the right order (search_orders) and, if relevant, run simulate_delay_impact.
        # Only for requests that plausibly target a specific order/simulation — a broad "what
        # needs attention" scan should stay fast and deterministic, not pay for an LLM round-trip.
        if _looks_targeted(request):
            reasoned = await self.reason(ctx, request, budget, params_hint=params or None)
            if reasoned is not None:
                return reasoned

        # broad scan: overdue-ish production orders
        search = await execute_tool(ctx.db, tool_name="search_orders", params={"status": "IN_PRODUCTION", "limit": 20}, ctx=ctx, budget=budget)
        orders = search.data or []
        findings = [{"type": "in_production", "order_id": o["id"], "number": o["number"], "progress": o["progress"]} for o in orders]
        return AgentResult(status="success", summary=f"В производстве заказов: {len(orders)}.", findings=findings, sources=search.sources, data={"orders": orders})


def _looks_targeted(request: str) -> bool:
    lowered = request.lower()
    return any(w in lowered for w in (
        "задерж", "что будет, если", "что произойдёт", "симулир", "заказ", "клиент", "покажи производств",
    ))
