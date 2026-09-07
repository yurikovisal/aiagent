from __future__ import annotations

from meza.agents.base import Agent, AgentResult
from meza.orchestrator.executor import Budget, execute_tool
from meza.services import warehouse as warehouse_svc
from meza.tools.base import ToolContext


class ProcurementAgent(Agent):
    agent_id = "procurement"
    name = "Procurement Agent"
    description = (
        "Анализирует потребность в материалах, проверяет наличие и сроки поставок, при "
        "обнаруженном дефиците предлагает заявку на закупку (create_purchase_request). "
        "Сам закупку НЕ совершает — только предлагает, окончательное решение всегда за человеком."
    )
    capabilities = ["availability_check", "purchase_request_proposal", "supplier_history"]
    allowed_tools = ["check_material_availability", "create_purchase_request", "get_supplier_history", "get_business_memory"]
    risk_level = "MEDIUM"
    requires_approval = True

    async def handle(self, ctx: ToolContext, request: str, params: dict | None = None, budget: Budget | None = None) -> AgentResult:
        params = params or {}
        budget = budget or Budget(8, 10, 1)

        if params.get("material_name") and params.get("required_quantity"):
            return await self._check_and_propose(ctx, budget, params)

        # Free-text procurement question ("хватит ли материала для заказа X, если не хватает —
        # закажи") — let the LLM extract material/quantity/date and chain
        # check_material_availability -> create_purchase_request itself (§28 genuine reasoning).
        # The write is still gated by the Approval Engine regardless of what the LLM decides.
        # Gated to requests that actually name a material/quantity/supplier need — a broad "what
        # needs attention" scan (procurement is one of several domains it fans out to) should
        # fall through to the fast deterministic low-stock scan instead of an LLM round-trip.
        if _looks_targeted(request):
            reasoned = await self.reason(ctx, request, budget, params_hint=params or None)
            if reasoned is not None:
                return reasoned

        low = await warehouse_svc.low_stock_materials(ctx.db)
        return AgentResult(status="success", summary=f"Материалов ниже минимума: {len(low)}.", data={"low_stock": low})

    async def _check_and_propose(self, ctx: ToolContext, budget: Budget, params: dict) -> AgentResult:
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


def _looks_targeted(request: str) -> bool:
    lowered = request.lower()
    has_digit = any(ch.isdigit() for ch in request)
    return has_digit or any(w in lowered for w in ("закуп", "поставщик", "заявк", "хватит", "хватает", "дефицит", "закажи"))
