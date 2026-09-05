from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext


class FinanceControllerAgent(Agent):
    agent_id = "finance"
    name = "Finance Controller"
    description = "Management accounting: PLAN vs ACTUAL по заказам. Не заменяет бухгалтерию."
    capabilities = ["order_margin", "cost_variance"]
    allowed_tools = ["calculate_order_margin"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None) -> AgentResult:
        params = params or {}
        budget = Budget(8, 10, 1)
        order_number = params.get("order_number")
        if not order_number:
            return AgentResult(status="insufficient_data", summary="Недостаточно данных: не указан номер заказа для расчёта маржи.")
        result = await execute_tool(ctx.db, tool_name="calculate_order_margin", params={"order_number": order_number}, ctx=ctx, budget=budget)
        if not result.ok:
            return AgentResult(status="insufficient_data", summary=result.error or "Нет данных.", error=result.error)
        risks = []
        if result.data.get("cost_variance_pct") and result.data["cost_variance_pct"] > 10:
            risks.append({
                "title": f"Перерасход по заказу {order_number}: {result.data['cost_variance_pct']:.1f}%",
                "severity": "MEDIUM", "entity_type": "order", "entity_id": params.get("order_id"),
            })
        return AgentResult(status="success", summary=result.data["explanation"], risks=risks, sources=result.sources, data=result.data)
