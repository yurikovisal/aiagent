from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.services import warehouse as warehouse_svc
from meza.tools.base import ToolContext


class ProcurementAgent(Agent):
    agent_id = "procurement"
    name = "Procurement Agent"
    description = "Анализирует потребность, сравнивает предложения; не совершает закупку сам."
    capabilities = ["availability_check", "purchase_request_proposal", "supplier_history"]
    allowed_tools = ["check_material_availability", "create_purchase_request", "get_supplier_history"]
    risk_level = "MEDIUM"
    requires_approval = True

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None) -> AgentResult:
        params = params or {}
        budget = Budget(8, 10, 1)
        if params.get("material_name") and params.get("required_quantity"):
            result = await execute_tool(
                ctx.db, tool_name="check_material_availability",
                params={"material_name": params["material_name"], "required_quantity": params["required_quantity"], "needed_by": params.get("needed_by")},
                ctx=ctx, budget=budget,
            )
            if not result.ok:
                return AgentResult(status="insufficient_data", summary=result.error or "Нет данных.", error=result.error)
            actions = []
            recs = []
            if result.data["status"] == "SHORTAGE":
                actions.append({
                    "tool": "create_purchase_request",
                    "params": {"material_name": params["material_name"], "quantity": result.data["shortage_after_incoming"],
                               "reason": f"Прогнозируемый дефицит к {params.get('needed_by')}", "needed_by": params.get("needed_by")},
                })
                recs.append(f"Создать заявку на закупку {result.data['shortage_after_incoming']:g} — одобрение обязательно.")
            return AgentResult(status="success", summary=result.summary, sources=result.sources,
                                actions_proposed=actions, recommendations=recs, data=result.data)
        low = await warehouse_svc.low_stock_materials(ctx.db)
        return AgentResult(status="success", summary=f"Материалов ниже минимума: {len(low)}.", data={"low_stock": low})
