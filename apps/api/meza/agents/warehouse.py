from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.services import warehouse as warehouse_svc
from meza.tools.base import ToolContext


class WarehouseAgent(Agent):
    agent_id = "warehouse"
    name = "Warehouse Agent"
    description = "Остатки, движения, резерв, дефицит, медленно оборачиваемые материалы."
    capabilities = ["stock", "availability", "low_stock", "slow_moving"]
    allowed_tools = ["get_inventory", "check_material_availability"]
    risk_level = "LOW"

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None) -> AgentResult:
        params = params or {}
        material_name = params.get("material_name") or params.get("material_sku")
        budget = Budget(8, 10, 1)
        if material_name:
            result = await execute_tool(
                ctx.db, tool_name="get_inventory",
                params={"material_sku": params.get("material_sku"), "material_name": params.get("material_name")},
                ctx=ctx, budget=budget,
            )
            if not result.ok:
                return AgentResult(status="insufficient_data", summary=result.error or "Материал не найден.", error=result.error)
            return AgentResult(status="success", summary=result.summary, sources=result.sources, data=result.data)
        low = await warehouse_svc.low_stock_materials(ctx.db)
        slow = await warehouse_svc.slow_moving_materials(ctx.db)
        findings = [{"type": "low_stock", **m} for m in low] + [{"type": "slow_moving", **m} for m in slow]
        risks = [
            {"title": f"Материал «{m['material_name']}» ниже минимума", "severity": "MEDIUM", "entity_type": "material", "entity_id": m["material_id"]}
            for m in low
        ]
        summary = f"Ниже минимума: {len(low)} материалов. Без движения: {len(slow)}."
        return AgentResult(
            status="success", summary=summary, findings=findings, risks=risks,
            recommendations=["Создать заявки на закупку для позиций ниже минимума."] if low else [],
            data={"low_stock": low, "slow_moving": slow},
        )
