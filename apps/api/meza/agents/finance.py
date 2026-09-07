from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.tools.base import ToolContext


class FinanceControllerAgent(Agent):
    agent_id = "finance"
    name = "Finance Controller"
    description = (
        "Management accounting: PLAN vs ACTUAL по заказам. Все финансовые расчёты (маржа, "
        "отклонения по категориям затрат) выполняются кодом инструмента calculate_order_margin — "
        "агент только находит нужный заказ и интерпретирует уже посчитанный результат. "
        "Не заменяет бухгалтерию."
    )
    capabilities = ["order_margin", "cost_variance"]
    allowed_tools = ["calculate_order_margin", "search_orders"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        params = params or {}
        budget = budget or Budget(8, 10, 1)
        order_number = params.get("order_number")

        if not order_number:
            # "Почему упала маржа по заказу для СтройИнвест?" — no order code, only a customer/
            # title hint. Let the LLM find the order (search_orders) then compute its margin.
            # Only worth an LLM round-trip for a targeted financial question — a broad "what
            # needs attention" scan (finance is one of several domains it fans out to) has
            # nothing concrete to ask about and should fall through fast.
            if _looks_targeted(request):
                reasoned = await self.reason(ctx, request, budget, params_hint=params or None)
                if reasoned is not None:
                    return reasoned
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


def _looks_targeted(request: str) -> bool:
    lowered = request.lower()
    return any(w in lowered for w in ("маржа", "маржин", "прибыл", "затрат", "себестоимост", "выручк", "рентабельн"))
